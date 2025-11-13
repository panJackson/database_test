#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新环境变量的工具脚本
从 .env 文件读取并设置到系统环境变量（当前 Python 进程）
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from test_case.test_text2sql import load_env_file, set_env_var


def main():
    """主函数：更新环境变量"""
    print("正在从 .env 文件更新环境变量...")
    
    # 加载 .env 文件
    success = load_env_file()
    
    if success:
        print("✓ 环境变量已更新！")
        
        # 显示更新后的值（只显示前几个字符）
        openai_key = os.getenv("OPENAI_API_KEY", "")
        google_key = os.getenv("GOOGLE_API_KEY", "")
        
        if openai_key:
            print(f"  OPENAI_API_KEY: {openai_key[:20]}...")
        else:
            print("  OPENAI_API_KEY: 未设置")
        
        if google_key:
            print(f"  GOOGLE_API_KEY: {google_key[:20]}...")
        else:
            print("  GOOGLE_API_KEY: 未设置")
    else:
        print("✗ 未找到 .env 文件或加载失败")
        print("\n提示：")
        print("  1. 确保 .env 文件存在于 test_case/.env 或项目根目录")
        print("  2. 检查文件格式是否正确（key=value）")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

