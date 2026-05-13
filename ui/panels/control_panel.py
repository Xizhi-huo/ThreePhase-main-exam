from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from domain.node_map import NODES
from ui.dialogs.blackbox import show_blackbox_dialog
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
        self.gov_gain_slider = param_page.gov_gain_slider
        self.gov_gain_label = param_page.gov_gain_label
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
            self.show_warning("尚未开始考核", "当前未处于考核进行状态。")
        self._update_free_exam_panel()

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
    def _point_segment_distance(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
        dx = bx - ax
        dy = by - ay
        length_sq = dx * dx + dy * dy
        if length_sq <= 1e-12:
            return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
        t = ((px - ax) * dx + (py - ay) * dy) / length_sq
        t = max(0.0, min(1.0, t))
        cx = ax + t * dx
        cy = ay + t * dy
        return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5

    def _find_primary_voltage_contact_node(self, x: float, y: float) -> str | None:
        point_threshold = 0.060
        segment_threshold = 0.018
        best_node = None
        best_dist = point_threshold

        for node_name, data in NODES.items():
            if not node_name.startswith("PRI_PT"):
                continue
            dist = ((x - data[0]) ** 2 + (y - data[1]) ** 2) ** 0.5
            if dist < best_dist:
                best_node = node_name
                best_dist = dist

        pt_cy = {"PT1": 0.355, "PT2": 0.205, "PT3": 0.355}
        h = 0.168
        for pt_name, cy in pt_cy.items():
            lower_bus_y = cy - h * 0.13
            bottom_y = cy - h * 0.46
            for phase in ("A", "B", "C"):
                primary_node = f"PRI_{pt_name}_{phase}"
                secondary_node = f"{pt_name}_{phase}"
                if primary_node not in NODES or secondary_node not in NODES:
                    continue
                sx, sy = NODES[primary_node][:2]
                tx = NODES[secondary_node][0]
                segments = (
                    (tx, lower_bus_y, tx, bottom_y),
                    (tx, bottom_y, tx, sy),
                    (tx, sy, sx, sy),
                )
                for ax, ay, bx, by in segments:
                    if self._point_segment_distance(x, y, ax, ay, bx, by) <= segment_threshold:
                        return primary_node

        return best_node

    def _on_circuit_click(self, event) -> None:
        if self._circuit_tab.get_phase_wiring_status() != PhaseWiringStatus.IDLE:
            if self._circuit_tab.handle_phase_wiring_click(event):
                return

        if not self.ctrl.sim_state.multimeter_mode:
            return
        if event.inaxes != self.ax_circuit or event.xdata is None or event.ydata is None:
            return

        primary_contact_node = self._find_primary_voltage_contact_node(event.xdata, event.ydata)
        if primary_contact_node:
            accident_message = self.ctrl.handle_primary_probe_contact(primary_contact_node)
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
            accident_message = self.ctrl.handle_primary_probe_contact(closest_node)
            if accident_message:
                self.show_warning("一次侧带电接触", accident_message)
                self.sync_runtime_controls_from_state()
                self._update_free_exam_panel()
                return

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
