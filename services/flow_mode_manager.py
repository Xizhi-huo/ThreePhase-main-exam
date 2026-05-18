from __future__ import annotations


class FlowModeManager:
    """Exam-only flow policy.

    自由考核台保留黑盒检查、黑盒修复和修复后故障清除策略。
    """

    def can_inspect_blackbox(self) -> bool:
        return True

    def can_repair_in_blackbox(self) -> bool:
        return True

    def should_auto_clear_fault_only_when_all_blackboxes_normal(self) -> bool:
        return True
