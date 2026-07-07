#!/usr/bin/env python3
"""
noorm - REL 测试数据文件夹和报告名称标准化工具

入口文件: python main.py --path <TestLogging路径> [options]
"""

import sys
import os

# 确保项目根目录在 sys.path 中
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from ui.cli import main

if __name__ == "__main__":
    main()