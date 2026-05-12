from __future__ import annotations


class FlowModeManager:
    """Exam-only flow policy.

    The standalone exam build is a free-operation console: no teaching hints,
    no step gates, no score sheet. The physical simulation still detects faults
    and blackbox repairs remain available, but the only pass/fail decision is
    made by the final Gen2 bus close result.
    """

    def __init__(self, test_flow_mode: str = "assessment"):
        self.test_flow_mode = "assessment"

    def is_teaching_mode(self) -> bool:
        return False

    def is_engineering_mode(self) -> bool:
        return False

    def is_assessment_mode(self) -> bool:
        return True

    def can_advance_with_fault(self) -> bool:
        return True

    def should_show_fault_detected_banner(self) -> bool:
        return False

    def should_show_diagnostic_hints(self) -> bool:
        return False

    def should_block_step5_until_blackbox_fixed(self) -> bool:
        return False

    def should_hold_at_step4_when_wiring_fault_unrepaired(self) -> bool:
        return False

    def should_show_blackbox_required_dialog_before_step5(self) -> bool:
        return False

    def can_inspect_blackbox(self) -> bool:
        return True

    def can_repair_in_blackbox(self) -> bool:
        return True

    def should_auto_clear_fault_only_when_all_blackboxes_normal(self) -> bool:
        return True

    def allow_admin_shortcuts(self) -> bool:
        return False

    def can_use_pt_exam_quick_record(self) -> bool:
        return False

    def should_record_assessment_metrics(self) -> bool:
        return False

    def should_auto_score_assessment(self) -> bool:
        return False

    def assessment_ends_after_step4_closed_loop(self) -> bool:
        return False
