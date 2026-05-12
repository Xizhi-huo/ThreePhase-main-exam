from __future__ import annotations

from typing import Callable

from domain.enums import BreakerPosition
from domain.free_exam_state import FreeExamState


class FreeExamService:
    """Free-operation exam coordinator for the standalone exam build."""

    def __init__(
        self,
        *,
        sim_state,
        get_physics: Callable[[], object],
        get_state: Callable[[], FreeExamState],
        set_state: Callable[[FreeExamState], None],
        get_pending_accident_scene_id: Callable[[], str | None],
    ) -> None:
        self._sim_state = sim_state
        self._get_physics = get_physics
        self._get_state = get_state
        self._set_state = set_state
        self._get_pending_accident_scene_id = get_pending_accident_scene_id

    def create_free_exam_state(self) -> FreeExamState:
        return FreeExamState()

    def reset_free_exam(self) -> None:
        self._set_state(self.create_free_exam_state())

    def start_free_exam(self, scenario_id: str) -> None:
        state = self.create_free_exam_state()
        state.active = True
        state.hidden_scenario_id = scenario_id
        state.result = "running"
        self._set_state(state)

    def record_current_measurement(self) -> bool:
        state = self._get_state()
        if not state.active:
            return False
        physics = self._get_physics()
        record = {
            "no": state.next_record_no,
            "nodes": getattr(physics, "meter_nodes", None),
            "reading": getattr(physics, "meter_reading", "--"),
            "value": getattr(physics, "meter_voltage", None),
            "status": getattr(physics, "meter_status", "idle"),
        }
        state.measurement_records.append(record)
        state.next_record_no += 1
        return True

    def on_gen2_final_close_attempt(self) -> bool:
        state = self._get_state()
        if not state.active:
            return True
        if state.final_close_attempted:
            return False
        state.final_close_attempted = True
        state.final_close_wait_frames = 10
        state.result = "pending"
        state.fail_reason = ""
        return True

    def update_after_physics(self) -> None:
        state = self._get_state()
        if not state.active or not state.final_close_attempted:
            return
        if state.result in {"passed", "failed"}:
            return

        pending_accident = self._get_pending_accident_scene_id()
        if pending_accident:
            self._fail(f"Gen2 合闸触发事故场景 {pending_accident}")
            return

        sim = self._sim_state
        physics = self._get_physics()
        gen1_on_bus = (
            sim.gen1.breaker_position == BreakerPosition.WORKING
            and sim.gen1.breaker_closed
        )
        gen2_on_bus = (
            sim.gen2.breaker_position == BreakerPosition.WORKING
            and sim.gen2.breaker_closed
        )
        if (
            gen1_on_bus
            and gen2_on_bus
            and getattr(physics, "bus_live", False)
            and getattr(physics, "bus_source", None) == "both"
        ):
            state.result = "passed"
            state.fail_reason = ""
            return

        if state.final_close_wait_frames > 0:
            state.final_close_wait_frames -= 1
            return

        if not sim.gen2.breaker_closed:
            self._fail("Gen2 未能成功合闸并入母排")
        elif getattr(physics, "bus_source", None) != "both":
            self._fail("Gen2 合闸后未形成双机并母运行")
        else:
            self._fail("Gen2 最终并母状态未满足通过条件")

    def _fail(self, reason: str) -> None:
        state = self._get_state()
        state.result = "failed"
        state.fail_reason = reason