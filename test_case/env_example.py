#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python 中设置环境变量的示例代码
演示如何使用 os.environ 设置和更新环境变量
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from test_case.test_text2sql import set_env_var, update_env_from_file, load_env_file


def example_1_direct_set():
    """示例1: 直接使用 os.environ 设置环境变量"""
    print("=" * 60)
    print("示例1: 直接使用 os.environ 设置环境变量")
    print("=" * 60)
    
    # 方法1: 使用字典方式设置
    os.environ['OPENAI_API_KEY'] = 'sk-your-new-key-here'
    os.environ['GOOGLE_API_KEY'] = 'your-new-google-key-here'
    
    # 方法2: 使用 setdefault（如果不存在才设置）
    os.environ.setdefault('OPENAI_API_KEY', 'sk-default-key')
    
    # 读取环境变量
    openai_key = os.environ.get('OPENAI_API_KEY')
    google_key = os.environ.get('GOOGLE_API_KEY')
    
    print(f"OPENAI_API_KEY: {openai_key[:20] if openai_key else '未设置'}...")
    print(f"GOOGLE_API_KEY: {google_key[:20] if google_key else '未设置'}...")
    print()


def example_2_using_helper_function():
    """示例2: 使用辅助函数设置环境变量"""
    print("=" * 60)
    print("示例2: 使用辅助函数设置环境变量")
    print("=" * 60)
    
    # 使用 set_env_var 函数
    set_env_var('OPENAI_API_KEY', 'sk-new-key-from-function')
    set_env_var('GOOGLE_API_KEY', 'new-google-key-from-function', override=True)
    
    # 读取验证
    print(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY', '未设置')[:20]}...")
    print(f"GOOGLE_API_KEY: {os.getenv('GOOGLE_API_KEY', '未设置')[:20]}...")
    print()


def example_3_update_from_env_file():
    """示例3: 从 .env 文件更新环境变量"""
    print("=" * 60)
    print("示例3: 从 .env 文件更新环境变量")
    print("=" * 60)
    
    # 从 .env 文件加载并更新环境变量
    success = update_env_from_file()
    
    if success:
        print("✓ 成功从 .env 文件更新环境变量")
        print(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY', '未设置')[:20]}...")
        print(f"GOOGLE_API_KEY: {os.getenv('GOOGLE_API_KEY', '未设置')[:20]}...")
    else:
        print("✗ 未找到 .env 文件")
    print()


def example_4_check_before_set():
    """示例4: 检查环境变量是否存在，不存在才设置"""
    print("=" * 60)
    print("示例4: 检查环境变量是否存在，不存在才设置")
    print("=" * 60)
    
    # 检查是否存在
    if 'OPENAI_API_KEY' not in os.environ:
        os.environ['OPENAI_API_KEY'] = 'sk-default-key'
        print("设置了默认的 OPENAI_API_KEY")
    else:
        print(f"OPENAI_API_KEY 已存在: {os.environ['OPENAI_API_KEY'][:20]}...")
    
    # 或者使用 get 方法设置默认值（不修改环境变量）
    key = os.environ.get('OPENAI_API_KEY', 'sk-default-value')
    print(f"当前值: {key[:20]}...")
    print()


def example_5_batch_update():
    """示例5: 批量更新环境变量"""
    print("=" * 60)
    print("示例5: 批量更新环境变量")
    print("=" * 60)
    
    # 定义要更新的环境变量字典
    env_vars = {
        'OPENAI_API_KEY': 'sk-batch-update-key',
        'GOOGLE_API_KEY': 'batch-update-google-key',
        'CUSTOM_VAR': 'custom-value'
    }
    
    # 批量设置
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"设置 {key} = {value[:20]}...")
    print()


def example_6_override_existing():
    """示例6: 强制覆盖已存在的环境变量"""
    print("=" * 60)
    print("示例6: 强制覆盖已存在的环境变量")
    print("=" * 60)
    
    # 先设置一个值
    os.environ['TEST_VAR'] = 'old-value'
    print(f"原始值: {os.environ['TEST_VAR']}")
    
    # 强制覆盖
    os.environ['TEST_VAR'] = 'new-value'
    print(f"覆盖后: {os.environ['TEST_VAR']}")
    
    # 或者使用 set_env_var 函数（override=True）
    set_env_var('TEST_VAR', 'newer-value', override=True)
    print(f"再次覆盖: {os.environ['TEST_VAR']}")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Python 环境变量设置示例")
    print("=" * 60 + "\n")
    
    # 运行所有示例
    example_1_direct_set()
    example_2_using_helper_function()
    example_3_update_from_env_file()
    example_4_check_before_set()
    example_5_batch_update()
    example_6_override_existing()
    
    print("=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)

