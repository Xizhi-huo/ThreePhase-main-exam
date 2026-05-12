# ========== 系统运行模式枚举 ==========
class SystemMode:
    ISOLATED_BUS = "隔离母排"


AVAILABLE_MODES = [SystemMode.ISOLATED_BUS]


# 断路器物理位置枚举
class BreakerPosition:
    DISCONNECTED = "脱开位置"    # 绝缘测试用
    TEST = "试验位置"            # 单机调试二次回路用
    WORKING = "工作位置"         # 并网用
