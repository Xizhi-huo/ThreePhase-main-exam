from __future__ import annotations


class FlowModeManager:
    """Exam-only flow policy.

    自由考核台只保留 4 个被实际消费的策略开关：
    黑盒检查、黑盒修复、诊断提示、修复全部完成后才清故障。
    """

    def can_inspect_blackbox(self) -> bool:
        return True

    def can_repair_in_blackbox(self) -> bool:
        return True

    def should_show_diagnostic_hints(self) -> bool:
        return False

    def should_auto_clear_fault_only_when_all_blackboxes_normal(self) -> bool:
        return True
