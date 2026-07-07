"""
数据解析层 - 封装 FolderNoorm 和 CsvNoorm 的数据提取逻辑
"""

import logging

from core.folder_noorm import FolderNoorm
from core.csv_noorm import CsvNoorm

logger = logging.getLogger("noorm.data_parser")


def parse_and_process(root_path, dry_run=False, skip_rename=False, skip_csv=False):
    """
    编排整个标准化流程：
    1. 解析并重命名文件夹
    2. 标准化 CSV
    返回 (folder_results, csv_result)
    """
    folder_results = []
    csv_result = None

    # 1. 文件夹处理
    if not skip_rename:
        logger.info("=" * 50)
        logger.info("开始处理文件夹名称标准化")
        logger.info("=" * 50)

        fn = FolderNoorm(root_path)
        folder_results = fn.process_all(dry_run=dry_run)

        # 汇总
        success_count = sum(1 for r in folder_results if r.get("success"))
        fail_count = sum(1 for r in folder_results if r.get("sn") and not r.get("success"))
        logger.info("文件夹处理完成: 成功=%d, 失败=%d, 总计=%d",
                     success_count, fail_count, len(folder_results))
    else:
        logger.info("跳过文件夹重命名")

    # 2. CSV 处理
    if not skip_csv:
        logger.info("=" * 50)
        logger.info("开始处理 HealthCheck CSV 标准化")
        logger.info("=" * 50)

        try:
            cn = CsvNoorm(root_path)
            csv_result = cn.process(
                folder_results=folder_results,
                dry_run=dry_run,
            )
            if csv_result:
                logger.info("CSV 处理完成: rows=%d->%d, 匹配=%s",
                             csv_result["original_rows"],
                             csv_result["final_rows"],
                             csv_result["sn_match"])
        except Exception as e:
            logger.error("CSV 处理失败: %s", e)
            csv_result = {"error": str(e)}
    else:
        logger.info("跳过 CSV 标准化")

    return folder_results, csv_result