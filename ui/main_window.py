from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

from ui.panels.control_panel import WidgetBuilderMixin
from ui.styles import apply_app_theme
from ui.tabs.circuit_tab import CircuitTab
from ui.tabs.waveform_tab import WaveformTab


class PowerSyncUI(WidgetBuilderMixin, QtWidgets.QMainWindow):
    """Main window for the standalone free-operation exam console."""

    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        self.setWindowTitle("三相电并网考核系统")

        self._resize_timer = QtCore.QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(150)
        self._resize_timer.timeout.connect(self._on_resize_done)
        self._is_resizing = False

        central = QtWidgets.QWidget()
        central.setObjectName("appRoot")
        self.setCentralWidget(central)
        root_layout = QtWidgets.QHBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setObjectName("mainTabWidget")
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.tabBar().setExpanding(False)
        self.tab_widget.tabBar().setElideMode(QtCore.Qt.ElideRight)
        root_layout.addWidget(self.tab_widget, stretch=1)

        self.ctrl_container = QtWidgets.QScrollArea()
        self.ctrl_container.setObjectName("controlSidebarScroll")
        self.ctrl_container.setFixedWidth(520)
        self.ctrl_container.setWidgetResizable(True)
        self.ctrl_container.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.ctrl_inner = QtWidgets.QWidget()
        self.ctrl_inner.setObjectName("controlSidebar")
        self.ctrl_inner.setProperty("panelSurface", True)
        self.ctrl_container.setWidget(self.ctrl_inner)
        root_layout.addWidget(self.ctrl_container)

        self.ctrl_layout = QtWidgets.QVBoxLayout(self.ctrl_inner)
        self.ctrl_layout.setAlignment(QtCore.Qt.AlignTop)
        self.ctrl_layout.setContentsMargins(0, 0, 0, 0)
        self.ctrl_layout.setSpacing(8)

        self._build_control_panel()

        self._waveform_tab = WaveformTab(self.ctrl, parent=self)
        self.tab_widget.addTab(self._waveform_tab, "实时波形与同期表")

        self._circuit_tab = CircuitTab(
            self.ctrl,
            sidebar_badges={
                "bus_status_lbl": self.bus_status_lbl,
                "bus_reference_lbl": self.bus_reference_lbl,
                "relay_lbl": self.relay_lbl,
                "status1_lbl": self.status1_lbl,
                "status2_lbl": self.status2_lbl,
            },
            apply_badge_tone=self._apply_badge_tone,
            on_circuit_click=self._on_circuit_click,
            is_test_mode_active=self._is_test_mode_active,
            get_current_test_step=self._current_test_step,
            parent=self,
        )
        self.tab_widget.addTab(self._circuit_tab, "母排拓扑与环流监测")

        apply_app_theme(QtWidgets.QApplication.instance())
        self.statusBar().showMessage("考核模式：自由操作台")

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self._is_resizing = True
        self._resize_timer.start()
        super().resizeEvent(event)

    def _on_resize_done(self) -> None:
        self._is_resizing = False

    def _is_test_mode_active(self) -> bool:
        return False

    def _current_test_step(self) -> int:
        return 0

    @property
    def ax_circuit(self):
        return self._circuit_tab.ax_circuit

    @property
    def canvas2(self):
        return self._circuit_tab.canvas2

    @property
    def phase_seq_meter(self):
        return self._circuit_tab.phase_seq_meter

    def _draw_waveform_canvases(self) -> None:
        self._waveform_tab.redraw_canvases()

    def rebuild_circuit_diagram(self) -> None:
        self._circuit_tab.rebuild_circuit_diagram()

    def enable_phase_seq_meter(self) -> None:
        self._circuit_tab.enable_phase_seq_meter()
        self.tab_widget.setCurrentIndex(1)

    def connect_phase_seq_meter(self, pt_name: str) -> None:
        self._circuit_tab.connect_phase_seq_meter(pt_name)
        self.tab_widget.setCurrentIndex(1)

    def disconnect_phase_seq_meter(self) -> None:
        self._circuit_tab.disconnect_phase_seq_meter()

    def sync_runtime_controls_from_state(self) -> None:
        sim = self.ctrl.sim_state
        self._sync_button_group(self._mode_bg, sim.system_mode)
        self._sync_button_group(self._gnd_bg, sim.grounding_mode)
        for checkbox, value in (
            (self.multimeter_cb, sim.multimeter_mode),
            (self.show_gen_wires_cb, sim.show_gen_wires),
        ):
            checkbox.blockSignals(True)
            checkbox.setChecked(bool(value))
            checkbox.blockSignals(False)
        self.pause_btn.setText("恢复物理时空" if sim.paused else "暂停整个物理空间")
        self._apply_button_tone(
            self.pause_btn,
            "success" if sim.paused else "warning",
            hero=True,
        )
        self._gen1_card.refresh()
        self._gen2_card.refresh()

    @staticmethod
    def _sync_button_group(group, value) -> None:
        for button in group.buttons():
            button.blockSignals(True)
            button.setChecked(button.property("value") == value)
            button.blockSignals(False)

    def _consume_controller_ui_requests(self) -> None:
        tab_index = self.ctrl.consume_requested_ui_tab()
        if tab_index is not None and 0 <= tab_index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(tab_index)
        self.ctrl.consume_requested_pt_ratio_row_updates()

    def render_visuals(self, rs) -> None:
        self._consume_controller_ui_requests()
        self._waveform_tab.render(rs)
        self._circuit_tab.render(rs)
        self._update_generator_buttons()
        self._update_free_exam_panel()

        if self._is_resizing:
            return
        if self.tab_widget.currentIndex() == 0:
            self._draw_waveform_canvases()
        elif self.tab_widget.currentIndex() == 1:
            self._circuit_tab.redraw_canvas()

    def show_warning(self, title: str, message: str) -> None:
        self._consume_controller_ui_requests()
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.resize(520, 260)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title_lbl = QtWidgets.QLabel(title)
        title_lbl.setStyleSheet("font-size:14px; font-weight:bold; color:#8b0000;")
        layout.addWidget(title_lbl)

        msg_lbl = QtWidgets.QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        msg_lbl.setStyleSheet("font-size:12px; color:#222222;")
        layout.addWidget(msg_lbl, 1)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec_()
