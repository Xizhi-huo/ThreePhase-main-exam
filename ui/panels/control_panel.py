from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from domain.enums import BreakerPosition
from domain.node_map import NODES
from ui.dialogs.blackbox import show_blackbox_dialog
from ui.dialogs.measurement_board import show_measurement_board_dialog
from ui.tabs.circuit_tab import PhaseWiringStatus
from ui.widgets.control_panel import GeneratorCard, ParamControlsPage, RunControlsPage
from ui.widgets.control_panel._widget_tokens import (
    apply_badge_tone,
    apply_button_tone,
    apply_toggle_tone,
    refresh_widget_styles,
    set_props,
)


class WidgetBuilderMixin:
    """Right-side control panel for the standalone exam console."""

    LIVE_LINE_HIT_TOLERANCE_PX = 5.0
    _PRIMARY_WIRE_XS = {
        1: (0.240, 0.280, 0.320),
        2: (0.680, 0.720, 0.760),
    }
    _PRIMARY_BUS_Y = (0.115, 0.090, 0.065)
    _PRIMARY_GEN_SIDE_Y = 0.455
    _PRIMARY_CB_TOP_Y = 0.200
    _PRIMARY_CB_BOTTOM_Y = 0.130

    @staticmethod
    def _refresh_widget_styles(*widgets):
        refresh_widget_styles(*widgets)

    @staticmethod
    def _set_props(widget, **props):
        set_props(widget, **props)

    def _apply_button_tone(self, button, tone="primary", *, hero=False, secondary=False, muted=False):
        apply_button_tone(button, tone, hero=hero, secondary=secondary, muted=muted)

    def _apply_badge_tone(self, widget, tone="neutral"):
        apply_badge_tone(widget, tone)

    def _apply_toggle_tone(self, widget, tone="primary"):
        apply_toggle_tone(widget, tone)

    def _build_control_panel(self) -> None:
        ctrl = self.ctrl

        title = QtWidgets.QLabel("三相电并网考核系统")
        self._set_props(title, sidebarTitle=True)
        title.setAlignment(QtCore.Qt.AlignCenter)
        self.ctrl_layout.addWidget(title)

        switcher = QtWidgets.QWidget()
        switcher.setObjectName("panelSwitcher")
        switcher.setProperty("toolbarStrip", True)
        switcher_layout = QtWidgets.QHBoxLayout(switcher)
        switcher_layout.setContentsMargins(0, 0, 0, 0)
        switcher_layout.setSpacing(8)

        self._cp_btn_run = QtWidgets.QPushButton("运行控制")
        self._cp_btn_param = QtWidgets.QPushButton("参数设置")
        for button in (self._cp_btn_run, self._cp_btn_param):
            button.setFixedHeight(36)
            self._set_props(button, segment=True, segmentTone="primary")
            button.setCheckable(True)
            switcher_layout.addWidget(button)
        self._cp_btn_run.setChecked(True)
        self.ctrl_layout.addWidget(switcher)

        self._cp_stack = QtWidgets.QStackedWidget()
        self.ctrl_layout.addWidget(self._cp_stack, 1)

        run_page = RunControlsPage(
            sim_state=ctrl.sim_state,
            on_start_free_exam=self._on_start_free_exam,
            on_reset_free_exam=self._on_reset_free_exam,
            on_record_measurement=self._on_free_exam_record_measurement,
            on_show_measurement_board=self._show_measurement_board,
            on_show_blackbox=self._show_free_exam_blackbox,
            on_enable_phase_seq_meter=self._enable_free_exam_phase_seq_meter,
            on_disable_phase_seq_meter=self._disable_free_exam_phase_seq_meter,
            on_pt_ratio_changed=self._on_pt_ratio_changed,
        )
        param_page = ParamControlsPage(
            sim_state=ctrl.sim_state,
            on_toggle_pause=ctrl.toggle_pause,
        )
        gen1_card = GeneratorCard(
            sim_state=ctrl.sim_state,
            gen_id=1,
            on_toggle_engine=ctrl.toggle_engine,
            on_toggle_breaker=ctrl.toggle_breaker,
            on_change_breaker_position=ctrl.change_breaker_position,
        )
        gen2_card = GeneratorCard(
            sim_state=ctrl.sim_state,
            gen_id=2,
            on_toggle_engine=ctrl.toggle_engine,
            on_toggle_breaker=ctrl.toggle_breaker,
            on_change_breaker_position=ctrl.change_breaker_position,
        )
        run_page.add_generator_card(gen1_card)
        run_page.add_generator_card(gen2_card)
        self._cp_stack.addWidget(run_page)
        self._cp_stack.addWidget(param_page)

        def _switch(index: int) -> None:
            self._cp_stack.setCurrentIndex(index)
            self._cp_btn_run.setChecked(index == 0)
            self._cp_btn_param.setChecked(index == 1)

        self._cp_btn_run.clicked.connect(lambda: _switch(0))
        self._cp_btn_param.clicked.connect(lambda: _switch(1))

        self._run_controls_page = run_page
        self._param_controls_page = param_page
        self._gen1_card = gen1_card
        self._gen2_card = gen2_card

        self._mode_bg = run_page.mode_bg
        self._fp_status_lbl = run_page.fp_status_lbl
        self.bus_status_lbl = run_page.bus_status_lbl
        self.bus_reference_lbl = run_page.bus_reference_lbl
        self._gnd_bg = run_page.gnd_bg
        self.multimeter_cb = run_page.multimeter_cb
        self.show_gen_wires_cb = run_page.show_gen_wires_cb

        self.btn_engine1 = gen1_card.engine_btn
        self.btn_engine2 = gen2_card.engine_btn
        self.btn_breaker1 = gen1_card.breaker_btn
        self.btn_breaker2 = gen2_card.breaker_btn
        self.status1_lbl = gen1_card.status_lbl
        self.status2_lbl = gen2_card.status_lbl
        self._gen1_mode_bg = gen1_card.mode_bg
        self._gen2_mode_bg = gen2_card.mode_bg
        self._gen1_pos_bg = gen1_card.pos_bg
        self._gen2_pos_bg = gen2_card.pos_bg

        self.sim_speed_slider = param_page.sim_speed_slider
        self.sim_speed_label = param_page.sim_speed_label
        self.rotate_phasor_cb = param_page.rotate_phasor_cb
        self.relay_lbl = param_page.relay_lbl
        self.pause_btn = param_page.pause_btn

        self._update_free_exam_panel()

    def _on_start_free_exam(self) -> None:
        self.ctrl.start_random_free_exam()
        self.sync_runtime_controls_from_state()
        self._update_free_exam_panel()
        try:
            self.tab_widget.setCurrentIndex(1)
        except Exception:
            pass

    def _on_reset_free_exam(self) -> None:
        self.ctrl.reset_free_exam()
        self._run_controls_page.reset_measurement_tool_state()
        self.sync_runtime_controls_from_state()
        self._update_free_exam_panel()

    def _on_free_exam_record_measurement(self) -> None:
        if not self.ctrl.record_free_exam_measurement():
            reason = self.ctrl.record_free_exam_measurement_reject_reason()
            if reason == "inactive":
                self.show_warning("尚未开始考核", "当前未处于考核进行状态。")
        self._update_free_exam_panel()

    def _show_measurement_board(self, records) -> None:
        show_measurement_board_dialog(self, records=records, sim_state=self.ctrl.sim_state)

    def _enable_free_exam_phase_seq_meter(self) -> None:
        self.enable_phase_seq_meter()

    def _disable_free_exam_phase_seq_meter(self) -> None:
        self.disconnect_phase_seq_meter()

    def _on_pt_ratio_changed(self, ratio_attr: str, primary_value: int, secondary_value: int) -> None:
        self.ctrl.update_pt_ratio(ratio_attr, primary_value, secondary_value)
        self._update_free_exam_panel()

    def _show_free_exam_blackbox(self, target: str) -> None:
        if not self.ctrl.is_free_exam_active():
            self.show_warning("尚未开始考核", "当前未处于考核进行状态。")
            return
        show_blackbox_dialog(self, api=self.ctrl, step=0, target=target)
        self._update_free_exam_panel()

    def _update_free_exam_panel(self) -> None:
        page = getattr(self, "_run_controls_page", None)
        if page is not None:
            page.refresh_free_exam_panel(getattr(self.ctrl, "free_exam_state", None))

    @staticmethod
    def _point_segment_projected_distance(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float | None:
        dx = bx - ax
        dy = by - ay
        length_sq = dx * dx + dy * dy
        if length_sq <= 1e-12:
            return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
        t = ((px - ax) * dx + (py - ay) * dy) / length_sq
        if t < 0.0 or t > 1.0:
            return None
        cx = ax + t * dx
        cy = ay + t * dy
        return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5

    def _primary_live_line_segments(self, gen_id: int):
        gen = self.ctrl.sim_state.gen1 if gen_id == 1 else self.ctrl.sim_state.gen2
        if not gen.running:
            return ()

        segments = []
        for x, bus_y in zip(self._PRIMARY_WIRE_XS[gen_id], self._PRIMARY_BUS_Y):
            segments.append((x, self._PRIMARY_GEN_SIDE_Y, x, self._PRIMARY_CB_TOP_Y))
            if gen.breaker_position == BreakerPosition.WORKING and gen.breaker_closed:
                segments.append((x, self._PRIMARY_CB_TOP_Y, x, self._PRIMARY_CB_BOTTOM_Y))
                segments.append((x, self._PRIMARY_CB_BOTTOM_Y, x, bus_y))
        return tuple(segments)

    def _find_live_primary_line_contact(self, event) -> int | None:
        if event.x is None or event.y is None:
            return None

        best_gen_id = None
        best_dist = self.LIVE_LINE_HIT_TOLERANCE_PX
        for gen_id in (1, 2):
            for ax, ay, bx, by in self._primary_live_line_segments(gen_id):
                start_px, start_py = self.ax_circuit.transData.transform((ax, ay))
                end_px, end_py = self.ax_circuit.transData.transform((bx, by))
                dist = self._point_segment_projected_distance(
                    float(event.x),
                    float(event.y),
                    float(start_px),
                    float(start_py),
                    float(end_px),
                    float(end_py),
                )
                if dist is not None and dist <= best_dist:
                    best_gen_id = gen_id
                    best_dist = dist
        return best_gen_id

    def _on_circuit_click(self, event) -> None:
        if self._circuit_tab.get_phase_wiring_status() != PhaseWiringStatus.IDLE:
            if self._circuit_tab.handle_phase_wiring_click(event):
                return

        if not self.ctrl.sim_state.multimeter_mode:
            return
        if event.inaxes != self.ax_circuit or event.xdata is None or event.ydata is None:
            return

        primary_line_gen_id = self._find_live_primary_line_contact(event)
        if primary_line_gen_id is not None:
            accident_message = self.ctrl.handle_primary_line_contact(primary_line_gen_id)
            if accident_message:
                self.show_warning("一次侧带电接触", accident_message)
                self.sync_runtime_controls_from_state()
                self._update_free_exam_panel()
                return
        closest_node = None
        min_dist = 0.04
        for name, data in NODES.items():
            dist = ((event.xdata - data[0]) ** 2 + (event.ydata - data[1]) ** 2) ** 0.5
            if dist < min_dist:
                closest_node = name
                min_dist = dist

        if closest_node:
            sim = self.ctrl.sim_state
            if sim.probe1_node is None:
                sim.probe1_node = closest_node
            elif sim.probe2_node is None and closest_node != sim.probe1_node:
                sim.probe2_node = closest_node
            else:
                sim.probe1_node = closest_node
                sim.probe2_node = None

    def _update_generator_buttons(self) -> None:
        self._gen1_card.refresh()
        self._gen2_card.refresh()
