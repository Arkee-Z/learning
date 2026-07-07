"""
CSV 标准化模块 - CsvNoorm

负责在 TestLogging 中定位 FATP-HealthCheck CSV 文件，
进行表头重命名、SN 空行清理、以及 SN 与文件夹名称的交叉校验。
"""

import os
import csv
import re
import logging
from io import StringIO

from constants.error import HealthCheckCSVNotFoundError

logger = logging.getLogger("noorm.csv_noorm")


# 表头重命名映射: {old_header: (new_header, row_index, col_index)}
# row_index=0 表示第一行（表头行），0,0 即 header (0,0) 处
HEADER_MAP = {
    "MpToolLib": ("Touch Station", 0, 0),
    "serialnumber": ("SerialNumber", 1, 0),
    "overallResult": ("Test Pass/Fail Status", 1, 1),
    "startTime": ("StartTime", 1, 5),
}


class CsvNoorm:
    """
    HealthCheck CSV 标准化处理器
    """

    def __init__(self, root_path):
        self.root_path = root_path
        self.csv_path = None
        self.found_csv = None  # 最终找到的 CSV 文件路径

    # ---- 查找 CSV ----

    def find_healthcheck_csv(self):
        """
        在 TestLogging 目录下查找符合 healthcheck_csv 模式的 CSV 文件。
        调用者只需提供上层目录即可，本方法自动定位 TestLogging。
        """
        base = self.root_path
        if not os.path.isdir(base):
            raise NotADirectoryError(f"路径不存在: {base}")

        base_name = os.path.basename(base)
        if base_name == "TestLogging":
            test_logging_dir = base
        else:
            candidate = os.path.join(base, "TestLogging")
            if os.path.isdir(candidate):
                test_logging_dir = candidate
            else:
                raise FileNotFoundError(
                    f"在路径 [{base}] 下未找到 TestLogging 目录"
                )

        # 编译 healthcheck_csv 正则
        hc_re = re.compile(
            self._get_pattern("healthcheck_csv", r"^FATP-HealthCheck__.*\.csv$"),
            re.IGNORECASE,
        )

        for entry in os.listdir(test_logging_dir):
            full_path = os.path.join(test_logging_dir, entry)
            if os.path.isfile(full_path) and hc_re.match(entry):
                self.found_csv = full_path
                logger.info("找到 HealthCheck CSV: %s", os.path.basename(full_path))
                return full_path

        raise HealthCheckCSVNotFoundError(self.root_path)

    def _get_pattern(self, key, default):
        """尝试从 _regexes.json 获取模式，否则使用默认值"""
        import json
        assets_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets"
        )
        regex_path = os.path.join(assets_dir, "_regexes.json")
        if os.path.isfile(regex_path):
            try:
                with open(regex_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get(key, default)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return default

    # ---- CSV 读写 ----

    def read_csv(self, csv_path=None):
        """读取 CSV 文件，返回 (headers, rows) 其中 rows 包含 header 行。"""
        if csv_path is None:
            csv_path = self.found_csv
        if csv_path is None:
            csv_path = self.find_healthcheck_csv()

        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()

        reader = csv.reader(StringIO(content))
        rows = []
        for row in reader:
            rows.append(row)
        return rows

    def write_csv(self, rows, csv_path=None):
        """将修改后的 rows 写回 CSV 文件。"""
        if csv_path is None:
            csv_path = self.found_csv
        if csv_path is None:
            raise ValueError("未指定 CSV 路径，请先调用 find_healthcheck_csv()")

        # 备份原文件
        bak_path = csv_path + ".bak"
        if not os.path.exists(bak_path):
            try:
                os.rename(csv_path, bak_path)
                logger.info("原文件备份至: %s", bak_path)
            except OSError as e:
                logger.error("备份失败: %s", e)

        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)
        logger.info("已写入标准化 CSV: %s", os.path.basename(csv_path))

    # ---- 标准化操作 ----

    def standardize_headers(self, rows):
        """
        根据 HEADER_MAP 替换表头。
        row 0 为表头行 (header row)，部分映射作用于 row 1 需要调整列位置。
        """
        if not rows:
            return rows

        modified = False

        # 处理 header row (row 0)
        header_row = list(rows[0]) if len(rows) > 0 else []
        for old_hdr, (new_hdr, r_idx, c_idx) in HEADER_MAP.items():
            if r_idx == 0:
                # 在原地查找并替换 (0, c_idx) — 但更好的方式是在 header 中匹配字符串
                for i, h in enumerate(header_row):
                    if h.strip() == old_hdr:
                        header_row[i] = new_hdr
                        modified = True
                        logger.debug("表头替换: %s -> %s (col %d)", old_hdr, new_hdr, i)
                        break
        rows[0] = header_row

        # 处理 row 1 (r_idx=1)，需要更新特定列
        if len(rows) > 1:
            row1 = list(rows[1])
            for old_hdr, (new_hdr, r_idx, c_idx) in HEADER_MAP.items():
                if r_idx == 1:
                    # 需要指定列坐标的情况（如 startTime 在 (1,5)）
                    if c_idx < len(row1):
                        old_val = row1[c_idx]
                        row1[c_idx] = new_hdr
                        modified = True
                        logger.debug("Row1 列%d 替换: %s -> %s", c_idx, old_val, new_hdr)
            rows[1] = row1

        if modified:
            logger.info("表头标准化完成")
        else:
            logger.info("表头无需修改")

        return rows

    def clear_row_zero_except_first(self, rows):
        """
        将 row 0 中除 (0,0) 以外的所有单元格置空。
        """
        if not rows:
            return rows

        row0 = list(rows[0])
        modified = False
        for i in range(1, len(row0)):
            if row0[i]:
                row0[i] = ""
                modified = True
        rows[0] = row0

        if modified:
            logger.info("Row0 首列之外已置空")
        else:
            logger.info("Row0 首列之外无需处理")

        return rows

    def remove_empty_sn_rows(self, rows):
        """
        删除第一列（SN 列）为空或为元数据描述的数据行。
        保留 row 0 (header) 和 row 1 (limit descriptors/空行) 的元数据行。
        """
        if not rows:
            return rows

        new_rows = []
        removed_count = 0

        for idx, row in enumerate(rows):
            # 保留前2行不动（header 行和 limit 描述行）
            if idx < 2:
                new_rows.append(row)
                continue

            sn_val = row[0].strip() if len(row) > 0 else ""

            # 检查第一列是否为空，或为 limit 描述文字
            if not sn_val:
                removed_count += 1
                continue

            new_rows.append(row)

        if removed_count > 0:
            logger.info("删除了 %d 个非数据行（空 SN/limit 行）", removed_count)
        else:
            logger.info("没有需要删除的空 SN 行")

        return new_rows

    # ---- 交叉校验 ----

    def validate_sn_match(self, csv_rows, processed_folders):
        """
        校验 HealthCheck CSV 中的 SN 列与已处理的文件夹 SN 列表是否匹配。
        processed_folders: [{"sn": "...", "original_name": "..."}]
        返回 (is_match, match_count, mismatch_list)
        """
        if not csv_rows:
            return False, 0, []

        # 收集 CSV 中的 SN（跳过前 2 行元数据和 limit 描述行）
        csv_sns = set()
        for idx, row in enumerate(csv_rows):
            if idx < 2:
                continue
            sn_val = row[0].strip() if len(row) > 0 else ""
            if sn_val and not sn_val.startswith("Upper") and not sn_val.startswith("Lower"):
                csv_sns.add(sn_val)

        # 收集已处理文件夹的 SN
        folder_sns = set()
        for f in processed_folders:
            if f.get("sn"):
                folder_sns.add(f["sn"])

        if not csv_sns or not folder_sns:
            return False, 0, []

        # 计算交集
        common = csv_sns & folder_sns
        mismatch = []

        for sn in csv_sns:
            if sn not in folder_sns:
                mismatch.append(("csv_only", sn))
        for sn in folder_sns:
            if sn not in csv_sns:
                mismatch.append(("folder_only", sn))

        is_match = len(mismatch) == 0

        if is_match:
            logger.info("CSV 与文件夹 SN 完全匹配，共 %d 个", len(common))
        else:
            logger.warning("CSV 与文件夹 SN 存在 %d 处不匹配:", len(mismatch))
            for typ, sn in mismatch:
                logger.warning("  %s: %s", typ, sn)

        return is_match, len(common), mismatch

    # ---- 完整处理 ----

    def process(self, csv_path=None, folder_results=None, dry_run=False):
        """
        完整执行 CSV 标准化流程。
        """
        if csv_path is not None:
            self.found_csv = csv_path
        elif self.found_csv is None:
            self.find_healthcheck_csv()

        csv_path_str = str(self.found_csv) if self.found_csv else ""
        logger.info("开始处理 CSV: %s", os.path.basename(csv_path_str))

        # 1. 读取
        rows = self.read_csv(self.found_csv)
        original_row_count = len(rows)

        # 2. 表头标准化
        rows = self.standardize_headers(rows)

        # 3. 清空 row0 首列以外
        rows = self.clear_row_zero_except_first(rows)

        # 4. 删除空 SN 行
        rows = self.remove_empty_sn_rows(rows)

        # 5. 交叉校验
        if folder_results:
            is_match, match_count, mismatch = self.validate_sn_match(
                rows, folder_results
            )
        else:
            is_match, match_count, mismatch = True, 0, []

        # 6. 写入
        if not dry_run:
            self.write_csv(rows)
        else:
            logger.info("[DRY-RUN] 跳过 CSV 写入")

        return {
            "csv_path": self.found_csv,
            "original_rows": original_row_count,
            "final_rows": len(rows),
            "rows_removed": original_row_count - len(rows),
            "sn_match": is_match,
            "match_count": match_count,
            "mismatch": mismatch,
            "dry_run": dry_run,
        }