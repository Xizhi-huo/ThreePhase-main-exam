from __future__ import annotations

import os
import random
import sys
import time
import traceback
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5 import QtCore, QtWidgets

from domain.constants import DEFAULT_PT_RATIO_ROWS, GRID_AMP
from domain.fault_scenarios import SCENARIOS
from domain.free_exam_state import FreeExamState
from domain.models import GeneratorState, SimulationState
from domain.phase_order_state import PhaseOrderState
from services.blackbox_repair_handler import BlackboxRepairHandler
from services.fault_manager import FaultManager
from services.flow_mode_manager import FlowModeManager
from services.free_exam_service import FreeExamService
from services.hardware_actions import HardwareActions
from services.phase_order_resolver import PhaseOrderResolver
from services.physics_engine import PhysicsEngine
from ui.main_window import PowerSyncUI


@dataclass
class _LoopState:
    completed: bool = True
    records: dict = field(default_factory=dict)


@dataclass
class _StepState:
    started: bool = False
    completed: bool = True
    records: dict = field(default_factory=dict)
    feedback: str = ""
    feedback_color: str = "#444444"
    result: object = None


@dataclass
class _SyncState:
    started: bool = False
    completed: bool = False
    round1_done: bool = False
    round2_done: bool = False


class _NullSyncService:
    def is_sync_test_complete(self) -> bool:
        return False

    def is_gen_synced(self, gen_a, gen_b) -> bool:
        return False


class PowerSyncController:
    _TICK_FAILURE_THRESHOLD = 5

    def __init__(self):
        self.sim_state = SimulationState(
            gen1=GeneratorState(
                freq=round(random.uniform(48.0, 52.0), 1),
                amp=round(random.uniform(9500.0, 11500.0), 1),
                phase_deg=round(random.uniform(-180.0, 180.0), 1),
            ),
            gen2=GeneratorState(
                freq=round(random.uniform(48.0, 52.0), 1),
                amp=round(random.uniform(9500.0, 11500.0), 1),
                phase_deg=round(random.uniform(-180.0, 180.0), 1),
            ),
        )
        self.phase_order_state = PhaseOrderState.default()
        self.flow_mgr = FlowModeManager()
        self.test_flow_mode = "assessment"
        self.free_exam_state = FreeExamState()
        self.exam_events: list[dict] = []

        self.loop_test_state = _LoopState()
        self.pt_voltage_check_state = _StepState()
        self.pt_phase_check_state = _StepState()
        self.pt_exam_states = {1: _StepState(), 2: _StepState()}
        self.sync_test_state = _SyncState()
        self.sync_svc = _NullSyncService()

        self._pending_accident_scene_id = None
        self._pending_ui_tab_index = None
        self._pending_pt_ratio_row_updates = {}
        self._last_fault_detected = False
        self._consecutive_tick_failures = 0
        self._tick_error_notified = False
        self._last_tick_perf = time.perf_counter()

        self.blackbox_handler = BlackboxRepairHandler(
            sim_state=self.sim_state,
            flow_mgr=self.flow_mgr,
            get_fault_mgr=lambda: self.fault_mgr,
            append_assessment_event=self.append_assessment_event,
            get_pt_phase_orders=lambda: self.pt_phase_orders,
            get_g1_blackbox_order=lambda: self.g1_blackbox_order,
            set_g1_blackbox_order=lambda value: setattr(self, "g1_blackbox_order", value),
            get_g2_blackbox_order=lambda: self.g2_blackbox_order,
            set_g2_blackbox_order=lambda value: setattr(self, "g2_blackbox_order", value),
            get_pt1_pri_blackbox_order=lambda: self.pt1_pri_blackbox_order,
            set_pt1_pri_blackbox_order=lambda value: setattr(self, "pt1_pri_blackbox_order", value),
            get_pt1_sec_blackbox_order=lambda: self.pt1_sec_blackbox_order,
            set_pt1_sec_blackbox_order=lambda value: setattr(self, "pt1_sec_blackbox_order", value),
            apply_g2_blackbox_to_pt3=self.phase_order_state.apply_g2_blackbox_to_pt3,
            apply_pt1_blackbox_to_pt_phases=self.phase_order_state.apply_pt1_blackbox_to_pt_phases,
        )
        self.fault_mgr = FaultManager(
            sim_state=self.sim_state,
            blackbox_handler=self.blackbox_handler,
            append_assessment_event=self.append_assessment_event,
            request_pt_ratio_row_update=self.request_pt_ratio_row_update,
            set_last_fault_detected=lambda value: setattr(self, "_last_fault_detected", value),
            get_pt_phase_orders=lambda: self.pt_phase_orders,
            get_g1_blackbox_order=lambda: self.g1_blackbox_order,
            set_g1_blackbox_order=lambda value: setattr(self, "g1_blackbox_order", value),
            get_g2_blackbox_order=lambda: self.g2_blackbox_order,
            set_g2_blackbox_order=lambda value: setattr(self, "g2_blackbox_order", value),
            get_pt1_pri_blackbox_order=lambda: self.pt1_pri_blackbox_order,
            set_pt1_pri_blackbox_order=lambda value: setattr(self, "pt1_pri_blackbox_order", value),
            get_pt1_sec_blackbox_order=lambda: self.pt1_sec_blackbox_order,
            set_pt1_sec_blackbox_order=lambda value: setattr(self, "pt1_sec_blackbox_order", value),
        )
        self.phase_resolver = PhaseOrderResolver(
            sim_state=self.sim_state,
            get_pt_phase_orders=lambda: self.pt_phase_orders,
            get_g2_blackbox_order=lambda: self.g2_blackbox_order,
        )
        self.free_exam_svc = FreeExamService(
            sim_state=self.sim_state,
            get_physics=lambda: self.physics,
            get_state=lambda: self.free_exam_state,
            set_state=lambda state: setattr(self, "free_exam_state", state),
            get_pending_accident_scene_id=lambda: self._pending_accident_scene_id,
            get_phase_sequence_measurement=self.get_phase_sequence_measurement,
        )
        self.physics = PhysicsEngine(
            sim_state=self.sim_state,
            flow_mgr=self.flow_mgr,
            phase_resolver=self.phase_resolver,
            sync_svc=self.sync_svc,
            get_pt_phase_orders=lambda: self.pt_phase_orders,
            get_loop_test_state=lambda: self.loop_test_state,
            get_pt_voltage_check_state=lambda: self.pt_voltage_check_state,
            is_sync_test_active=lambda: False,
            mark_fault_detected=self.mark_fault_detected,
            queue_accident_dialog=self.queue_accident_dialog,
        )
        self.hw = HardwareActions(
            sim_state=self.sim_state,
            show_warning=lambda title, message: self.ui.show_warning(title, message),
            is_free_exam_active=self.is_free_exam_active,
            on_free_exam_final_close_attempt=self.free_exam_svc.on_gen2_final_close_attempt,
        )

        self.ui = PowerSyncUI(self)
        self._timer = QtCore.QTimer()
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    @property
    def pt_phase_orders(self):
        return self.phase_order_state.pt_phase_orders

    @property
    def g1_blackbox_order(self):
        return self.phase_order_state.g1_blackbox_order

    @g1_blackbox_order.setter
    def g1_blackbox_order(self, value):
        self.phase_order_state.g1_blackbox_order[:] = list(value)

    @property
    def g2_blackbox_order(self):
        return self.phase_order_state.g2_blackbox_order

    @g2_blackbox_order.setter
    def g2_blackbox_order(self, value):
        self.phase_order_state.g2_blackbox_order[:] = list(value)

    @property
    def pt1_pri_blackbox_order(self):
        return self.phase_order_state.pt1_pri_blackbox_order

    @pt1_pri_blackbox_order.setter
    def pt1_pri_blackbox_order(self, value):
        self.phase_order_state.pt1_pri_blackbox_order[:] = list(value)

    @property
    def pt1_sec_blackbox_order(self):
        return self.phase_order_state.pt1_sec_blackbox_order

    @pt1_sec_blackbox_order.setter
    def pt1_sec_blackbox_order(self, value):
        self.phase_order_state.pt1_sec_blackbox_order[:] = list(value)

    def is_assessment_mode(self) -> bool:
        return True

    def is_free_exam_active(self) -> bool:
        return bool(self.free_exam_state.active)

    def can_inspect_blackbox(self) -> bool:
        return self.flow_mgr.can_inspect_blackbox()

    def can_repair_in_blackbox(self) -> bool:
        return self.flow_mgr.can_repair_in_blackbox()

    def is_loop_test_complete(self) -> bool:
        return True

    def is_sync_test_active(self) -> bool:
        return False

    def get_pt_phase_sequence(self, pt_name: str):
        return self.phase_resolver.get_pt_phase_sequence(pt_name)

    def get_phase_sequence_measurement(self):
        if not hasattr(self, "ui"):
            return None

        circuit_tab = getattr(self.ui, "_circuit_tab", None)
        phase_meter = getattr(self.ui, "phase_seq_meter", None)
        if circuit_tab is None or phase_meter is None:
            return None

        raw_status = circuit_tab.get_phase_wiring_status()
        status = getattr(raw_status, "value", str(raw_status))
        if status == "idle":
            return None

        pt_name = circuit_tab.get_phase_wiring_active_pt()
        phase_session = getattr(circuit_tab, "_phase_wiring", None)
        wired = set(getattr(phase_session, "wired", set()))
        nodes = tuple(f"{pt_name}_{phase}" for phase in ("A", "B", "C")) if pt_name else None

        if status != "ready":
            target = pt_name or "未选择 PT"
            return {
                "kind": "phase_sequence",
                "pt_name": pt_name,
                "nodes": nodes,
                "reading": f"{target} 相序仪接线未完成：已接 {len(wired)}/3",
                "value": None,
                "status": "waiting",
                "phase_sequence": "unknown",
            }

        sequence = phase_meter.current_sequence()
        label = self._phase_sequence_label(sequence)
        if sequence == "unknown":
            reading = f"{pt_name} 相序仪未得到有效结果"
            record_status = "waiting"
        else:
            reading = f"{pt_name} 相序：{sequence}（{label}）"
            record_status = "ok" if label == "正序" else "warning" if label == "不平衡/故障" else "danger"

        return {
            "kind": "phase_sequence",
            "pt_name": pt_name,
            "nodes": nodes,
            "reading": reading,
            "value": sequence,
            "status": record_status,
            "phase_sequence": sequence,
        }

    @staticmethod
    def _phase_sequence_label(sequence: str) -> str:
        if sequence in {"ABC", "BCA", "CAB"}:
            return "正序"
        if sequence == "FAULT":
            return "不平衡/故障"
        if sequence == "unknown":
            return "未知"
        return "反序"

    def get_generator_state(self, gen_id: int):
        return self.sim_state.gen1 if gen_id == 1 else self.sim_state.gen2

    def start_random_free_exam(self) -> str:
        fault_ids = [scene_id for scene_id in SCENARIOS if scene_id]
        scenario_id = random.choice(fault_ids)
        self.reset_for_scenario(scenario_id)
        self._pending_accident_scene_id = None
        self.exam_events.clear()
        self.free_exam_svc.start_free_exam(scenario_id)
        return scenario_id

    def reset_free_exam(self) -> None:
        self._pending_accident_scene_id = None
        self.exam_events.clear()
        self.reset_for_scenario("")
        self.free_exam_svc.reset_free_exam()

    def record_free_exam_measurement(self) -> bool:
        return self.free_exam_svc.record_current_measurement()

    def get_blackbox_runtime_state(self, target: str):
        return self.blackbox_handler.get_blackbox_runtime_state(target)

    def apply_blackbox_repair_attempt(self, *args, **kwargs):
        return self.blackbox_handler.apply_blackbox_repair_attempt(*args, **kwargs)

    def toggle_engine(self, gen_id: int) -> None:
        self.hw.toggle_engine(gen_id)

    def toggle_breaker(self, gen_id: int) -> None:
        self.hw.toggle_breaker(gen_id)

    def change_breaker_position(self, gen_id: int, position: str) -> bool:
        return self.hw.change_breaker_position(gen_id, position)

    def toggle_pause(self) -> None:
        self.sim_state.paused = not self.sim_state.paused
        self.ui.pause_btn.setText("恢复物理时空" if self.sim_state.paused else "暂停整个物理空间")
        self.ui._apply_button_tone(
            self.ui.pause_btn,
            "success" if self.sim_state.paused else "warning",
            hero=True,
        )

    def request_ui_tab(self, tab_index: int) -> None:
        self._pending_ui_tab_index = tab_index

    def consume_requested_ui_tab(self):
        tab_index = self._pending_ui_tab_index
        self._pending_ui_tab_index = None
        return tab_index

    def request_pt_ratio_row_update(self, ratio_attr: str, pri_value: int, sec_value: int) -> None:
        self._pending_pt_ratio_row_updates[ratio_attr] = (pri_value, sec_value)

    def consume_requested_pt_ratio_row_updates(self):
        updates = dict(self._pending_pt_ratio_row_updates)
        self._pending_pt_ratio_row_updates.clear()
        return updates

    def append_assessment_event(self, event_type, **kwargs) -> None:
        self.exam_events.append({"type": event_type, **kwargs})

    def mark_fault_detected(self, **payload) -> bool:
        fc = self.sim_state.fault_config
        if fc.active and not fc.repaired:
            fc.detected = True
            self._last_fault_detected = True
            self.exam_events.append({"type": "fault_detected", **payload})
        return True

    def reset_pt_ratios_to_defaults(self) -> None:
        for ratio_attr, (pri_value, sec_value) in DEFAULT_PT_RATIO_ROWS.items():
            setattr(self.sim_state, ratio_attr, pri_value / sec_value)
            self.request_pt_ratio_row_update(ratio_attr, pri_value, sec_value)

    def reset_blackbox_orders(self) -> None:
        self.phase_order_state.reset_blackbox_orders()

    def rebuild_circuit_view(self) -> None:
        self.ui.rebuild_circuit_diagram()

    def inject_fault(self, scenario_id: str) -> None:
        self.fault_mgr.inject_fault(scenario_id)

    def repair_fault(self, step: int = 0, source: str = "repair_fault") -> None:
        self.fault_mgr.repair_fault(step=step, source=source)

    def reset_for_scenario(self, scenario_id: str) -> None:
        sim = self.sim_state
        for gen in (sim.gen1, sim.gen2):
            gen.running = False
            gen.breaker_closed = False
            gen.cmd_close = False
            gen.actual_amp = 0.0
        sim.auto_sync_active = False
        sim.sync_target = None
        sim.probe1_node = None
        sim.probe2_node = None
        sim.loop_test_mode = False
        sim.fault_reverse_bc = False

        self.loop_test_state = _LoopState()
        self.pt_voltage_check_state = _StepState()
        self.pt_phase_check_state = _StepState()
        self.pt_exam_states = {1: _StepState(), 2: _StepState()}
        self.sync_test_state = _SyncState()

        self.phase_order_state.reset_pt_phase_orders()
        self.phase_order_state.reset_blackbox_orders()
        self.reset_pt_ratios_to_defaults()
        self.inject_fault(scenario_id)
        self._last_fault_detected = False

        if hasattr(self, "physics"):
            self.physics.reset_wave_history()
            self.physics.bus_reference_gen = None
        if hasattr(self, "ui"):
            try:
                self.rebuild_circuit_view()
            except Exception:
                traceback.print_exc()

    def queue_accident_dialog(self, scene_id: str) -> None:
        if self._pending_accident_scene_id is None:
            self._pending_accident_scene_id = scene_id

    def _consume_pending_accident_dialog(self) -> None:
        self._pending_accident_scene_id = None

    def _handle_tick_failure(self, stage: str) -> None:
        self._consecutive_tick_failures += 1
        traceback.print_exc()
        if self._consecutive_tick_failures == 3 and not self._tick_error_notified:
            self.ui.statusBar().showMessage(
                f"物理帧更新连续失败 {self._consecutive_tick_failures} 次（阶段: {stage}），请检查控制台错误日志。"
            )
            self._tick_error_notified = True
        if self._consecutive_tick_failures >= self._TICK_FAILURE_THRESHOLD and self._timer.isActive():
            self._timer.stop()
            self.ui.statusBar().showMessage(
                f"物理引擎已熔断停止（阶段: {stage}，连续失败 {self._consecutive_tick_failures} 次）。"
            )

    def _clear_tick_failure_state(self) -> None:
        if self._consecutive_tick_failures > 0:
            self.ui.statusBar().clearMessage()
        self._consecutive_tick_failures = 0
        self._tick_error_notified = False

    def _tick(self) -> None:
        now_perf = time.perf_counter()
        frame_dt = max(0.0, now_perf - self._last_tick_perf)
        self._last_tick_perf = now_perf
        try:
            self.physics.frame_dt = frame_dt
            self.physics.update_physics()
            self.free_exam_svc.update_after_physics()
            rs = self.physics.build_render_state()
        except Exception:
            self._handle_tick_failure("physics")
            return

        try:
            self.ui.render_visuals(rs)
            self._consume_pending_accident_dialog()
            self._clear_tick_failure_state()
        except Exception:
            self._handle_tick_failure("render")


if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")

    ctrl = PowerSyncController()
    ctrl.ui.showMaximized()

    sys.exit(app.exec_())
