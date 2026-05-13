from __future__ import annotations

from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from ui.panels.control_panel import WidgetBuilderMixin
from ui.styles import apply_app_theme
from ui.tabs.circuit_tab import CircuitTab
from ui.tabs.waveform_tab import WaveformTab


ACCIDENT_IMAGE_PATH = Path(__file__).resolve().parents[1] / "image" / "Screenshot.png"
ACCIDENT_WARNING_TITLE = "\u4e00\u6b21\u4fa7\u5e26\u7535\u63a5\u89e6"


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
        self._run_controls_page.sync_pt_ratio_rows_from_state()
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
        ratio_updates = self.ctrl.consume_requested_pt_ratio_row_updates()
        if ratio_updates:
            self._run_controls_page.apply_pt_ratio_row_updates(ratio_updates)

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

    @staticmethod
    def _strip_accident_prefix(text: str, prefix: str) -> str:
        return text[len(prefix):].strip() if text.startswith(prefix) else text.strip()

    def _parse_accident_message(self, message: str) -> tuple[str, str, str, str]:
        parts = [part.strip() for part in message.split("\n\n") if part.strip()]
        risk = self._strip_accident_prefix(parts[0], "风险：") if parts else ACCIDENT_WARNING_TITLE
        consequence = self._strip_accident_prefix(parts[1], "后果：") if len(parts) > 1 else message
        caption = parts[2] if len(parts) > 2 else ""
        ending = parts[3] if len(parts) > 3 else "本次考核终止。"
        return risk, consequence, caption, ending

    def _show_accident_warning(self, title: str, message: str) -> None:
        risk, consequence, caption, ending = self._parse_accident_message(message)

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.resize(640, 700)
        dialog.setStyleSheet(
            """
            QDialog {
                background: #0f172a;
            }
            QLabel {
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                letter-spacing: 0px;
            }
            QPushButton {
                min-width: 110px;
                min-height: 34px;
                border-radius: 6px;
                background: #dc2626;
                color: white;
                font-weight: 700;
                font-size: 13px;
                padding: 6px 18px;
            }
            QPushButton:hover {
                background: #b91c1c;
            }
            """
        )

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        header = QtWidgets.QFrame()
        header.setStyleSheet(
            "QFrame {"
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7f1d1d, stop:1 #dc2626);"
            "border: 1px solid #fca5a5; border-radius: 12px;"
            "}"
        )
        header_layout = QtWidgets.QVBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(4)

        eyebrow_lbl = QtWidgets.QLabel("一次侧带电接触")
        eyebrow_lbl.setStyleSheet("font-size:12px; font-weight:700; color:#fecaca;")
        header_layout.addWidget(eyebrow_lbl)

        risk_lbl = QtWidgets.QLabel(risk)
        risk_lbl.setWordWrap(True)
        risk_lbl.setStyleSheet("font-size:26px; font-weight:900; color:#ffffff;")
        header_layout.addWidget(risk_lbl)
        layout.addWidget(header)

        consequence_panel = QtWidgets.QFrame()
        consequence_panel.setStyleSheet(
            "QFrame { background:#fff7ed; border:1px solid #fb923c; border-radius:10px; }"
        )
        consequence_layout = QtWidgets.QVBoxLayout(consequence_panel)
        consequence_layout.setContentsMargins(14, 10, 14, 10)
        consequence_layout.setSpacing(5)

        consequence_title = QtWidgets.QLabel("工程后果")
        consequence_title.setStyleSheet("font-size:12px; font-weight:900; color:#9a3412;")
        consequence_layout.addWidget(consequence_title)

        consequence_lbl = QtWidgets.QLabel(consequence)
        consequence_lbl.setWordWrap(True)
        consequence_lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        consequence_lbl.setStyleSheet("font-size:15px; font-weight:700; color:#431407; line-height:150%;")
        consequence_layout.addWidget(consequence_lbl)
        layout.addWidget(consequence_panel)

        if caption:
            caption_panel = QtWidgets.QFrame()
            caption_panel.setStyleSheet(
                "QFrame { background:#422006; border:1px solid #fbbf24; border-radius:10px; }"
            )
            caption_layout = QtWidgets.QVBoxLayout(caption_panel)
            caption_layout.setContentsMargins(14, 10, 14, 10)
            caption_lbl = QtWidgets.QLabel(caption)
            caption_lbl.setWordWrap(True)
            caption_lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            caption_lbl.setStyleSheet("font-size:18px; font-weight:900; color:#fde68a; line-height:150%;")
            caption_layout.addWidget(caption_lbl)
            layout.addWidget(caption_panel)

        if ACCIDENT_IMAGE_PATH.exists():
            pixmap = QtGui.QPixmap(str(ACCIDENT_IMAGE_PATH))
            if not pixmap.isNull():
                image_frame = QtWidgets.QFrame()
                image_frame.setStyleSheet(
                    "QFrame { background:#020617; border:1px solid #334155; border-radius:10px; }"
                )
                image_layout = QtWidgets.QVBoxLayout(image_frame)
                image_layout.setContentsMargins(8, 8, 8, 8)
                image_lbl = QtWidgets.QLabel()
                image_lbl.setAlignment(QtCore.Qt.AlignCenter)
                image_lbl.setPixmap(
                    pixmap.scaled(
                        520,
                        280,
                        QtCore.Qt.KeepAspectRatio,
                        QtCore.Qt.SmoothTransformation,
                    )
                )
                image_layout.addWidget(image_lbl)
                layout.addWidget(image_frame, 0, QtCore.Qt.AlignCenter)

        ending_lbl = QtWidgets.QLabel(ending)
        ending_lbl.setAlignment(QtCore.Qt.AlignCenter)
        ending_lbl.setStyleSheet(
            "font-size:18px; font-weight:900; color:#ffffff; background:#991b1b;"
            "border:1px solid #fca5a5; border-radius:8px; padding:8px 10px;"
        )
        layout.addWidget(ending_lbl)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        ok_button = buttons.button(QtWidgets.QDialogButtonBox.Ok)
        if ok_button is not None:
            ok_button.setText("我知道了")
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons, 0, QtCore.Qt.AlignRight)
        dialog.exec_()

    def show_warning(self, title: str, message: str) -> None:
        self._consume_controller_ui_requests()
        if title == ACCIDENT_WARNING_TITLE:
            self._show_accident_warning(title, message)
            return

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
