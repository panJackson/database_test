# Text2SQL 能力测试

本目录包含用于测试 OpenAI 和 Google 大模型 text2sql 能力的测试脚本。

## 文件说明

- `testcase.json`: 测试用例文件，包含要测试的问题列表
- `test_text2sql.py`: 主测试脚本
- `test_results.json`: 测试结果输出文件（运行后生成）
- `.env`: 环境变量配置文件（需要自己创建，不要提交到版本控制）
- `.env.example`: `.env` 文件示例（可选，用于参考）
- `run_background.sh`: 后台运行脚本（macOS/Linux）
- `stop_background.sh`: 停止后台测试脚本（macOS/Linux）
- `status_background.sh`: 查看运行状态脚本（macOS/Linux）
- `view_log.sh`: 查看日志脚本（macOS/Linux）
- `run_background.ps1`: 后台运行脚本（Windows PowerShell）
- `stop_background.ps1`: 停止后台测试脚本（Windows PowerShell）
- `logs/`: 日志文件目录（自动创建）

## 环境要求

### Python 依赖

```bash
pip install -r test_case/requirements.txt
```

或者手动安装：

```bash
pip install openai google-generativeai pymysql python-dotenv
```

### 环境变量配置

有两种方式配置 API Key：

#### 方式一：使用 .env 文件（推荐）

1. 在 `test_case` 目录或项目根目录创建 `.env` 文件：

```bash
# 在 test_case 目录下创建
cd test_case
touch .env
```

2. 编辑 `.env` 文件，添加你的 API Key：

```bash
# OpenAI API 配置
OPENAI_API_KEY=your-openai-api-key-here

# Google API 配置
GOOGLE_API_KEY=your-google-api-key-here
```

3. 脚本会自动加载 `.env` 文件，无需手动设置环境变量

**注意**：
- `.env` 文件包含敏感信息，不要提交到版本控制系统
- 脚本会按以下顺序查找 `.env` 文件：
  1. `test_case/.env`
  2. 项目根目录 `.env`

#### 方式二：使用环境变量

如果不想使用 `.env` 文件，也可以直接设置环境变量：

```bash
# OpenAI API Key（用于测试 OpenAI 模型）
export OPENAI_API_KEY="your-openai-api-key"

# Google API Key（用于测试 Google 模型）
export GOOGLE_API_KEY="your-google-api-key"
```

**优先级**：环境变量 > .env 文件（如果同时设置，环境变量优先）

#### 方式三：使用辅助脚本加载到环境变量

如果你想让 `.env` 文件中的配置在终端会话中生效，可以使用提供的辅助脚本：

**macOS/Linux (bash/zsh)**:
```bash
# 在终端中执行
source test_case/load_env.sh

# 或者添加到 ~/.zshrc 或 ~/.bashrc 中
echo 'source /path/to/sportsqa/test_case/load_env.sh' >> ~/.zshrc
```

**Windows (PowerShell)**:
```powershell
# 在 PowerShell 中执行
. test_case\load_env.ps1
```

### 设置系统环境变量（永久生效）

如果你想永久设置环境变量到系统中：

#### macOS/Linux

1. **编辑 shell 配置文件**：

```bash
# 对于 zsh (macOS 默认)
nano ~/.zshrc

# 对于 bash
nano ~/.bashrc
# 或
nano ~/.bash_profile
```

2. **添加以下内容**：

```bash
# OpenAI API Key
export OPENAI_API_KEY="sk-your-openai-api-key-here"

# Google API Key
export GOOGLE_API_KEY="your-google-api-key-here"
```

3. **重新加载配置**：

```bash
source ~/.zshrc  # 或 source ~/.bashrc
```

4. **验证设置**：

```bash
echo $OPENAI_API_KEY
echo $GOOGLE_API_KEY
```

#### Windows

**方法一：通过 PowerShell（推荐）**

```powershell
# 设置用户级环境变量（永久）
[System.Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'sk-your-openai-api-key', 'User')
[System.Environment]::SetEnvironmentVariable('GOOGLE_API_KEY', 'your-google-api-key', 'User')

# 重启终端后生效
```

**方法二：通过系统设置（图形界面）**

1. 右键"此电脑" → 属性
2. 点击"高级系统设置"
3. 点击"环境变量"
4. 在"用户变量"中点击"新建"
5. 添加变量名：`OPENAI_API_KEY`，变量值：`sk-your-key`
6. 同样添加 `GOOGLE_API_KEY`
7. 重启终端或重新登录

## 使用方法

### 基本用法（前台运行）

```bash
# 使用默认配置运行测试
python test_case/test_text2sql.py

# 指定测试用例文件
python test_case/test_text2sql.py --testcase test_case/testcase.json

# 指定模型
python test_case/test_text2sql.py --openai-model gpt-4o --google-model gemini-2.0-flash-exp
```

### 后台运行（推荐用于长时间测试）

#### macOS/Linux

```bash
# 启动后台测试
./test_case/run_background.sh

# 或者指定参数
./test_case/run_background.sh --testcase test_case/testcase.json --openai-model gpt-4o

# 查看运行状态
./test_case/status_background.sh

# 实时查看日志
./test_case/view_log.sh

# 或者查看指定日志文件
./test_case/view_log.sh logs/test_text2sql_20250101_120000.log

# 停止后台测试
./test_case/stop_background.sh
```

#### Windows PowerShell

```powershell
# 启动后台测试
.\test_case\run_background.ps1

# 查看日志（实时）
Get-Content test_case\logs\test_text2sql_*.log -Wait -Tail 50

# 停止后台测试
.\test_case\stop_background.ps1
```

### 后台运行说明

- **日志文件**: 所有输出（包括标准输出和错误输出）都会保存到 `logs/test_text2sql_YYYYMMDD_HHMMSS.log`
- **PID 文件**: 进程 ID 保存在 `test_text2sql.pid`，用于管理和停止进程
- **自动创建**: 日志目录会自动创建
- **防止重复**: 如果测试已在运行，会提示并退出

### 参数说明

- `--testcase`: 测试用例文件路径（默认: `test_case/testcase.json`）
- `--openai-model`: OpenAI 模型名称（覆盖配置文件中的所有设置）
- `--google-model`: Google 模型名称（覆盖配置文件中的所有设置）

注意：命令行参数会覆盖配置文件中的所有模型设置，适用于快速测试不同模型。

## 测试用例格式

`testcase.json` 文件支持两种格式：

### 新格式（推荐）- 支持分组和自定义提示词

```json
{
  "default_prompt": "默认提示词（可选，如果测试组未指定则使用此提示词）",
  "default_openai_model": ["gpt-4o"],
  "default_google_model": ["gemini-2.0-flash-exp"],
  "test_groups": [
    {
      "name": "测试组1",
      "prompt": "此组的提示词（可选，如果不指定则使用 default_prompt）",
      "openai_model": ["gpt-4o", "gpt-4o-mini"],
      "google_model": ["gemini-2.0-flash-exp", "gemini-1.5-pro"],
      "questions": [
        "问题1",
        "问题2"
      ]
    },
    {
      "name": "测试组2",
      "prompt": "另一个提示词",
      "openai_model": ["gpt-4o-mini"],
      "google_model": ["gemini-1.5-pro"],
      "questions": [
        "问题3",
        "问题4"
      ]
    }
  ]
}
```

### 旧格式（向后兼容）

```json
{
  "questions": [
    "问题1",
    "问题2",
    "问题3"
  ]
}
```

### 配置说明

- **default_prompt**: 默认提示词，如果测试组未指定 `prompt`，则使用此提示词。如果提示词中不包含"数据库表结构"，脚本会自动补充完整的数据库结构说明。
- **default_openai_model**: 默认 OpenAI 模型名称或模型数组（数组格式：`["gpt-4o"]` 或 `["gpt-4o", "gpt-4o-mini"]`）
- **default_google_model**: 默认 Google 模型名称或模型数组（数组格式：`["gemini-2.0-flash-exp"]` 或 `["gemini-2.0-flash-exp", "gemini-1.5-pro"]`）
- **test_groups**: 测试组数组，每个组可以有自己的配置
  - **name**: 测试组名称（可选）
  - **prompt**: 该组的提示词（可选，不指定则使用 default_prompt）
  - **openai_model**: 该组使用的 OpenAI 模型或模型数组（可选，不指定则使用 default_openai_model）
    - 可以是字符串：`"gpt-4o"`（单个模型）
    - 可以是数组：`["gpt-4o", "gpt-4o-mini"]`（多个模型，会对每个问题测试所有模型）
  - **google_model**: 该组使用的 Google 模型或模型数组（可选，不指定则使用 default_google_model）
    - 可以是字符串：`"gemini-2.0-flash-exp"`（单个模型）
    - 可以是数组：`["gemini-2.0-flash-exp", "gemini-1.5-pro"]`（多个模型，会对每个问题测试所有模型）
  - **questions**: 该组的问题列表

### 模型数组说明

- **支持多个模型**：`openai_model` 和 `google_model` 可以是数组，脚本会对每个问题使用所有配置的模型进行测试
- **向后兼容**：仍然支持字符串格式（单个模型），会自动转换为数组
- **统计分离**：每个模型的测试结果会单独统计，便于对比不同模型的性能

### 提示词说明

- 如果提示词中不包含"数据库表结构"关键字，脚本会自动在提示词末尾添加完整的数据库表结构说明
- 提示词可以使用 `\n` 表示换行
- 建议在提示词中明确说明需要返回 SQL 语句，不要包含其他解释

## 测试流程

1. 读取 `testcase.json` 中的问题列表
2. 对每个问题，分别使用 OpenAI 和 Google 模型生成 SQL
3. 执行生成的 SQL 语句
4. 统计执行成功率
5. 生成测试报告并保存到 `test_results.json`

## 测试结果

测试脚本会输出：

1. **控制台输出**：
   - 每个问题的测试进度
   - SQL 生成和执行结果
   - 最终统计信息（成功率、失败详情等）

2. **JSON 结果文件** (`test_results.json`)：
   - 包含所有测试的详细结果
   - 包括问题、生成的 SQL、执行结果、错误信息等

## 示例输出

```
================================================================================
Text2SQL 能力测试
================================================================================
测试时间: 2025-01-XX XX:XX:XX
OpenAI 模型: gpt-4o
Google 模型: gemini-2.0-flash-exp
================================================================================

加载了 2 个测试问题

开始测试 OpenAI 模型...

[1/2] OpenAI - aaaaa
  ✓ SQL 执行成功，返回 0 条记录
  SQL: SELECT * FROM sportradar_tennis_competition LIMIT 50;

[2/2] OpenAI - bbbbb
  ✗ 失败: 仅允许 SELECT 查询语句
  SQL: INSERT INTO ...

================================================================================
开始测试 Google 模型...
...

================================================================================
测试结果统计
================================================================================

OPENAI 模型 (gpt-4o):
  总问题数: 2
  成功执行: 1
  失败: 1
  成功率: 50.00%

  失败详情:
    1. 问题: bbbbb
       错误: 仅允许 SELECT 查询语句
       SQL: INSERT INTO ...

GOOGLE 模型 (gemini-2.0-flash-exp):
  总问题数: 2
  成功执行: 2
  失败: 0
  成功率: 100.00%

详细结果已保存到: test_case/test_results.json
================================================================================
```

## 注意事项

1. 确保数据库连接配置正确（在 `config.json` 中配置）
2. 确保有足够的 API 配额
3. SQL 执行有安全限制：
   - 仅允许 SELECT 查询
   - 必须包含 LIMIT 子句
   - LIMIT 值不能超过 50
   - 只能访问允许的表

## 故障排除

### API Key 未找到

**问题**：提示 "未设置 OPENAI_API_KEY 环境变量" 或 "未设置 GOOGLE_API_KEY 环境变量"

**解决方案**：
1. 确认已创建 `.env` 文件
2. 检查 `.env` 文件中的 key 名称是否正确（`OPENAI_API_KEY` 和 `GOOGLE_API_KEY`）
3. 确认 `.env` 文件位置正确（`test_case/.env` 或项目根目录 `.env`）
4. 确认已安装 `python-dotenv`：`pip install python-dotenv`
5. 或者直接设置环境变量：`export OPENAI_API_KEY="your-key"`

### OpenAI API 错误
- 检查 `OPENAI_API_KEY` 是否正确设置（环境变量或 `.env` 文件）
- 确认 API 密钥有效且有足够配额
- 检查网络连接是否正常

### Google API 错误
- 检查 `GOOGLE_API_KEY` 是否正确设置（环境变量或 `.env` 文件）
- 确认 API 密钥有效且有足够配额
- 检查网络连接是否正常

### 数据库连接错误
- 检查 `config.json` 中的数据库配置
- 确认数据库服务可访问
- 确认数据库用户权限正确

### SQL 执行失败
- 检查生成的 SQL 是否符合安全规则
- 查看错误信息了解具体原因
- 检查是否生成了危险 SQL（UPDATE、DELETE 等）

### .env 文件未加载

**问题**：已创建 `.env` 文件但脚本仍提示未设置环境变量

**解决方案**：
1. 确认 `.env` 文件格式正确（每行一个 key=value，不要有引号）
2. 确认文件位置：优先查找 `test_case/.env`，然后是项目根目录 `.env`
3. 检查文件权限：确保脚本有读取权限
4. 尝试使用绝对路径：在代码中明确指定 `.env` 文件路径

