"""
命令行交互模块 - noorm CLI 入口

用法:
    python -m noorm.cli --path <TestLogging路径> [options]

选项:
    --path      目标路径（必填）
    --dry-run   仅预览，不执行修改
    --skip-rename  跳过文件夹重命名
    --skip-csv     跳过 CSV 标准化
    --verbose      输出详细日志
    --check        仅检查资源文件和目录结构
"""

import argparse
import logging
import sys
import os

# 确保项目根目录在 sys.path 中
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from proc.data_clean import clean_run, rollback
from proc.data_check import check_assets, check_folders, check_csv

logger = logging.getLogger("noorm.cli")


def setup_logging(verbose=False):
    """配置日志输出格式"""
    level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(level)

    root_logger = logging.getLogger("noorm")
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    # 禁用第三方库的 debug 日志
    for logger_name in ("csv", "json"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def print_header(title):
    """打印格式化标题"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("  %s", title)
    logger.info("=" * 60)


def print_footer():
    """打印结束分隔符"""
    logger.info("=" * 60)
    logger.info("")


def do_check(args):
    """执行检查模式"""
    print_header("noorm 数据检查")
    logger.info("目标路径: %s", args.path)

    # 1. 检查资产文件
    logger.info("")
    logger.info("--- 资产文件检查 ---")
    asset_status = check_assets(args.path)
    for key in ("waterfall", "wfcheck", "regexes"):
        status = "✓" if asset_status.get(key) else "✗"
        logger.info("  %s: %s", key, status)
    if asset_status.get("errors"):
        logger.warning("  异常: %s", asset_status["errors"])
    logger.info("  SN 记录数: %d", asset_status.get("sn_count", 0))

    # 2. 检查文件夹
    logger.info("")
    logger.info("--- 文件夹检查 ---")
    folder_info = check_folders(args.path)
    if folder_info:
        logger.info("  共发现 %d 个文件夹:", len(folder_info))
        for f in folder_info:
            status_icon = {
                "ready": "→",
                "all_completed": "✓",
                "unparseable": "✗",
                "sn_not_found": "✗",
            }.get(f["status"], "?")
            logger.info("  %s %s", status_icon, f["name"])
            if f["status"] == "ready":
                logger.info("        SN: %s, Unit: %s, %s",
                             f["sn"], f["unit_no"], f["cp_info"])
                logger.info("        → %s", f["planned_name"])
            elif f["status"] == "all_completed":
                logger.info("        %s", f["cp_info"])
            elif f["status"] in ("unparseable", "sn_not_found"):
                logger.info("        %s", f["parse_result"])
    else:
        logger.info("  未发现目标文件夹")

    # 3. 检查 CSV
    logger.info("")
    logger.info("--- CSV 检查 ---")
    csv_info = check_csv(args.path)
    if csv_info is None:
        logger.warning("  CSV 检查返回空结果")
    elif "error" in csv_info:
        logger.warning("  %s", csv_info["error"])
    else:
        logger.info("  文件: %s", os.path.basename(csv_info["path"]))
        logger.info("  总行数: %d", csv_info["row_count"])
        logger.info("  有表头: %s", "是" if csv_info.get("has_header") else "否")
        logger.info("  有数据行: %s", "是" if csv_info.get("has_data_rows") else "否")
        logger.info("  有效 SN 数: %d", csv_info.get("sn_count", 0))

    print_footer()


def do_run(args):
    """执行运行模式"""
    mode_str = "DRY-RUN" if args.dry_run else "执行"
    print_header(f"noorm 标准化 [{mode_str}]")
    logger.info("目标路径: %s", args.path)
    logger.info("Dry-run: %s", args.dry_run)
    logger.info("跳过文件夹重命名: %s", args.skip_rename)
    logger.info("跳过 CSV 标准化: %s", args.skip_csv)

    # 执行
    folder_results, csv_result = clean_run(
        args.path,
        dry_run=args.dry_run,
        skip_rename=args.skip_rename,
        skip_csv=args.skip_csv,
    )

    # 打印详细结果
    if folder_results:
        ready = [r for r in folder_results if r.get("new_name")]
        logger.info("")
        logger.info("--- 文件夹处理明细 ---")
        for r in folder_results:
            if r.get("new_name"):
                if args.dry_run:
                    prefix = "[重命名]"
                else:
                    prefix = "[完成]" if r.get("success") else "[跳过]"
                logger.info("  %s %s", prefix, r["original_name"])
                logger.info("          → %s", r["new_name"])
            elif r.get("message"):
                logger.info("  [信息] %s", r["message"])

    if csv_result and "error" not in csv_result:
        logger.info("")
        logger.info("--- CSV 处理明细 ---")
        logger.info("  文件: %s", os.path.basename(str(csv_result["csv_path"])))
        logger.info("  删除空行: %d", csv_result["rows_removed"])
        logger.info("  SN 匹配: %s", "完全匹配 ✓" if csv_result["sn_match"] else "存在不匹配 ⚠")
        if not csv_result["sn_match"] and csv_result.get("mismatch"):
            for typ, sn in csv_result["mismatch"]:
                logger.warning("    不匹配: %s - %s", typ, sn)
    elif csv_result and "error" in csv_result:
        logger.info("")
        logger.info("--- CSV 处理异常 ---")
        logger.info("  %s", csv_result["error"])

    print_footer()


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="noorm - REL 测试数据文件夹和报告名称标准化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --path ./example/TestLogging              # 执行标准化
  python main.py --path ./example/TestLogging --dry-run     # 预览模式
  python main.py --path ./example/TestLogging --check       # 仅检查
  python main.py --path ./example/TestLogging --skip-csv    # 跳过 CSV

说明:
  所有目标对象均包裹在 TestLogging 文件夹中，程序会自动定位该目录。
  传入 --path 时，可直接指向 TestLogging 的父目录或 TestLogging 本身均可。
        """,
    )

    parser.add_argument(
        "--path",
        required=True,
        help="TestLogging 文件夹的父目录（或 TestLogging 自身）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不执行任何修改",
    )
    parser.add_argument(
        "--skip-rename",
        action="store_true",
        help="跳过文件夹重命名",
    )
    parser.add_argument(
        "--skip-csv",
        action="store_true",
        help="跳过 CSV 标准化",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出详细调试日志",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="仅检查资源文件和目录结构，不执行修改",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="回滚操作（基于 .bak 备份恢复 CSV）",
    )

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    # 验证路径
    if not os.path.isdir(args.path):
        logger.error("路径不存在或不是目录: %s", args.path)
        sys.exit(1)

    try:
        if args.rollback:
            print_header("noorm 回滚")
            rollback(args.path)
            print_footer()
        elif args.check:
            do_check(args)
        else:
            do_run(args)
    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error("运行时异常: %s", e, exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main()