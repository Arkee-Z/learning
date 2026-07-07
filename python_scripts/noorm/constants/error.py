"""
noorm 自定义异常模块
"""


class NoormError(Exception):
    """noorm 基类异常"""
    pass


class SNNotFoundError(NoormError):
    """在 _waterfall 或 _wfcheck 中未找到 SN"""
    def __init__(self, sn, source):
        self.sn = sn
        self.source = source
        super().__init__(f"SN [{sn}] 在 {source} 中未找到")


class AllCPCompletedError(NoormError):
    """所有 checkpoint 均已完成的提示"""
    def __init__(self, sn, unit_no):
        self.sn = sn
        self.unit_no = unit_no
        super().__init__(f"SN [{sn}] (Unit_No:{unit_no}) 的 testplan 已全部完成")


class FolderParseError(NoormError):
    """文件夹名解析失败"""
    def __init__(self, folder_name):
        self.folder_name = folder_name
        super().__init__(f"无法解析文件夹名: {folder_name}")


class HealthCheckCSVNotFoundError(NoormError):
    """未找到 FATP-HealthCheck CSV 文件"""
    def __init__(self, root_path):
        self.root_path = root_path
        super().__init__(f"在路径中未找到 FATP-HealthCheck 类型的 CSV 文件: {root_path}")


class InvalidAssetDataError(NoormError):
    """资源文件数据异常"""
    def __init__(self, asset_name, detail=""):
        self.asset_name = asset_name
        super().__init__(f"资源文件 {asset_name} 数据异常: {detail}")