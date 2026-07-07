"""
文件夹名称标准化模块 - FolderNoorm

负责扫描 TestLogging 文件夹、解析文件夹名称、检查 CP 状态、
检测 Fail 日志并生成标准名称后执行重命名。
"""

import os
import re
import csv
import json
import shutil
import logging

from constants.error import (
    SNNotFoundError,
    AllCPCompletedError,
    FolderParseError,
    InvalidAssetDataError,
)

logger = logging.getLogger("noorm.folder_noorm")

# 资产文件路径（相对于项目根目录）
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


class FolderNoorm:
    """
    文件夹标准化处理器
    """

    def __init__(self, root_path):
        self.root_path = root_path
        self.regexes = {}           # 加载的正则字典
        self.sn_re = None           # SN 正则对象
        self.noorm_patterns = []    # 已标准化的文件夹匹配 pattern 列表（编译后）
        self.folder_patterns = []   # 未标准化文件夹名解析 pattern 列表（编译后）
        self.waterfall = {}         # {sn: {unit_no, cps: [cp0...cp7]}}
        self.wfcheck = {}           # {sn: [y/n for cp0...cp7]}
        self._load_regexes()
        self._load_waterfall()
        self._load_wfcheck()

    # ---- 资产加载 ----

    def _load_regexes(self):
        """加载 _regexes.json"""
        path = os.path.join(_ASSETS_DIR, "_regexes.json")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"正则配置文件不存在: {path}")
        with open(path, "r", encoding="utf-8") as f:
            self.regexes = json.load(f)

        # 编译 sn 正则
        self.sn_re = re.compile(self.regexes["sn"])

        # 编译已标准化 pattern 列表（noorm_patterns 优先检查）
        self.noorm_patterns = [
            re.compile(p) for p in self.regexes.get("noorm_patterns", [])
        ]

        # 编译文件夹解析 pattern 列表
        self.folder_patterns = [
            re.compile(p) for p in self.regexes.get("folder_patterns", [])
        ]

    def _load_waterfall(self):
        """加载 _waterfall.csv -> {sn: {unit_no, cps}}"""
        path = os.path.join(_ASSETS_DIR, "_waterfall.csv")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"waterfall 文件不存在: {path}")
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sn = row.get("SN", "").strip()
                if not sn:
                    continue
                unit_no = row.get("Unit_No", "").strip()
                cps = []
                for i in range(8):
                    cp_key = f"CP{i}"
                    cp_val = row.get(cp_key, "").strip()
                    cps.append(cp_val)
                self.waterfall[sn] = {"unit_no": unit_no, "cps": cps}

    def _load_wfcheck(self):
        """加载 _wfcheck.csv -> {sn: [Y/N string for cp0..cp7]}"""
        path = os.path.join(_ASSETS_DIR, "_wfcheck.csv")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"wfcheck 文件不存在: {path}")
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sn = row.get("SN", "").strip()
                if not sn:
                    continue
                statuses = []
                for i in range(8):
                    cp_key = f"CP{i}"
                    val = row.get(cp_key, "").strip().upper()
                    statuses.append(val)
                self.wfcheck[sn] = statuses

    # ---- 文件夹扫描 ----

    def _get_test_logging_dir(self):
        """
        返回 TestLogging 目录的真实路径。
        若 root_path 本身即 TestLogging，返回它自己。
        否则查找 root_path 下的 TestLogging 子目录。
        """
        base = self.root_path
        if not os.path.isdir(base):
            raise NotADirectoryError(f"路径不存在: {base}")

        base_name = os.path.basename(base)
        if base_name == "TestLogging":
            return base

        candidate = os.path.join(base, "TestLogging")
        if os.path.isdir(candidate):
            return candidate

        raise FileNotFoundError(
            f"在路径 [{base}] 下未找到 TestLogging 目录"
        )

    def _iter_target_folders(self):
        """
        遍历 TestLogging 下的直接子目录。
        调用者只需提供上层目录即可，本方法自动定位 TestLogging。
        """
        test_logging_dir = self._get_test_logging_dir()

        for entry in os.listdir(test_logging_dir):
            full_path = os.path.join(test_logging_dir, entry)
            if os.path.isdir(full_path):
                # 排除隐藏目录
                if entry.startswith("."):
                    continue
                yield entry, full_path

    # ---- 文件夹名解析 ----

    def check_already_noormed(self, folder_name):
        """
        检查文件夹名是否已经是 noorm 标准化格式 (#{id}_{checkpoint}_{sn}_{timestamp})。
        如果是，返回 dict (sn, id, checkpoint, date, time) 否则返回 None。
        """
        for pattern in self.noorm_patterns:
            m = pattern.match(folder_name)
            if m:
                return {
                    "sn": m.group("sn"),
                    "id": m.group("id"),
                    "checkpoint": m.group("checkpoint"),
                    "date": m.group("date"),
                    "time": m.group("time"),
                }
        return None

    def parse_folder_name(self, folder_name):
        """
        使用 folder_patterns 列表解析原始（未标准化）文件夹名。
        返回 dict (sn, id, date, time, full_match) 或 None。
        """
        for idx, pattern in enumerate(self.folder_patterns):
            m = pattern.match(folder_name)
            if m:
                result = {"full_match": m.group(0), "pattern_index": idx}
                # 提取 sn
                for key in ("sn", "sn1"):
                    if key in m.groupdict():
                        result["sn"] = m.group(key)
                        break
                else:
                    raise FolderParseError(folder_name)

                # 提取 id（可选）
                if "id" in m.groupdict() and m.group("id"):
                    result["id"] = m.group("id")

                # 提取 date / time（可选）
                if "date" in m.groupdict() and m.group("date"):
                    result["date"] = m.group("date")
                if "time" in m.groupdict() and m.group("time"):
                    result["time"] = m.group("time")

                # 如果没有 date/time 但有 rest，尝试从 rest 提取
                if "rest" in m.groupdict() and m.group("rest"):
                    rest = m.group("rest")
                    # 尝试提取 timestamp 模式: YYYYMMDD_HHMMSS
                    ts_match = re.search(r"(\d{8})_(\d{6})", rest)
                    if ts_match:
                        result.setdefault("date", ts_match.group(1))
                        result.setdefault("time", ts_match.group(2))

                return result
        return None

    # ---- CP 检查 ----

    def _find_sn_in_waterfall(self, sn):
        """在 waterfall 中查找 SN，返回记录或 None"""
        return self.waterfall.get(sn, None)

    def _find_sn_in_wfcheck(self, sn):
        """在 wfcheck 中查找 SN，返回状态列表或 None"""
        return self.wfcheck.get(sn, None)

    def get_next_incomplete_cp(self, sn):
        """
        检查 SN 的 CP 完成状态，返回第一个未完成的 CP 序号和名称。
        返回 (cp_index, cp_name) 或 None（全部完成）。
        """
        wf_record = self._find_sn_in_waterfall(sn)
        check_record = self._find_sn_in_wfcheck(sn)

        if not wf_record:
            raise SNNotFoundError(sn, "_waterfall.csv")
        if not check_record:
            raise SNNotFoundError(sn, "_wfcheck.csv")

        cps = wf_record["cps"]
        statuses = check_record

        # 确定实际有效的 CP 数量
        effective_count = len(cps)
        # 去除空名称
        while effective_count > 0 and not cps[effective_count - 1]:
            effective_count -= 1
        if effective_count == 0:
            raise InvalidAssetDataError("_waterfall.csv",
                                        f"SN [{sn}] 没有有效的 CP 数据")

        # 如果 CP 数量不一致，以较短的为准
        check_len = len(statuses)
        if check_len < effective_count:
            effective_count = check_len

        for i in range(effective_count):
            cp_status = statuses[i].upper()
            cp_name = cps[i]
            if cp_status == "N":
                return i, cp_name

        # 全部完成
        return None, None

    # ---- Fail 日志检测 ----

    def has_fail_logs(self, folder_path):
        """
        检查目标文件夹（递归）中是否有以 Fail 开头的 log 文件。
        """
        fail_re = re.compile(self.regexes.get("fail_prefix", "^Fail"),
                             re.IGNORECASE)
        for root, dirs, files in os.walk(folder_path):
            for fname in files:
                if fail_re.match(fname):
                    return True
        return False

    # ---- CP 状态写入 ----

    def _write_wfcheck(self):
        """将内存中的 self.wfcheck 写回 _wfcheck.csv。"""
        path = os.path.join(_ASSETS_DIR, "_wfcheck.csv")
        bak_path = path + ".bak"

        # 备份原文件
        if not os.path.exists(bak_path):
            try:
                shutil.copy2(path, bak_path)
                logger.debug("_wfcheck.csv 已备份至: %s", bak_path)
            except OSError as e:
                logger.error("_wfcheck.csv 备份失败: %s", e)

        # 按 in-memory dict 的插入顺序写回
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            header = ["Unit_No", "SN"] + [f"CP{i}" for i in range(8)]
            writer.writerow(header)
            for sn, statuses in self.wfcheck.items():
                unit_no = self.waterfall.get(sn, {}).get("unit_no", "")
                # 补齐至 8 个状态
                padded = list(statuses) + [""] * (8 - len(statuses))
                row = [unit_no, sn] + padded[:8]
                writer.writerow(row)

        logger.info("_wfcheck.csv 已更新 (%d 条记录)", len(self.wfcheck))

    def update_cp_status(self, sn, cp_index, dry_run=False):
        """
        将指定 SN 的 CP{cp_index} 状态从 N 标记为 Y。
        如果 dry_run=True，仅打印日志，不写回文件。
        """
        check_record = self._find_sn_in_wfcheck(sn)
        if not check_record:
            raise SNNotFoundError(sn, "_wfcheck.csv")

        if cp_index >= len(check_record):
            logger.warning("CP%d 超出范围 (SN: %s)", cp_index, sn)
            return

        # 标记为 Y
        old_status = check_record[cp_index]
        check_record[cp_index] = "Y"
        self.wfcheck[sn] = check_record

        if dry_run:
            logger.info("[DRY-RUN] 会将 SN [%s] 的 CP%d 状态从 %s 标记为 Y",
                        sn, cp_index, old_status)
        else:
            logger.info("SN [%s] CP%d 状态已标记为 Y (原: %s)",
                        sn, cp_index, old_status)

        # 仅非 dry-run 时写回文件
        if not dry_run:
            self._write_wfcheck()

    # ---- 标准名称生成 ----

    def build_standard_name(self, sn, unit_no, cp_index, cp_name, parsed_info,
                            has_fail):
        """
        按模式生成标准文件夹名。
        格式: #{id}_{checkpoint}_{sn}_{timestamp}
        或   #{id}_{checkpoint}_BFail_{sn}_{timestamp}
        """
        item_id = parsed_info.get("id", "")
        date_str = parsed_info.get("date", "")
        time_str = parsed_info.get("time", "")

        # 拼接 timestamp
        timestamp = f"{date_str}_{time_str}" if date_str and time_str else ""

        # 简化 checkpoint 名：只取第一个单词/关键部分
        # 这里使用完整名称，但替换空格为下划线
        cp_clean = cp_name.strip().replace(" ", "_")

        if has_fail:
            new_name = f"#{item_id}_{cp_clean}_BFail_{sn}_{timestamp}"
        else:
            new_name = f"#{item_id}_{cp_clean}_{sn}_{timestamp}"

        # 清理多余的下划线
        new_name = re.sub(r"_+", "_", new_name)
        # 去除首尾下划线
        new_name = new_name.strip("_")

        return new_name

    # ---- 重命名执行 ----

    def rename_folder(self, old_path, new_name, dry_run=False):
        """
        重命名文件夹。
        dry_run=True 时仅返回预期新路径，不执行。
        返回 (old_path, new_path, executed)
        """
        parent_dir = os.path.dirname(old_path)
        new_path = os.path.join(parent_dir, new_name)

        if os.path.exists(new_path) and old_path != new_path:
            logger.warning("目标路径已存在，跳过: %s", new_path)
            return old_path, new_path, False

        if dry_run:
            logger.info("[DRY-RUN] 重命名: %s -> %s",
                        os.path.basename(old_path), new_name)
            return old_path, new_path, False

        try:
            os.rename(old_path, new_path)
            logger.info("重命名成功: %s -> %s",
                        os.path.basename(old_path), new_name)
            return old_path, new_path, True
        except OSError as e:
            logger.error("重命名失败: %s -> %s, 错误: %s",
                         os.path.basename(old_path), new_name, e)
            return old_path, new_path, False

    # ---- 完整处理单个文件夹 ----

    def process_folder(self, folder_name, folder_path, dry_run=False):
        """
        处理单个目标文件夹：
        1. 解析文件夹名
        2. 查找 SN 在 waterfall/wfcheck
        3. 找到下一个未完成的 CP
        4. 检测 Fail 日志
        5. 生成标准名称
        6. 重命名（或 dry-run）
        返回处理结果 dict。
        """
        result = {
            "original_name": folder_name,
            "sn": None,
            "unit_no": None,
            "cp_index": None,
            "cp_name": None,
            "has_fail": False,
            "new_name": None,
            "success": False,
            "message": "",
        }

        # 1. 检查是否已经是 noorm 标准化格式
        noorm_info = self.check_already_noormed(folder_name)
        if noorm_info:
            result["sn"] = noorm_info["sn"]
            result["new_name"] = folder_name  # 自身就是标准名
            result["success"] = True
            result["message"] = f"该路径已完成 noorm，跳过: {folder_name}"
            logger.info(result["message"])
            return result

        # 2. 解析原始文件夹名
        parsed = self.parse_folder_name(folder_name)
        if not parsed:
            result["message"] = f"无法解析文件夹名: {folder_name}"
            logger.warning(result["message"])
            return result

        sn = parsed.get("sn", "")
        result["sn"] = sn

        # 3. 查找 waterfall
        wf_record = self._find_sn_in_waterfall(sn)
        if not wf_record:
            result["message"] = f"SN [{sn}] 在 waterfall 中未找到"
            logger.warning(result["message"])
            return result

        unit_no = wf_record["unit_no"]
        result["unit_no"] = unit_no

        # 4. 查找下一个未完成 CP
        try:
            cp_index, cp_name = self.get_next_incomplete_cp(sn)
        except AllCPCompletedError as e:
            result["message"] = str(e)
            logger.info(result["message"])
            return result

        if cp_index is None:
            result["message"] = (f"SN [{sn}] (Unit_No:{unit_no}) "
                                 f"的 testplan 已全部完成")
            logger.info(result["message"])
            return result

        result["cp_index"] = cp_index
        result["cp_name"] = cp_name

        # 5. 检测 Fail 日志
        has_fail = self.has_fail_logs(folder_path)
        result["has_fail"] = has_fail

        # 6. 生成标准名称
        new_name = self.build_standard_name(
            sn, unit_no, cp_index, cp_name, parsed, has_fail
        )
        result["new_name"] = new_name

        # 7. 重命名
        _, new_path, executed = self.rename_folder(
            folder_path, new_name, dry_run=dry_run
        )
        result["success"] = executed or dry_run
        result["new_path"] = new_path

        # 8. 更新 CP 状态（重命名成功后才会真正更新文件）
        #    在 dry-run 下仅打印日志
        if executed or dry_run:
            self.update_cp_status(sn, cp_index, dry_run=dry_run)

        if dry_run:
            result["message"] = f"[DRY-RUN] 准备重命名: {folder_name} -> {new_name}"
        else:
            if executed:
                result["message"] = f"已重命名: {folder_name} -> {new_name}"
            else:
                result["message"] = f"重命名跳过: {folder_name} (可能已存在)"

        return result

    # ---- 批量处理 ----

    def process_all(self, dry_run=False):
        """
        批量处理所有目标文件夹。
        返回处理结果列表。
        """
        results = []
        for folder_name, folder_path in self._iter_target_folders():
            logger.debug("处理文件夹: %s", folder_name)
            r = self.process_folder(folder_name, folder_path, dry_run=dry_run)
            results.append(r)
        return results