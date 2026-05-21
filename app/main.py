from __future__ import annotations

import hashlib
import os
import random
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5 import QtCore, QtWidgets

from domain.constants import DEFAULT_PT_RATIO_ROWS, GRID_AMP
from domain.enums import BreakerPosition
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


PRIMARY_CONTACT_ACCIDENTS = (
    (
        "万用表绝缘击穿",
        "普通表笔接触带电一次侧，高压击穿表笔绝缘并损坏仪表。",
        "小伙汁，万用表替你扛了一下，但现场它不一定扛得住。",
        "一次侧-1.png",
    ),
    (
        "弧光闪络",
        "一次侧高压点发生弧光闪络，柜内保护动作，操作中止。",
        "小伙汁，这一下在屏幕里只是弹窗，现场就是弧光和冲击波了。",
        "一次侧-2.png",
    ),
    (
        "相间短路",
        "表笔跨越高压相间距离，引发相间短路和开关柜跳闸。",
        "小伙汁，三相不是这么“握手”的，现场这一碰可能直接炸柜。",
        "一次侧-3.png",
    ),
    (
        "对地放电",
        "高压侧经表笔形成对地放电路径，接地保护动作。",
        "小伙汁，电流已经给自己找路了，现场你可能也在路上。",
        "一次侧-4.png",
    ),
    (
        "表笔熔毁",
        "测试线绝缘和金属端部过热熔毁，仪表端口损坏。",
        "小伙汁，表笔先融了算你运气好，现场下一步可能就轮到人了。",
        "一次侧-5.png",
    ),
    (
        "人身触电风险",
        "带电一次侧接触形成严重人身触电风险，安全闭锁动作。",
        "小伙汁，在这里我能救你一命，现场就没这么好运了。",
        "一次侧-6.png",
    ),
)


class PowerSyncController:
    _TICK_FAILURE_THRESHOLD = 5

    def __init__(self):
        # 初始化按依赖层级排列；仅保留两处必要延迟绑定：
        # blackbox_handler ↔ fault_mgr 存在真实循环，hardware_actions 需要晚建的 ui。
        # 其他服务尽量直接引用，避免构造期回调顺序耦合。
        # 独立考核版按依赖层级组装状态与服务。
        # Layer 0：纯状态对象（无依赖）
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
        self.free_exam_state = FreeExamState()

        # Layer 0：UI 通信中转标志
        self._pending_accident_scene_id = None
        self._pending_ui_tab_index = None
        self._pending_pt_ratio_row_updates = {}
        self._last_fault_detected = False
        self._consecutive_tick_failures = 0
        self._tick_error_notified = False
        self._last_tick_perf = time.perf_counter()

        # Layer 1：仅依赖 sim_state / phase_order_state 的服务
        self.phase_resolver = PhaseOrderResolver(
            sim_state=self.sim_state,
            get_pt_phase_orders=lambda: self.pt_phase_orders,
            get_g1_blackbox_order=lambda: self.g1_blackbox_order,
            get_g2_blackbox_order=lambda: self.g2_blackbox_order,
        )

        # Layer 2：blackbox_handler ↔ fault_mgr 真循环依赖
        self.blackbox_handler = BlackboxRepairHandler(
            sim_state=self.sim_state,
            flow_mgr=self.flow_mgr,
            get_fault_mgr=lambda: self.fault_mgr,  # 延迟绑定：fault_mgr 在下一层才存在
            get_pt_phase_orders=lambda: self.pt_phase_orders,
            get_g1_blackbox_order=lambda: self.g1_blackbox_order,
            set_g1_blackbox_order=lambda value: setattr(self, "g1_blackbox_order", value),
            get_g2_blackbox_order=lambda: self.g2_blackbox_order,
            set_g2_blackbox_order=lambda value: setattr(self, "g2_blackbox_order", value),
            get_pt1_pri_blackbox_order=lambda: self.pt1_pri_blackbox_order,
            set_pt1_pri_blackbox_order=lambda value: setattr(self, "pt1_pri_blackbox_order", value),
            get_pt1_sec_blackbox_order=lambda: self.pt1_sec_blackbox_order,
            set_pt1_sec_blackbox_order=lambda value: setattr(self, "pt1_sec_blackbox_order", value),
            get_pt2_sec_blackbox_order=lambda: self.pt2_sec_blackbox_order,
            set_pt2_sec_blackbox_order=lambda value: setattr(self, "pt2_sec_blackbox_order", value),
            apply_g2_blackbox_to_pt3=self.phase_order_state.apply_g2_blackbox_to_pt3,
            apply_pt1_blackbox_to_pt_phases=self.phase_order_state.apply_pt1_blackbox_to_pt_phases,
            apply_pt2_blackbox_to_pt2=self.phase_order_state.apply_pt2_blackbox_to_pt2,
        )
        self.fault_mgr = FaultManager(
            sim_state=self.sim_state,
            blackbox_handler=self.blackbox_handler,
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
            get_pt2_sec_blackbox_order=lambda: self.pt2_sec_blackbox_order,
            set_pt2_sec_blackbox_order=lambda value: setattr(self, "pt2_sec_blackbox_order", value),
        )

        # Layer 3：物理引擎（依赖 phase_resolver、回调）
        self.physics = PhysicsEngine(
            sim_state=self.sim_state,
            flow_mgr=self.flow_mgr,
            phase_resolver=self.phase_resolver,
            get_pt_phase_orders=lambda: self.pt_phase_orders,
            mark_fault_detected=self.mark_fault_detected,
            queue_accident_dialog=self.queue_accident_dialog,
        )

        # Layer 4：依赖 physics 的考核服务
        self.free_exam_svc = FreeExamService(
            sim_state=self.sim_state,
            physics=self.physics,
            get_state=lambda: self.free_exam_state,
            set_state=lambda state: setattr(self, "free_exam_state", state),
            get_pending_accident_scene_id=lambda: self._pending_accident_scene_id,
            get_phase_sequence_measurement=self.get_phase_sequence_measurement,
        )

        # Layer 5：硬件操作（ui 在最后构造，警告出口保留延迟绑定）
        self.hw = HardwareActions(
            sim_state=self.sim_state,
            show_warning=lambda title, message: self.ui.show_warning(title, message),  # 延迟绑定：ui 在最后构造
            is_free_exam_active=self.is_free_exam_active,
            on_free_exam_final_close_attempt=self.free_exam_svc.on_gen2_final_close_attempt,
        )

        # Layer 6：UI（消费上面所有服务）
        self.ui = PowerSyncUI(self)

        # Layer 7：物理时钟
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

    @property
    def pt2_sec_blackbox_order(self):
        return self.phase_order_state.pt2_sec_blackbox_order

    @pt2_sec_blackbox_order.setter
    def pt2_sec_blackbox_order(self, value):
        self.phase_order_state.pt2_sec_blackbox_order[:] = list(value)

    def is_free_exam_active(self) -> bool:
        return bool(self.free_exam_state.active)

    def can_inspect_blackbox(self) -> bool:
        return self.flow_mgr.can_inspect_blackbox()

    def can_repair_in_blackbox(self) -> bool:
        return self.flow_mgr.can_repair_in_blackbox()

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
        if sequence in {"unknown", "FAULT"}:
            reading = f"{pt_name} 相序：----"
            record_status = "waiting"
            recorded_sequence = "unknown"
        else:
            label = self._phase_sequence_label(sequence)
            reading = f"{pt_name} 相序：{sequence}（{label}）"
            record_status = "ok"
            recorded_sequence = sequence

        return {
            "kind": "phase_sequence",
            "pt_name": pt_name,
            "nodes": nodes,
            "reading": reading,
            "value": recorded_sequence,
            "status": record_status,
            "phase_sequence": recorded_sequence,
        }

    @staticmethod
    def _phase_sequence_label(sequence: str) -> str:
        if sequence in {"ABC", "BCA", "CAB"}:
            return "正序"
        if sequence in {"FAULT", "unknown"}:
            return "----"
        return "反序"

    def get_generator_state(self, gen_id: int):
        return self.sim_state.gen1 if gen_id == 1 else self.sim_state.gen2

    def start_random_free_exam(self) -> str:
        fault_ids = [scene_id for scene_id in SCENARIOS if scene_id]
        scenario_id = random.choice(fault_ids)
        self.reset_for_scenario(scenario_id)
        self._pending_accident_scene_id = None
        self.free_exam_svc.start_free_exam(scenario_id)
        return scenario_id

    def reset_free_exam(self) -> None:
        self._pending_accident_scene_id = None
        self.reset_for_scenario("")
        self.free_exam_svc.reset_free_exam()

    def record_free_exam_measurement(self) -> bool:
        return self.free_exam_svc.record_current_measurement()

    def record_free_exam_measurement_reject_reason(self) -> str:
        return self.free_exam_svc.last_record_reject_reason()

    def handle_primary_line_contact(self, gen_id: int) -> str | None:
        if gen_id == 1:
            gen = self.sim_state.gen1
        elif gen_id == 2:
            gen = self.sim_state.gen2
        else:
            return None
        if not gen.running:
            return None

        title, consequence, caption, image = random.choice(PRIMARY_CONTACT_ACCIDENTS)
        message = (
            f"风险：{title}\n\n后果：{consequence}\n\n{caption}"
            f"\n\n本次考核终止。\n\n[image:{image}]"
        )
        if not self.free_exam_svc.register_safety_accident(message):
            return None

        self.sim_state.probe1_node = None
        self.sim_state.probe2_node = None
        return message

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
        self.ui.pause_btn.setText("恢复波形动画时间" if self.sim_state.paused else "暂停波形动画时间")
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

    def update_pt_ratio(self, ratio_attr: str, primary_value: int, secondary_value: int) -> bool:
        if ratio_attr not in DEFAULT_PT_RATIO_ROWS or secondary_value <= 0:
            return False
        ratio = float(primary_value) / float(secondary_value)
        setattr(self.sim_state, ratio_attr, ratio)
        self.fault_mgr.maybe_repair_pt_ratio_fault(
            ratio_attr,
            ratio,
            step=0,
            source="free_exam_pt_ratio_panel",
        )
        return True

    def mark_fault_detected(self, **payload) -> bool:
        fc = self.sim_state.fault_config
        if fc.active and not fc.repaired:
            fc.detected = True
            self._last_fault_detected = True
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
            gen.mode = "stop"
            gen.running = False
            gen.breaker_closed = False
            gen.breaker_position = BreakerPosition.DISCONNECTED
            gen.cmd_close = False
            gen.freq = round(random.uniform(48.0, 52.0), 1)
            gen.amp = round(random.uniform(9500.0, 11500.0), 1)
            gen.phase_deg = round(random.uniform(-180.0, 180.0), 1)
            gen.actual_amp = 0.0
        sim.multimeter_mode = False
        sim.probe1_node = None
        sim.probe2_node = None
        sim.grounding_mode = "小电阻接地"
        sim.fault_reverse_bc = False

        self.phase_order_state.reset_pt_phase_orders()
        self.phase_order_state.reset_blackbox_orders()
        self.reset_pt_ratios_to_defaults()
        try:
            self.inject_fault(scenario_id)
        except Exception:
            traceback.print_exc()
            # 回滚到无故障安全态，避免 UI 停在半重置状态。
            self.phase_order_state.reset_pt_phase_orders()
            self.phase_order_state.reset_blackbox_orders()
            self.reset_pt_ratios_to_defaults()
            fc = self.sim_state.fault_config
            fc.scenario_id = ""
            fc.active = False
            fc.detected = False
            fc.repaired = False
            fc.params = {}
            try:
                self.inject_fault("")
            except Exception:
                traceback.print_exc()
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
                f"物理帧更新连续失败 {self._consecutive_tick_failures} 次（阶段: {stage}），控制台错误日志包含详细信息。"
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


def _access_root() -> Path:
    # 打包成 exe 后哈希文件在 exe 同级目录；源码运行时在项目根目录。
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _load_access_password_hash() -> str | None:
    try:
        content = (_access_root() / "access_password.hash").read_text(encoding="utf-8")
    except OSError:
        return None
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line.lower()
    return None


def _check_access_password() -> bool:
    expected = _load_access_password_hash()
    if not expected:
        QtWidgets.QMessageBox.critical(
            None, "无法启动", "访问密码文件缺失或损坏，请联系管理员。"
        )
        return False
    for remaining in (2, 1, 0):
        text, ok = QtWidgets.QInputDialog.getText(
            None, "访问验证", "请输入访问密码：", QtWidgets.QLineEdit.Password
        )
        if not ok:
            return False
        if hashlib.sha256(text.encode("utf-8")).hexdigest() == expected:
            return True
        if remaining:
            QtWidgets.QMessageBox.warning(
                None, "密码错误", f"密码错误，还可重试 {remaining} 次。"
            )
    QtWidgets.QMessageBox.critical(None, "验证失败", "密码错误次数过多，程序退出。")
    return False


if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")

    if not _check_access_password():
        sys.exit(0)

    ctrl = PowerSyncController()
    ctrl.ui.showMaximized()

    sys.exit(app.exec_())
