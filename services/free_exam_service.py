from __future__ import annotations

import time
from typing import Callable, Mapping

from domain.enums import BreakerPosition
from domain.free_exam_state import FreeExamState


class FreeExamService:
    """Free-operation exam coordinator for the standalone exam build."""

    def __init__(
        self,
        *,
        sim_state,
        physics,
        get_state: Callable[[], FreeExamState],
        set_state: Callable[[FreeExamState], None],
        get_pending_accident_scene_id: Callable[[], str | None],
        get_phase_sequence_measurement: Callable[[], Mapping[str, object] | None] | None = None,
    ) -> None:
        self._sim_state = sim_state
        self._physics = physics
        self._get_state = get_state
        self._set_state = set_state
        self._get_pending_accident_scene_id = get_pending_accident_scene_id
        self._get_phase_sequence_measurement = get_phase_sequence_measurement
        self._last_record_perf: float | None = None

    def create_free_exam_state(self) -> FreeExamState:
        return FreeExamState()

    def reset_free_exam(self) -> None:
        self._set_state(self.create_free_exam_state())
        self._last_record_perf = None

    def start_free_exam(self, scenario_id: str) -> None:
        state = self.create_free_exam_state()
        state.active = True
        state.hidden_scenario_id = scenario_id
        state.result = "running"
        self._set_state(state)
        self._last_record_perf = None

    def record_current_measurement(self) -> bool:
        state = self._get_state()
        if not state.active:
            return False
        now = time.perf_counter()
        if self._last_record_perf is not None and (now - self._last_record_perf) < 0.4:
            return False
        phase_record = None
        if self._get_phase_sequence_measurement is not None:
            phase_record = self._get_phase_sequence_measurement()

        if phase_record is not None:
            record = {"no": state.next_record_no, **phase_record}
        else:
            record = {
                "no": state.next_record_no,
                "kind": "multimeter",
                "nodes": self._current_multimeter_nodes(),
                "reading": getattr(self._physics, "meter_reading", "--"),
                "value": getattr(self._physics, "meter_voltage", None),
                "status": getattr(self._physics, "meter_status", "idle"),
            }
        state.measurement_records.append(record)
        state.next_record_no += 1
        self._last_record_perf = now
        return True

    def _current_multimeter_nodes(self):
        nodes = getattr(self._physics, "meter_nodes", None)
        if nodes:
            return nodes
        probe1 = getattr(self._sim_state, "probe1_node", None)
        probe2 = getattr(self._sim_state, "probe2_node", None)
        if probe1 and probe2:
            return (probe1, probe2)
        return nodes

    def on_gen2_final_close_attempt(self) -> bool:
        state = self._get_state()
        if not state.active:
            return True
        if state.final_close_attempted:
            return False
        state.final_close_attempted = True
        state.final_close_wait_frames = 30
        state.sustained_pass_frames = 0
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
            self._fail("未通过：考核条件未满足")
            return

        sim = self._sim_state
        fc = sim.fault_config
        if fc.active and fc.scenario_id and not fc.repaired and state.final_close_attempted:
            self._fail("未通过：考核条件未满足")
            return

        gen1_on_bus = (
            sim.gen1.breaker_position == BreakerPosition.WORKING
            and sim.gen1.breaker_closed
        )
        gen2_on_bus = (
            sim.gen2.breaker_position == BreakerPosition.WORKING
            and sim.gen2.breaker_closed
        )
        pass_condition = (
            gen1_on_bus
            and gen2_on_bus
            and getattr(self._physics, "bus_live", False)
            and getattr(self._physics, "bus_source", None) == "both"
        )

        if pass_condition:
            state.sustained_pass_frames += 1
            if state.sustained_pass_frames >= 5:
                state.result = "passed"
                state.fail_reason = ""
                return
        else:
            state.sustained_pass_frames = 0

        if state.final_close_wait_frames > 0:
            state.final_close_wait_frames -= 1
            return

        if not sim.gen2.breaker_closed:
            self._fail("Gen2 未能成功合闸并入母排")
        elif getattr(self._physics, "bus_source", None) != "both":
            self._fail("Gen2 合闸后未形成双机并母运行")
        else:
            self._fail("Gen2 最终并母状态未满足通过条件")

    def register_safety_accident(self, reason: str) -> bool:
        state = self._get_state()
        if not state.active or state.result in {"passed", "failed"}:
            return False
        state.final_close_attempted = True
        state.final_close_wait_frames = 0
        state.sustained_pass_frames = 0
        self._fail(reason)
        return True

    def _fail(self, reason: str) -> None:
        state = self._get_state()
        state.result = "failed"
        state.fail_reason = reason
