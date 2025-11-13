#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Text2SQL 能力测试脚本
测试 OpenAI 和 Google 大模型的 text2sql 能力，统计 SQL 执行成功率
"""

import json
import os
import sys
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import traceback

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 加载 .env 文件
def load_env_file(env_path: str = None) -> bool:
    """从 .env 文件加载环境变量
    
    Args:
        env_path: .env 文件路径，如果为 None 则自动查找
        
    Returns:
        bool: 是否成功加载
    """
    # 尝试使用 python-dotenv
    try:
        from dotenv import load_dotenv
        if env_path:
            if os.path.exists(env_path):
                load_dotenv(env_path, override=True)  # override=True 允许覆盖已存在的环境变量
                return True
        else:
            # 尝试从多个位置加载 .env 文件
            env_paths = [
                os.path.join(os.path.dirname(__file__), '.env'),  # test_case/.env
                os.path.join(os.path.dirname(__file__), '..', '.env'),  # 项目根目录/.env
            ]
            for path in env_paths:
                if os.path.exists(path):
                    load_dotenv(path, override=True)
                    return True
    except ImportError:
        pass
    
    # 如果没有 python-dotenv，手动解析 .env 文件
    if env_path is None:
        env_paths = [
            os.path.join(os.path.dirname(__file__), '.env'),
            os.path.join(os.path.dirname(__file__), '..', '.env'),
        ]
        for path in env_paths:
            if os.path.exists(path):
                env_path = path
                break
    
    if env_path and os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 跳过注释和空行
                    if not line or line.startswith('#'):
                        continue
                    # 解析 key=value
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # 移除引号
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        # 设置环境变量（使用 os.environ）
                        os.environ[key] = value
            return True
        except Exception as e:
            print(f"警告: 加载 .env 文件失败: {e}")
    
    return False


def set_env_var(key: str, value: str, override: bool = True) -> None:
    """设置环境变量
    
    Args:
        key: 环境变量名
        value: 环境变量值
        override: 如果环境变量已存在，是否覆盖（默认 True）
    """
    if override or key not in os.environ:
        os.environ[key] = value


def update_env_from_file(env_path: str = None) -> None:
    """从 .env 文件更新环境变量（强制更新）
    
    Args:
        env_path: .env 文件路径，如果为 None 则自动查找
    """
    load_env_file(env_path)


# 初始化时加载 .env 文件
load_env_file()

try:
    import openai
except ImportError:
    print("警告: 未安装 openai 库，请运行: pip install openai")
    openai = None

try:
    import google.generativeai as genai
except ImportError:
    print("警告: 未安装 google-generativeai 库，请运行: pip install google-generativeai")
    genai = None

try:
    import pymysql
except ImportError:
    print("警告: 未安装 pymysql 库，请运行: pip install pymysql")
    pymysql = None

# 默认数据库配置（向后兼容）
DEFAULT_DB_NAME = "tennis"
ALLOWED_TABLES = {
    "sportradar_tennis_competition",
    "sportradar_tennis_season",
    "sportradar_tennis_competitor",
    "sportradar_tennis_summary_live"
}
MAX_ROWS = 50

# 数据库连接缓存
_db_cache = {}


class MySQLDatabase:
    """简单的 MySQL 数据库连接类"""
    
    def __init__(self, host: str, user: str, password: str, database: str):
        """初始化数据库连接
        
        Args:
            host: 数据库主机地址
            user: 数据库用户名
            password: 数据库密码
            database: 数据库名称
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self._connection = None
    
    def _get_connection(self):
        """获取数据库连接（懒加载）"""
        if self._connection is None:
            if pymysql is None:
                raise ImportError("pymysql 未安装，请运行: pip install pymysql")
            self._connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
        return self._connection
    
    def execute_query(self, sql: str) -> List[Dict]:
        """执行查询并返回结果
        
        Args:
            sql: SQL 查询语句
            
        Returns:
            List[Dict]: 查询结果列表
        """
        conn = self._get_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()
    
    def close(self):
        """关闭数据库连接"""
        if self._connection:
            self._connection.close()
            self._connection = None


def is_safe_sql(sql: str, allowed_tables: set, max_rows: int = 50) -> Tuple[bool, str]:
    """检查 SQL 是否安全（仅允许 SELECT + 限制条件）
    
    Args:
        sql: SQL 语句
        allowed_tables: 允许访问的表名集合（大写）
        max_rows: 最大返回行数
        
    Returns:
        Tuple[bool, str]: (是否安全, 错误消息)
    """
    sql_upper = sql.strip().upper()
    
    if not sql_upper.startswith("SELECT"):
        return False, "仅允许 SELECT 查询语句"
    
    # 提取 FROM 和 JOIN 中的表名
    tables = re.findall(r"FROM\s+([`\"\[\]\w.]+)", sql_upper, re.I)
    tables += re.findall(r"JOIN\s+([`\"\[\]\w.]+)", sql_upper, re.I)
    
    # 禁用关键字
    DISALLOWED_KEYWORDS = {
        "DROP", "DELETE", "UPDATE", "INSERT", "CREATE", "ALTER",
        "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE"
    }
    
    for table in tables:
        clean_table = re.sub(r'[`\"\[\]]', '', table.split('.')[-1])  # 支持 schema.table
        if clean_table.upper() not in allowed_tables:
            return False, f"禁止访问表 `{clean_table}`"
    
    # 检查禁用关键字
    for kw in DISALLOWED_KEYWORDS:
        if re.search(r'\b' + kw + r'\b', sql_upper):
            return False, f"禁止使用关键字 `{kw}`"
    
    # 检查 LIMIT
    limit_match = re.search(r"LIMIT\s+(\d+)", sql_upper, re.I)
    if not limit_match:
        return False, "查询必须包含 LIMIT 子句"
    if int(limit_match.group(1)) > max_rows:
        return False, f"LIMIT 值不能超过 {max_rows}"
    
    return True, ""


def get_db_from_config(db_name: str, db_config: Dict) -> MySQLDatabase:
    """根据配置创建数据库连接
    
    Args:
        db_name: 数据库名称标识
        db_config: 数据库配置字典，包含 host, user, password, database
        
    Returns:
        MySQLDatabase: 数据库连接实例
    """
    cache_key = f"{db_name}_{db_config.get('host')}_{db_config.get('database')}"
    
    if cache_key not in _db_cache:
        _db_cache[cache_key] = MySQLDatabase(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
    
    return _db_cache[cache_key]

# 默认 SQL 生成提示词（基于 tennis sql_query_agent.py）
DEFAULT_SQL_GENERATION_PROMPT = """你是一个专业的网球数据查询助手。你的任务是：

1. 理解用户关于网球比赛、选手、胜负关系、统计数据的提问。
2. 将自然语言转化为高效、安全的 SQL（必须包含 LIMIT，且不超过 50）。
3. 只返回 SQL 语句，不要包含任何其他解释或说明。

**数据库表结构**：
### 1. 表一：赛事元数据表
**表名**：`sportradar_tennis_competition`

**建表语句（DDL）**
```sql
CREATE TABLE `sportradar_tennis_competition` (
  `id` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Sportradar 赛事唯一标识，主键，格式如 sr:competition:XXXXX',
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '赛事完整名称，例如 "ITF Men Stara Zagora, Bulgaria Men Singles"',
  `type` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '赛事类型，常见值：singles、doubles、team，以及具体级别如 Grand Slam、ATP 1000、Challenger、ITF M25 等',
  `gender` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '性别分类，取值：men、women、mixed（统一小写）',
  `category_id` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '所属巡回赛/组织分类 ID，格式如 sr:category:XXXX',
  `category_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '分类名称，例如 ITF Men、ATP Tour、WTA Tour、Grand Slams',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

### 2. 表二：赛季实例表
**建表语句（DDL）**
```sql
CREATE TABLE `sportradar_tennis_season` (
  `id` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Sportradar 赛季唯一标识，主键，格式如 sr:season:XXXXXX',
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '赛季完整名称，例如 "ITF Argentina F7, Men Singles 2022"',
  `start_date` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '赛季开始日期，ISO 8601 格式字符串，如 "2022-11-13"',
  `end_date` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '赛季结束日期，ISO 8601 格式字符串，如 "2022-11-20"',
  `competition_id` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '外键，关联 sportradar_tennis_competition.id',
  PRIMARY KEY (`id`),
  INDEX idx_competition (competition_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

### 3. 表三：参赛实体表
**建表语句（DDL）**
```sql
CREATE TABLE `sportradar_tennis_competitor` (
  `id` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Sportradar 参赛实体唯一标识（单人/组合），格式如 sr:competitor:XXXXXX',
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '显示名称，如 "Cascino E / Monnet C" 或 "Djokovic N"',
  `short_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '短名称，通常与 name 一致',
  `abbreviation` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '缩写，如 "CAM"、"DJOK"',
  `players` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'JSON 数组，详列选手信息：id, name, country, country_code, abbreviation',
  `season_id` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '外键，关联 sportradar_tennis_season.id',
  PRIMARY KEY (`id`, `season_id`),
  INDEX idx_season (season_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

### 4. 表四：实时比赛摘要
表名：sportradar_tennis_summary_live
CREATE TABLE `sportradar_tennis_summary_live` (
  `sport_event_id` varchar(255) COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '比赛唯一 ID，主键，如 sr:sport_event:64653806',
  `sport_event_type` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '比赛类型',
  `sport_event_start_time` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '计划开赛时间，ISO 8601 UTC',
  `sport_event_start_time_confirmed` tinyint(1) DEFAULT NULL COMMENT '1=确认，0=未确认',
  `sport_event_parent_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '父赛事 ID（如团体赛）',
  `sport_event_replaced_by` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_resume_time` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '中断后恢复时间',
  `sport_event_estimated` tinyint(1) DEFAULT NULL COMMENT '1=预计时间',
  `sport_event_sport_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '运动 ID，网球为 sr:sport:5',
  `sport_event_sport_name` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'Tennis',
  `sport_event_category_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_category_name` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_category_country_code` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_competition_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '→ competition.id',
  `sport_event_competition_name` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_competition_alternative_name` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_competition_type` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'singles/doubles',
  `sport_event_competition_level` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_competition_gender` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_competition_parent_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_mode_best_of` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '3 或 5',
  `sport_event_round_name` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '如 "Round Robin"',
  `sport_event_round_number` int(11) DEFAULT NULL,
  `sport_event_round_cup_round_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_round_cup_round_sport_event_number` int(11) DEFAULT NULL,
  `sport_event_round_cup_round_number_of_sport_events` int(11) DEFAULT NULL,
  `sport_event_round_competition_sport_event_number` int(11) DEFAULT NULL,
  `sport_event_round_other_sport_event_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_season_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '→ season.id',
  `sport_event_season_name` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_season_year` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_season_competition_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_season_start_date` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_season_end_date` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_season_disabled` tinyint(1) DEFAULT NULL,
  `sport_event_stage_type` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'league, knockout',
  `sport_event_stage_year` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_stage_phase` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'regular season',
  `sport_event_stage_order` int(11) DEFAULT NULL,
  `sport_event_stage_start_date` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_stage_end_date` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_channels` text COLLATE utf8mb4_0900_ai_ci COMMENT '直播频道 JSON',
  `sport_event_children` text COLLATE utf8mb4_0900_ai_ci COMMENT '子赛事',
  `sport_event_competitors` text COLLATE utf8mb4_0900_ai_ci COMMENT '参赛者 JSON 数组，含 qualifier: home/away',
  `sport_event_coverage` text COLLATE utf8mb4_0900_ai_ci COMMENT '数据覆盖级别（如 play_by_play）',
  `sport_event_venue` text COLLATE utf8mb4_0900_ai_ci COMMENT '场地信息 JSON',
  `sport_event_sport_event_context_groups` text COLLATE utf8mb4_0900_ai_ci COMMENT '小组信息（如 Group D）',
  `sport_event_status` text COLLATE utf8mb4_0900_ai_ci COMMENT '实时状态 JSON：status, match_status, period_scores',
  `statistics_periods` text COLLATE utf8mb4_0900_ai_ci COMMENT '分盘数据（未来扩展）',
  `statistics_totals` text COLLATE utf8mb4_0900_ai_ci COMMENT '选手总计 JSON：aces, breakpoints_won 等',
  PRIMARY KEY (`sport_event_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

**约束**：
- 必须使用 `LIMIT` 限制返回行数（建议 ≤ 20）。
- 禁止任何写操作。
- 只返回 SQL 语句，不要包含任何其他解释或说明。
"""

# 完整的数据库表结构说明（用于补充到自定义提示词）
DATABASE_SCHEMA_PROMPT = """
**数据库表结构**：
### 1. 表一：赛事元数据表
**表名**：`sportradar_tennis_competition`

**建表语句（DDL）**
```sql
CREATE TABLE `sportradar_tennis_competition` (
  `id` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Sportradar 赛事唯一标识，主键，格式如 sr:competition:XXXXX',
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '赛事完整名称，例如 "ITF Men Stara Zagora, Bulgaria Men Singles"',
  `type` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '赛事类型，常见值：singles、doubles、team，以及具体级别如 Grand Slam、ATP 1000、Challenger、ITF M25 等',
  `gender` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '性别分类，取值：men、women、mixed（统一小写）',
  `category_id` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '所属巡回赛/组织分类 ID，格式如 sr:category:XXXX',
  `category_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '分类名称，例如 ITF Men、ATP Tour、WTA Tour、Grand Slams',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

### 2. 表二：赛季实例表
**建表语句（DDL）**
```sql
CREATE TABLE `sportradar_tennis_season` (
  `id` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Sportradar 赛季唯一标识，主键，格式如 sr:season:XXXXXX',
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '赛季完整名称，例如 "ITF Argentina F7, Men Singles 2022"',
  `start_date` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '赛季开始日期，ISO 8601 格式字符串，如 "2022-11-13"',
  `end_date` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '赛季结束日期，ISO 8601 格式字符串，如 "2022-11-20"',
  `competition_id` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '外键，关联 sportradar_tennis_competition.id',
  PRIMARY KEY (`id`),
  INDEX idx_competition (competition_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

### 3. 表三：参赛实体表
**建表语句（DDL）**
```sql
CREATE TABLE `sportradar_tennis_competitor` (
  `id` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Sportradar 参赛实体唯一标识（单人/组合），格式如 sr:competitor:XXXXXX',
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '显示名称，如 "Cascino E / Monnet C" 或 "Djokovic N"',
  `short_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '短名称，通常与 name 一致',
  `abbreviation` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '缩写，如 "CAM"、"DJOK"',
  `players` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'JSON 数组，详列选手信息：id, name, country, country_code, abbreviation',
  `season_id` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '外键，关联 sportradar_tennis_season.id',
  PRIMARY KEY (`id`, `season_id`),
  INDEX idx_season (season_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

### 4. 表四：实时比赛摘要
表名：sportradar_tennis_summary_live
CREATE TABLE `sportradar_tennis_summary_live` (
  `sport_event_id` varchar(255) COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '比赛唯一 ID，主键，如 sr:sport_event:64653806',
  `sport_event_type` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '比赛类型',
  `sport_event_start_time` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '计划开赛时间，ISO 8601 UTC',
  `sport_event_start_time_confirmed` tinyint(1) DEFAULT NULL COMMENT '1=确认，0=未确认',
  `sport_event_parent_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '父赛事 ID（如团体赛）',
  `sport_event_replaced_by` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_resume_time` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '中断后恢复时间',
  `sport_event_estimated` tinyint(1) DEFAULT NULL COMMENT '1=预计时间',
  `sport_event_sport_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '运动 ID，网球为 sr:sport:5',
  `sport_event_sport_name` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'Tennis',
  `sport_event_category_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_category_name` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_category_country_code` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_competition_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '→ competition.id',
  `sport_event_competition_name` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_competition_alternative_name` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_competition_type` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'singles/doubles',
  `sport_event_competition_level` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_competition_gender` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_competition_parent_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_mode_best_of` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '3 或 5',
  `sport_event_round_name` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '如 "Round Robin"',
  `sport_event_round_number` int(11) DEFAULT NULL,
  `sport_event_round_cup_round_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_round_cup_round_sport_event_number` int(11) DEFAULT NULL,
  `sport_event_round_cup_round_number_of_sport_events` int(11) DEFAULT NULL,
  `sport_event_round_competition_sport_event_number` int(11) DEFAULT NULL,
  `sport_event_round_other_sport_event_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_season_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '→ season.id',
  `sport_event_season_name` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_season_year` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_season_competition_id` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_season_start_date` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_season_end_date` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_season_disabled` tinyint(1) DEFAULT NULL,
  `sport_event_stage_type` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'league, knockout',
  `sport_event_stage_year` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_stage_phase` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'regular season',
  `sport_event_stage_order` int(11) DEFAULT NULL,
  `sport_event_stage_start_date` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_stage_end_date` varchar(255) COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `sport_event_channels` text COLLATE utf8mb4_0900_ai_ci COMMENT '直播频道 JSON',
  `sport_event_children` text COLLATE utf8mb4_0900_ai_ci COMMENT '子赛事',
  `sport_event_competitors` text COLLATE utf8mb4_0900_ai_ci COMMENT '参赛者 JSON 数组，含 qualifier: home/away',
  `sport_event_coverage` text COLLATE utf8mb4_0900_ai_ci COMMENT '数据覆盖级别（如 play_by_play）',
  `sport_event_venue` text COLLATE utf8mb4_0900_ai_ci COMMENT '场地信息 JSON',
  `sport_event_sport_event_context_groups` text COLLATE utf8mb4_0900_ai_ci COMMENT '小组信息（如 Group D）',
  `sport_event_status` text COLLATE utf8mb4_0900_ai_ci COMMENT '实时状态 JSON：status, match_status, period_scores',
  `statistics_periods` text COLLATE utf8mb4_0900_ai_ci COMMENT '分盘数据（未来扩展）',
  `statistics_totals` text COLLATE utf8mb4_0900_ai_ci COMMENT '选手总计 JSON：aces, breakpoints_won 等',
  PRIMARY KEY (`sport_event_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

**约束**：
- 必须使用 `LIMIT` 限制返回行数（建议 ≤ 20）。
- 禁止任何写操作。
- 只返回 SQL 语句，不要包含任何其他解释或说明。
"""


def extract_sql_from_response(response: str) -> Optional[str]:
    """从模型响应中提取 SQL 语句"""
    # 尝试提取 ```sql ... ``` 代码块中的内容
    sql_match = re.search(r'```sql\s*(.*?)\s*```', response, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return sql_match.group(1).strip()
    
    # 尝试提取 ``` ... ``` 代码块中的内容
    code_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
    if code_match:
        content = code_match.group(1).strip()
        # 如果内容以 SELECT 开头，认为是 SQL
        if content.upper().startswith('SELECT'):
            return content
    
    # 如果响应本身看起来像 SQL（以 SELECT 开头）
    response_stripped = response.strip()
    if response_stripped.upper().startswith('SELECT'):
        # 移除可能的行号或其他前缀
        lines = response_stripped.split('\n')
        sql_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                sql_lines.append(line)
        return ' '.join(sql_lines)
    
    return None


def generate_sql_with_openai(question: str, prompt: str, model: str = "gpt-4o") -> Tuple[Optional[str], Optional[str]]:
    """使用 OpenAI 模型生成 SQL"""
    if openai is None:
        return None, "OpenAI 库未安装"
    
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": question}
        ]
        
        # 检测是否需要使用 responses API（某些新模型如 gpt-5-pro）
        use_responses_api = model in ["gpt-5-pro", "gpt-5-thinking", "gpt-5-main"]
        
        if use_responses_api:
            # 使用 responses API
            try:
                # responses API 使用不同的格式
                full_prompt = f"{prompt}\n\n用户问题：{question}\n\n请只返回 SQL 语句："
                response = client.responses.create(
                    model=model,
                    input=full_prompt
                )
                # responses API 的响应格式可能不同
                if hasattr(response, 'output') and response.output:
                    content = response.output
                elif hasattr(response, 'choices') and response.choices:
                    content = response.choices[0].text if hasattr(response.choices[0], 'text') else str(response.choices[0])
                else:
                    content = str(response)
            except AttributeError:
                # 如果 responses API 不存在，尝试使用 chat/completions
                return None, f"模型 {model} 需要使用 responses API，但当前 SDK 版本可能不支持。请使用支持 chat/completions 的模型（如 gpt-4o, gpt-4o-mini）"
        else:
            # 使用 chat/completions API
            # 某些模型不支持自定义 temperature，先尝试使用 temperature，如果失败则使用默认值
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.1
                )
            except Exception as temp_error:
                # 如果 temperature 不支持，尝试不使用 temperature（使用默认值）
                error_str = str(temp_error)
                if 'temperature' in error_str.lower() or 'unsupported_value' in error_str.lower():
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages
                    )
                elif 'v1/responses' in error_str.lower() or 'not in v1/chat/completions' in error_str.lower():
                    # 如果模型需要使用 responses API，尝试使用
                    try:
                        full_prompt = f"{prompt}\n\n用户问题：{question}\n\n请只返回 SQL 语句："
                        response = client.responses.create(
                            model=model,
                            input=full_prompt
                        )
                        if hasattr(response, 'output') and response.output:
                            content = response.output
                        elif hasattr(response, 'choices') and response.choices:
                            content = response.choices[0].text if hasattr(response.choices[0], 'text') else str(response.choices[0])
                        else:
                            content = str(response)
                        sql = extract_sql_from_response(content)
                        return sql, None
                    except AttributeError:
                        return None, f"模型 {model} 需要使用 responses API，但当前 SDK 版本不支持。建议使用 gpt-4o 或 gpt-4o-mini"
                else:
                    # 其他错误直接抛出
                    raise
            
            # 从 chat/completions 响应中提取内容
            content = response.choices[0].message.content
        
        sql = extract_sql_from_response(content)
        
        return sql, None
    except Exception as e:
        error_msg = str(e)
        # 如果错误提示需要使用 responses API
        if 'v1/responses' in error_msg.lower() or 'not in v1/chat/completions' in error_msg.lower():
            return None, f"模型 {model} 需要使用 responses API，但当前 SDK 可能不支持。建议使用支持 chat/completions 的模型（如 gpt-4o, gpt-4o-mini, gpt-4-turbo）"
        return None, f"OpenAI API 错误: {error_msg}"


def generate_sql_with_google(question: str, prompt: str, model: str = "gemini-2.0-flash-exp") -> Tuple[Optional[str], Optional[str]]:
    """使用 Google 模型生成 SQL"""
    if genai is None:
        return None, "Google Generative AI 库未安装"
    
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return None, "未设置 GOOGLE_API_KEY 环境变量"
        
        genai.configure(api_key=api_key)
        
        model_instance = genai.GenerativeModel(model)
        
        full_prompt = f"{prompt}\n\n用户问题：{question}\n\n请只返回 SQL 语句："
        
        response = model_instance.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.1)
        )
        
        content = response.text
        sql = extract_sql_from_response(content)
        
        return sql, None
    except Exception as e:
        return None, f"Google API 错误: {str(e)}"


# 危险 SQL 关键字（会对数据库造成修改的操作）
DANGEROUS_KEYWORDS = {
    "DROP", "DELETE", "UPDATE", "INSERT", "CREATE", "ALTER",
    "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "REPLACE"
}


def detect_dangerous_sql(sql: str) -> Tuple[bool, Optional[str]]:
    """检测 SQL 是否包含危险操作
    
    Returns:
        Tuple[bool, Optional[str]]: (是否为危险SQL, 危险操作类型)
    """
    if not sql:
        return False, None
    
    sql_upper = sql.strip().upper()
    
    # 检查是否包含危险关键字
    for keyword in DANGEROUS_KEYWORDS:
        # 使用单词边界匹配，避免误判（如 SELECT 中包含 "SELECT"）
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, sql_upper):
            return True, keyword
    
    return False, None


def execute_sql_safely(sql: str, db_name: str = None, db_config: Dict = None) -> Tuple[bool, str, Optional[List[Dict]]]:
    """安全执行 SQL 并返回结果
    
    Args:
        sql: SQL 语句
        db_name: 数据库名称标识（用于从配置中获取）
        db_config: 数据库配置字典（如果提供则直接使用）
        
    Returns:
        Tuple[bool, str, Optional[List[Dict]]]: (是否成功, 消息, 结果)
    """
    if not sql:
        return False, "SQL 为空", None
    
    try:
        # 检查 SQL 安全性
        # 将允许的表名转换为大写集合
        allowed_tables_upper = {table.upper() for table in ALLOWED_TABLES}
        ok, msg = is_safe_sql(sql, allowed_tables_upper, MAX_ROWS)
        if not ok:
            return False, msg, None
        
        # 获取数据库连接
        if db_config:
            db = get_db_from_config(db_name or "custom", db_config)
        else:
            # 如果没有提供 db_config，无法连接数据库
            return False, "未提供数据库配置，无法执行 SQL", None
        
        results = db.execute_query(sql)
        
        return True, "执行成功", results
    except Exception as e:
        return False, f"执行异常: {str(e)}", None


def test_question(question: str, prompt: str, model_type: str, model_name: str, db_name: str = None, db_config: Dict = None) -> Dict:
    """测试单个问题的 SQL 生成和执行"""
    result = {
        "question": question,
        "prompt": prompt,
        "model_type": model_type,
        "model_name": model_name,
        "sql": None,
        "success": False,
        "error": None,
        "result_count": 0,
        "is_dangerous": False,
        "dangerous_keyword": None
    }
    
    # 生成 SQL
    if model_type == "openai":
        sql, error = generate_sql_with_openai(question, prompt, model_name)
    elif model_type == "google":
        sql, error = generate_sql_with_google(question, prompt, model_name)
    else:
        result["error"] = f"未知的模型类型: {model_type}"
        return result
    
    if error:
        result["error"] = error
        return result
    
    if not sql:
        result["error"] = "未能从模型响应中提取 SQL"
        return result
    
    result["sql"] = sql
    
    # 检测危险 SQL
    is_dangerous, dangerous_keyword = detect_dangerous_sql(sql)
    result["is_dangerous"] = is_dangerous
    result["dangerous_keyword"] = dangerous_keyword
    
    # 如果是危险 SQL，不执行，直接返回
    if is_dangerous:
        result["error"] = f"检测到危险操作: {dangerous_keyword}"
        return result
    
    # 执行 SQL（使用传入的数据库配置）
    success, msg, results = execute_sql_safely(sql, db_name=db_name, db_config=db_config)
    result["success"] = success
    if not success:
        result["error"] = msg
    else:
        result["result_count"] = len(results) if results else 0
    
    return result


def normalize_model_config(model_config, default_value):
    """标准化模型配置：将字符串转换为数组，确保返回数组格式"""
    if model_config is None:
        return default_value if isinstance(default_value, list) else [default_value]
    if isinstance(model_config, str):
        return [model_config]
    if isinstance(model_config, list):
        return model_config
    # 如果类型不对，返回默认值
    return default_value if isinstance(default_value, list) else [default_value]


def load_test_cases(testcase_file: str) -> Tuple[List[Dict], Dict]:
    """加载测试用例
    
    Returns:
        Tuple[List[Dict], Dict]: (测试组列表, 默认配置)
    """
    with open(testcase_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 向后兼容：如果存在旧的格式，转换为新格式
    if "questions" in data and "test_groups" not in data:
        # 使用默认提示词和模型
        default_prompt = data.get("default_prompt", DEFAULT_SQL_GENERATION_PROMPT + DATABASE_SCHEMA_PROMPT)
        default_openai_model = normalize_model_config(
            data.get("default_openai_model"), ["gpt-4o"]
        )
        default_google_model = normalize_model_config(
            data.get("default_google_model"), ["gemini-2.0-flash-exp"]
        )
        
        test_groups = [{
            "name": "默认测试组",
            "prompt": default_prompt,
            "openai_model": default_openai_model,
            "google_model": default_google_model,
            "questions": data["questions"]
        }]
    else:
        test_groups = data.get("test_groups", [])
    
    # 获取默认配置
    defaults = {
        "prompt": data.get("default_prompt", DEFAULT_SQL_GENERATION_PROMPT + DATABASE_SCHEMA_PROMPT),
        "openai_model": normalize_model_config(
            data.get("default_openai_model"), ["gpt-4o"]
        ),
        "google_model": normalize_model_config(
            data.get("default_google_model"), ["gemini-2.0-flash-exp"]
        )
    }
    
    # 获取数据库配置
    database_configs = data.get("database", {})
    
    # 为每个测试组补充默认值和数据库配置
    for group in test_groups:
        if "prompt" not in group:
            group["prompt"] = defaults["prompt"]
        else:
            # 如果提示词中没有包含数据库结构，自动添加
            if "数据库表结构" not in group["prompt"]:
                group["prompt"] = group["prompt"] + DATABASE_SCHEMA_PROMPT
        
        group["openai_model"] = normalize_model_config(
            group.get("openai_model"), defaults["openai_model"]
        )
        group["google_model"] = normalize_model_config(
            group.get("google_model"), defaults["google_model"]
        )
        
        # 处理数据库配置
        group_db_name = group.get("database_name")
        if group_db_name and group_db_name in database_configs:
            group["db_config"] = database_configs[group_db_name]
            group["db_name"] = group_db_name
        elif group_db_name:
            # 如果指定了 database_name 但配置中不存在，使用默认配置管理器
            group["db_name"] = group_db_name
            group["db_config"] = None
        else:
            # 如果没有指定，使用默认数据库
            group["db_name"] = DEFAULT_DB_NAME
            group["db_config"] = None
    
    return test_groups, defaults


def run_tests(testcase_file: str, openai_model: str = None, google_model: str = None):
    """运行所有测试"""
    print("=" * 80)
    print("Text2SQL 能力测试")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 加载测试用例
    test_groups, defaults = load_test_cases(testcase_file)
    
    total_questions = sum(len(group.get("questions", [])) for group in test_groups)
    print(f"\n加载了 {len(test_groups)} 个测试组，共 {total_questions} 个测试问题\n")
    
    # 测试结果：按模型类型和模型名称组织
    all_results = {
        "openai": {},
        "google": {}
    }
    
    # 遍历每个测试组
    for group_idx, group in enumerate(test_groups, 1):
        group_name = group.get("name", f"测试组{group_idx}")
        group_prompt = group.get("prompt", defaults["prompt"])
        
        # 处理模型配置：命令行参数优先，否则使用组配置，最后使用默认配置
        if openai_model:
            group_openai_models = [openai_model]
        else:
            group_openai_models = group.get("openai_model", defaults["openai_model"])
        
        if google_model:
            group_google_models = [google_model]
        else:
            group_google_models = group.get("google_model", defaults["google_model"])
        
        questions = group.get("questions", [])
        group_db_name = group.get("db_name", DEFAULT_DB_NAME)
        group_db_config = group.get("db_config")
        
        print("\n" + "=" * 80)
        print(f"测试组 {group_idx}: {group_name}")
        print(f"  OpenAI 模型: {', '.join(group_openai_models)}")
        print(f"  Google 模型: {', '.join(group_google_models)}")
        print(f"  数据库: {group_db_name}")
        if group_db_config:
            print(f"  数据库主机: {group_db_config.get('host', 'N/A')}")
        print(f"  问题数量: {len(questions)}")
        print("=" * 80)
        
        # 测试 Google 模型（遍历所有配置的模型）- 先测试 Google
        if genai:
            for model_name in group_google_models:
                print(f"\n[{group_name}] 开始测试 Google 模型: {model_name}")
                if model_name not in all_results["google"]:
                    all_results["google"][model_name] = []
                
                for i, question in enumerate(questions, 1):
                    print(f"\n  [{i}/{len(questions)}] Google ({model_name}) - {question}")
                    result = test_question(question, group_prompt, "google", model_name,
                                         db_name=group_db_name, db_config=group_db_config)
                    result["group_name"] = group_name
                    all_results["google"][model_name].append(result)
                    if result.get("is_dangerous"):
                        print(f"    ⚠️  危险 SQL 检测: {result['dangerous_keyword']}")
                        print(f"    SQL: {result['sql']}")
                    elif result["success"]:
                        print(f"    ✓ SQL 执行成功，返回 {result['result_count']} 条记录")
                        print(f"    SQL: {result['sql']}")
                    else:
                        print(f"    ✗ 失败: {result['error']}")
                        if result["sql"]:
                            print(f"    SQL: {result['sql']}")
        else:
            print(f"\n[{group_name}] 跳过 Google 测试（库未安装）")
        
        # 测试 OpenAI 模型（遍历所有配置的模型）- 后测试 OpenAI
        if openai:
            for model_name in group_openai_models:
                print(f"\n[{group_name}] 开始测试 OpenAI 模型: {model_name}")
                if model_name not in all_results["openai"]:
                    all_results["openai"][model_name] = []
                
                for i, question in enumerate(questions, 1):
                    print(f"\n  [{i}/{len(questions)}] OpenAI ({model_name}) - {question}")
                    result = test_question(question, group_prompt, "openai", model_name, 
                                         db_name=group_db_name, db_config=group_db_config)
                    result["group_name"] = group_name
                    all_results["openai"][model_name].append(result)
                    if result.get("is_dangerous"):
                        print(f"    ⚠️  危险 SQL 检测: {result['dangerous_keyword']}")
                        print(f"    SQL: {result['sql']}")
                    elif result["success"]:
                        print(f"    ✓ SQL 执行成功，返回 {result['result_count']} 条记录")
                        print(f"    SQL: {result['sql']}")
                    else:
                        print(f"    ✗ 失败: {result['error']}")
                        if result["sql"]:
                            print(f"    SQL: {result['sql']}")
        else:
            print(f"\n[{group_name}] 跳过 OpenAI 测试（库未安装）")
    
    # 统计结果
    print("\n" + "=" * 80)
    print("测试结果统计")
    print("=" * 80)
    
    # 先统计 Google，再统计 OpenAI
    for model_type in ["google", "openai"]:
        if not all_results[model_type]:
            continue
        
        print(f"\n{model_type.upper()} 模型统计:")
        print("-" * 80)
        
        # 遍历每个模型
        for model_name, model_results in all_results[model_type].items():
            total = len(model_results)
            success_count = sum(1 for r in model_results if r["success"])
            dangerous_count = sum(1 for r in model_results if r.get("is_dangerous", False))
            safe_count = total - dangerous_count
            success_rate = (success_count / safe_count * 100) if safe_count > 0 else 0
            
            print(f"\n  模型: {model_name}")
            print(f"    总问题数: {total}")
            print(f"    成功执行: {success_count}")
            print(f"    失败: {safe_count - success_count}")
            print(f"    ⚠️  危险 SQL: {dangerous_count}")
            print(f"    安全 SQL 成功率: {success_rate:.2f}%")
            
            # 按测试组统计
            group_stats = {}
            for result in model_results:
                group_name = result.get("group_name", "未知组")
                if group_name not in group_stats:
                    group_stats[group_name] = {"total": 0, "success": 0, "dangerous": 0}
                group_stats[group_name]["total"] += 1
                if result.get("is_dangerous", False):
                    group_stats[group_name]["dangerous"] += 1
                elif result["success"]:
                    group_stats[group_name]["success"] += 1
            
            # 按组显示统计
            if len(group_stats) > 1:
                print(f"\n    按测试组统计:")
                for group_name, stats in group_stats.items():
                    safe_total = stats["total"] - stats["dangerous"]
                    group_rate = (stats["success"] / safe_total * 100) if safe_total > 0 else 0
                    print(f"      {group_name}: 成功 {stats['success']}/{safe_total}, 危险 {stats['dangerous']} ({group_rate:.2f}%)")
            
            # 显示危险 SQL 详情
            dangerous_cases = [r for r in model_results if r.get("is_dangerous", False)]
            if dangerous_cases:
                print(f"\n    ⚠️  危险 SQL 详情:")
                for i, case in enumerate(dangerous_cases, 1):
                    print(f"      {i}. [{case.get('group_name', '未知组')}] 问题: {case['question']}")
                    print(f"         危险操作: {case.get('dangerous_keyword', '未知')}")
                    print(f"         SQL: {case['sql']}")
            
            # 显示失败详情（不包括危险SQL）
            failures = [r for r in model_results if not r["success"] and not r.get("is_dangerous", False)]
            if failures:
                print(f"\n    失败详情（安全SQL）:")
                for i, failure in enumerate(failures, 1):
                    print(f"      {i}. [{failure.get('group_name', '未知组')}] 问题: {failure['question']}")
                    print(f"         错误: {failure['error']}")
                    if failure['sql']:
                        print(f"         SQL: {failure['sql']}")
        
        # 总体统计（所有模型）
        all_model_results = []
        for model_results in all_results[model_type].values():
            all_model_results.extend(model_results)
        
        if all_model_results:
            total_all = len(all_model_results)
            success_all = sum(1 for r in all_model_results if r["success"])
            dangerous_all = sum(1 for r in all_model_results if r.get("is_dangerous", False))
            safe_all = total_all - dangerous_all
            rate_all = (success_all / safe_all * 100) if safe_all > 0 else 0
            print(f"\n  {model_type.upper()} 总体统计（所有模型）:")
            print(f"    总问题数: {total_all}")
            print(f"    成功执行: {success_all}")
            print(f"    失败: {safe_all - success_all}")
            print(f"    ⚠️  危险 SQL: {dangerous_all}")
            print(f"    安全 SQL 总成功率: {rate_all:.2f}%")
    
    # 保存详细结果到 JSON 文件
    output_file = os.path.join(os.path.dirname(testcase_file), "test_results.json")
    
    # 将结果转换为扁平化格式以便保存
    flattened_results = {
        "openai": [],
        "google": []
    }
    for model_type in ["openai", "google"]:
        for model_name, model_results in all_results[model_type].items():
            flattened_results[model_type].extend(model_results)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_time": datetime.now().isoformat(),
            "test_groups": test_groups,
            "defaults": defaults,
            "results": all_results,
            "results_flat": flattened_results  # 扁平化结果，便于查看
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细结果已保存到: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    import argparse

    
    parser = argparse.ArgumentParser(description="Text2SQL 能力测试脚本")
    parser.add_argument(
        "--testcase",
        default=os.path.join(os.path.dirname(__file__), "testcase.json"),
        help="测试用例文件路径（默认: test_case/testcase.json）"
    )
    parser.add_argument(
        "--openai-model",
        default=None,
        help="OpenAI 模型名称（覆盖配置文件中的设置）"
    )
    parser.add_argument(
        "--google-model",
        default=None,
        help="Google 模型名称（覆盖配置文件中的设置）"
    )
    
    args = parser.parse_args()
    
    # 检查环境变量
    if openai and not os.getenv("OPENAI_API_KEY"):
        print("警告: 未设置 OPENAI_API_KEY 环境变量")
    
    if genai and not os.getenv("GOOGLE_API_KEY"):
        print("警告: 未设置 GOOGLE_API_KEY 环境变量")
    
    run_tests(args.testcase, args.openai_model, args.google_model)

