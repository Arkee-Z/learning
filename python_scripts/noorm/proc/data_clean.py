"""
数据清洗/执行层 - 管理与文件夹重命名和 CSV 标准化相关的清理操作
"""

import logging
import os

from core.folder_noorm import FolderNoorm
from core.csv_noorm import CsvNoorm
from constants.error import NoormError

logger = logging.getLogger("noorm.data_clean")


def clean_run(root_path, dry_run=False, skip_rename=False, skip_csv=False):
    """
    执行完整的清洗/标准化流程。
    封装了 folder_noorm 和 csv_noorm 的完整处理流程。
    返回 (folder_results, csv_result)
    """
    folder_results = []
    csv_result = None

    # 1. 文件夹重命名
    if not skip_rename:
        logger.info("=" * 60)
        logger.info("  文件夹名称标准化" if not dry_run else "  [DRY-RUN] 文件夹名称标准化预览")
        logger.info("=" * 60)

        try:
            fn = FolderNoorm(root_path)
            folder_results = fn.process_all(dry_run=dry_run)

            # 打印汇总
            ready = [r for r in folder_results if r.get("new_name") and r.get("new_name") != r.get("original_name")]
            noorm_skipped = [r for r in folder_results if r.get("new_name") and r.get("new_name") == r.get("original_name")]
            completed = [r for r in folder_results if r.get("success")]
            cp_done = [r for r in folder_results if r.get("message", "").endswith("已全部完成")]
            failed = [r for r in folder_results if not r.get("success") and not r.get("new_name")]

            logger.info("  总计: %d 个文件夹", len(folder_results))
            logger.info("  待重命名: %d 个", len(ready))
            logger.info("  已跳过(已noorm): %d 个", len(noorm_skipped))
            if not dry_run:
                logger.info("  已完成: %d 个", len(completed))
            logger.info("  已完成(全部CP): %d 个", len(cp_done))
            logger.info("  无法处理: %d 个", len(failed))

            if failed:
                logger.warning("  无法处理的文件夹:")
                for r in failed:
                    logger.warning("    - %s: %s", r.get("original_name", ""), r.get("message", ""))

        except Exception as e:
            logger.error("文件夹处理异常: %s", e)
            folder_results = []

    else:
        logger.info("跳过文件夹重命名")

    # 2. CSV 标准化
    if not skip_csv:
        logger.info("=" * 60)
        logger.info("  HealthCheck CSV 标准化" if not dry_run else "  [DRY-RUN] HealthCheck CSV 标准化预览")
        logger.info("=" * 60)

        try:
            cn = CsvNoorm(root_path)
            csv_result = cn.process(folder_results=folder_results, dry_run=dry_run)

            if csv_result and "error" not in csv_result:
                logger.info("  原始行数: %d", csv_result["original_rows"])
                logger.info("  最终行数: %d", csv_result["final_rows"])
                logger.info("  删除空行: %d", csv_result["rows_removed"])
                logger.info("  SN 匹配: %s", "完全匹配" if csv_result["sn_match"] else "存在不匹配")

                if not csv_result["sn_match"] and csv_result["mismatch"]:
                    logger.warning("  不匹配项:")
                    for typ, sn in csv_result["mismatch"]:
                        logger.warning("    %s: %s", typ, sn)
            else:
                logger.error("CSV 处理失败")

        except Exception as e:
            logger.error("CSV 处理异常: %s", e)
            csv_result = {"error": str(e)}
    else:
        logger.info("跳过 CSV 标准化")

    return folder_results, csv_result


def rollback(root_path):
    """
    回滚操作：将修改后的文件夹和 CSV 恢复到原始状态。
    注意：回滚基于备份文件，需谨慎使用。
    返回操作结果日志列表。
    """
    logs = []
    test_logging_dir = None
    base = root_path

    if os.path.isdir(base):
        base_name = os.path.basename(base)
        if base_name == "TestLogging":
            test_logging_dir = base
        else:
            candidate = os.path.join(base, "TestLogging")
            if os.path.isdir(candidate):
                test_logging_dir = candidate
            else:
                test_logging_dir = base

    # 回滚 CSV
    if test_logging_dir:
        for entry in os.listdir(test_logging_dir):
            full_path = os.path.join(test_logging_dir, entry)
            bak_path = full_path + ".bak"
            if os.path.isfile(bak_path):
                try:
                    os.replace(bak_path, full_path)
                    logs.append(f"CSV 已回滚: {entry}")
                    logger.info("CSV 已回滚: %s", entry)
                except OSError as e:
                    logs.append(f"CSV 回滚失败: {entry} - {e}")
                    logger.error("CSV 回滚失败: %s - %s", entry, e)

    logger.info("回滚操作完成" if logs else "无文件需要回滚")
    return logs