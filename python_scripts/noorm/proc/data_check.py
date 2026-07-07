"""
数据校验层 - 在 dry-run 模式下预览并校验所有待执行的操作
"""

import logging
import os

from core.folder_noorm import FolderNoorm
from core.csv_noorm import CsvNoorm
from constants.error import SNNotFoundError, InvalidAssetDataError

logger = logging.getLogger("noorm.data_check")


def check_assets(root_path):
    """
    检查资源文件完整性并返回加载状态。
    """
    status = {"waterfall": False, "wfcheck": False, "regexes": False, "errors": []}
    try:
        fn = FolderNoorm(root_path)
        status["waterfall"] = len(fn.waterfall) > 0
        status["wfcheck"] = len(fn.wfcheck) > 0
        status["regexes"] = len(fn.regexes) > 0
        status["sn_count"] = len(fn.waterfall)
    except Exception as e:
        status["errors"].append(str(e))
    return status


def check_folders(root_path):
    """
    预览所有目标文件夹的待处理信息。
    使用 FolderNoorm 的 process_all(dry_run=True) 但返回更详细的信息。
    """
    fn = FolderNoorm(root_path)
    results = []

    for folder_name, folder_path in fn._iter_target_folders():
        info = {
            "name": folder_name,
            "path": folder_path,
            "parse_result": None,
            "sn": None,
            "unit_no": None,
            "cp_info": None,
            "has_fail": False,
            "planned_name": None,
            "status": "pending",
        }

        # 解析
        parsed = fn.parse_folder_name(folder_name)
        if not parsed:
            info["status"] = "unparseable"
            info["parse_result"] = "无法解析"
            results.append(info)
            continue

        info["parse_result"] = parsed
        sn = parsed.get("sn", "")
        info["sn"] = sn

        # 查 SN
        wf_record = fn._find_sn_in_waterfall(sn)
        if not wf_record:
            info["status"] = "sn_not_found"
            info["parse_result"] = f"SN [{sn}] 未在 waterfall 中找到"
            results.append(info)
            continue

        info["unit_no"] = wf_record["unit_no"]

        # 查 CP
        try:
            cp_index, cp_name = fn.get_next_incomplete_cp(sn)
        except SNNotFoundError as e:
            info["status"] = "sn_not_found"
            info["parse_result"] = str(e)
            results.append(info)
            continue

        if cp_index is None:
            info["status"] = "all_completed"
            info["cp_info"] = "所有 CP 已完成"
            results.append(info)
            continue

        info["cp_info"] = f"CP{cp_index}: {cp_name}"

        # 检测 Fail 日志
        info["has_fail"] = fn.has_fail_logs(folder_path)

        # 生成标准名
        new_name = fn.build_standard_name(
            sn, info["unit_no"], cp_index, cp_name, parsed, info["has_fail"]
        )
        info["planned_name"] = new_name
        info["status"] = "ready"

        results.append(info)

    return results


def check_csv(root_path):
    """
    预览 CSV 标准化操作。
    """
    try:
        cn = CsvNoorm(root_path)
        csv_path = cn.find_healthcheck_csv()
        rows = cn.read_csv(csv_path)

        return {
            "path": csv_path,
            "row_count": len(rows),
            "has_header": len(rows) > 0,
            "has_data_rows": len(rows) > 2,
            "sn_count": sum(1 for r in rows[2:] if len(r) > 0 and r[0].strip() and not r[0].strip().startswith(("Upper", "Lower"))),
        }
    except Exception as e:
        logger.error("检查 CSV 异常: %s", e)
        return {"error": str(e)}