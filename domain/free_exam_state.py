from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class FreeExamState:
    active: bool = False
    hidden_scenario_id: str = ""
    final_close_attempted: bool = False
    final_close_wait_frames: int = 0
    sustained_pass_frames: int = 0
    result: str = "idle"  # idle | running | pending | passed | failed
    fail_reason: str = ""
    measurement_records: List[Dict[str, Any]] = field(default_factory=list)
    next_record_no: int = 1

    def reset(self) -> None:
        self.active = False
        self.hidden_scenario_id = ""
        self.final_close_attempted = False
        self.final_close_wait_frames = 0
        self.sustained_pass_frames = 0
        self.result = "idle"
        self.fail_reason = ""
        self.measurement_records.clear()
        self.next_record_no = 1
