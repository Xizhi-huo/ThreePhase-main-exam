from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from domain.enums import AVAILABLE_MODES, SystemMode
from ui.widgets.control_panel._widget_tokens import (
    apply_badge_tone,
    apply_button_tone,
    apply_toggle_tone,
    set_props,
)


class RunControlsPage(QtWidgets.QWidget):
    def __init__(
        self,
        *,
        sim_state,
        on_start_free_exam,
        on_reset_free_exam,
        on_record_measurement,
        on_show_blackbox,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.sim_state = sim_state
        self.on_start_free_exam_cb = on_start_free_exam
        self.on_reset_free_exam_cb = on_reset_free_exam
        self.on_record_measurement_cb = on_record_measurement
        self.on_show_blackbox_cb = on_show_blackbox
        self._measurement_log_expanded = False
        self._last_record_count = 0
        self._last_record_log_text = ""
        self._build()

    def _build(self) -> None:
        self.setObjectName("controlPage0")
        self.setProperty("panelSurface", True)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)
        layout.setAlignment(QtCore.Qt.AlignTop)

        mode_group = QtWidgets.QGroupBox("系统运行模式")
        mode_layout = QtWidgets.QVBoxLayout(mode_group)
        mode_layout.setSpacing(2)
        self.mode_bg = QtWidgets.QButtonGroup(self)
        for mode_value in AVAILABLE_MODES:
            available = mode_value == SystemMode.ISOLATED_BUS
            radio = QtWidgets.QRadioButton(mode_value if available else f"{mode_value} (待开发)")
            radio.setProperty("value", mode_value)
            radio.setEnabled(available)
            radio.setChecked(self.sim_state.system_mode == mode_value)
            radio.toggled.connect(lambda checked, v=mode_value: self._on_mode_changed(v, checked))
            self.mode_bg.addButton(radio)
            mode_layout.addWidget(radio)
        layout.addWidget(mode_group)

        start_group = QtWidgets.QGroupBox("考核启动")
        start_group.setProperty("cardTone", "warning")
        start_layout = QtWidgets.QVBoxLayout(start_group)
        start_layout.setContentsMargins(8, 8, 8, 8)
        start_layout.setSpacing(8)

        self.fp_btn_random = QtWidgets.QPushButton("开始随机考核")
        self.fp_btn_random.setCheckable(True)
        set_props(self.fp_btn_random, segment=True, segmentTone="danger")
        self.fp_btn_random.clicked.connect(self.on_start_free_exam_cb)
        start_layout.addWidget(self.fp_btn_random)

        self.fp_status_lbl = QtWidgets.QLabel("未开始：点击随机故障开始考核。")
        self.fp_status_lbl.setWordWrap(True)
        set_props(self.fp_status_lbl, mutedText=True, badge=True, tone="warning")
        start_layout.addWidget(self.fp_status_lbl)
        layout.addWidget(start_group)

        self.exam_group = QtWidgets.QGroupBox("自由操作台")
        exam_layout = QtWidgets.QVBoxLayout(self.exam_group)
        exam_layout.setContentsMargins(8, 8, 8, 8)
        exam_layout.setSpacing(8)

        self.exam_status_lbl = QtWidgets.QLabel("未开始")
        self.exam_status_lbl.setWordWrap(True)
        apply_badge_tone(self.exam_status_lbl, "warning")
        exam_layout.addWidget(self.exam_status_lbl)

        action_row = QtWidgets.QWidget()
        action_layout = QtWidgets.QHBoxLayout(action_row)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)
        self.btn_record_measurement = QtWidgets.QPushButton("记录当前测量")
        self.btn_reset_exam = QtWidgets.QPushButton("重置")
        apply_button_tone(self.btn_record_measurement, "primary")
        apply_button_tone(self.btn_reset_exam, "warning")
        self.btn_record_measurement.clicked.connect(self.on_record_measurement_cb)
        self.btn_reset_exam.clicked.connect(self.on_reset_free_exam_cb)
        action_layout.addWidget(self.btn_record_measurement, 2)
        action_layout.addWidget(self.btn_reset_exam, 1)
        exam_layout.addWidget(action_row)

        blackbox_group = QtWidgets.QGroupBox("黑盒检查")
        blackbox_layout = QtWidgets.QGridLayout(blackbox_group)
        blackbox_layout.setContentsMargins(8, 8, 8, 8)
        blackbox_layout.setSpacing(6)
        self.blackbox_buttons = {}
        for idx, target in enumerate(("G1", "G2", "PT1", "PT3")):
            button = QtWidgets.QPushButton(target)
            apply_button_tone(button, "secondary", secondary=True)
            button.clicked.connect(lambda checked=False, t=target: self.on_show_blackbox_cb(t))
            self.blackbox_buttons[target] = button
            blackbox_layout.addWidget(button, idx // 2, idx % 2)
        exam_layout.addWidget(blackbox_group)

        self.measurement_log_btn = QtWidgets.QPushButton("测量记录 0")
        self.measurement_log_btn.setCheckable(True)
        self.measurement_log_btn.setToolTip("展开或收起已记录的测量数据")
        set_props(self.measurement_log_btn, segment=True, segmentTone="primary")
        self.measurement_log_btn.clicked.connect(self._on_measurement_log_toggled)
        exam_layout.addWidget(self.measurement_log_btn)

        self.measurement_log_view = QtWidgets.QPlainTextEdit()
        self.measurement_log_view.setReadOnly(True)
        self.measurement_log_view.setLineWrapMode(QtWidgets.QPlainTextEdit.WidgetWidth)
        self.measurement_log_view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.measurement_log_view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.measurement_log_view.setMinimumHeight(72)
        self.measurement_log_view.setMaximumHeight(132)
        self.measurement_log_view.setProperty("measurementLog", True)
        self.measurement_log_view.setVisible(False)
        exam_layout.addWidget(self.measurement_log_view)
        layout.addWidget(self.exam_group)

        self.bus_status_lbl = QtWidgets.QLabel("母排：无电")
        apply_badge_tone(self.bus_status_lbl, "warning")
        self.bus_status_lbl.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.bus_status_lbl)

        self.bus_reference_lbl = QtWidgets.QLabel("参考基准：无")
        apply_badge_tone(self.bus_reference_lbl, "neutral")
        self.bus_reference_lbl.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.bus_reference_lbl)

        grounding_group = QtWidgets.QGroupBox("中性点接地（三相四线 N 线）")
        grounding_layout = QtWidgets.QHBoxLayout(grounding_group)
        grounding_layout.setSpacing(4)
        self.gnd_bg = QtWidgets.QButtonGroup(self)
        for label, value in [("断开", "断开"), ("小电阻(10Ω)", "小电阻接地"), ("直接接地", "直接接地")]:
            radio = QtWidgets.QRadioButton(label)
            radio.setProperty("value", value)
            radio.setChecked(self.sim_state.grounding_mode == value)
            radio.toggled.connect(lambda checked, v=value: self._on_grounding_changed(v, checked))
            self.gnd_bg.addButton(radio)
            grounding_layout.addWidget(radio)
        layout.addWidget(grounding_group)

        self.multimeter_cb = QtWidgets.QCheckBox("拿取万用表")
        self.multimeter_cb.setChecked(self.sim_state.multimeter_mode)
        apply_toggle_tone(self.multimeter_cb, "warning")
        self.multimeter_cb.toggled.connect(self._on_multimeter_toggled)
        layout.addWidget(self.multimeter_cb)

        self.show_gen_wires_cb = QtWidgets.QCheckBox("显示发电机与母排之间的连线")
        self.show_gen_wires_cb.setChecked(self.sim_state.show_gen_wires)
        apply_toggle_tone(self.show_gen_wires_cb, "info")
        self.show_gen_wires_cb.toggled.connect(lambda value: setattr(self.sim_state, "show_gen_wires", value))
        layout.addWidget(self.show_gen_wires_cb)

        self._generator_layout = QtWidgets.QVBoxLayout()
        self._generator_layout.setContentsMargins(0, 0, 0, 0)
        self._generator_layout.setSpacing(8)
        layout.addLayout(self._generator_layout)

        self.refresh_free_exam_panel(None)

    def add_generator_card(self, card) -> None:
        self._generator_layout.addWidget(card)

    def refresh_free_exam_panel(self, state) -> None:
        result = getattr(state, "result", "idle") if state is not None else "idle"
        active = bool(getattr(state, "active", False)) if state is not None else False
        attempted = bool(getattr(state, "final_close_attempted", False)) if state is not None else False
        fail_reason = getattr(state, "fail_reason", "") if state is not None else ""
        records = list(getattr(state, "measurement_records", [])) if state is not None else []

        if result == "passed":
            text, tone = "通过：Gen2 已成功并入母排。", "success"
        elif result == "failed":
            reason = f"\n原因：{fail_reason}" if fail_reason else ""
            text, tone = f"未通过：最终 Gen2 并母未成功。{reason}", "danger"
        elif result == "pending":
            text, tone = "已提交最终合闸，正在根据母排并入状态判定。", "warning"
        elif active:
            text, tone = "考核进行中：随机故障已隐藏注入，完成排查后使用 Gen2 普通合闸按钮并母。", "info"
        else:
            text, tone = "未开始：点击随机故障开始考核。", "warning"

        self.fp_status_lbl.setText(text)
        apply_badge_tone(self.fp_status_lbl, tone)
        self.exam_status_lbl.setText(text)
        apply_badge_tone(self.exam_status_lbl, tone)
        self.fp_btn_random.setChecked(active and result in {"running", "pending"})
        self.fp_btn_random.setText("重新开始随机考核" if active or attempted else "开始随机考核")
        self.btn_record_measurement.setEnabled(active and result in {"running", "pending"})
        for button in self.blackbox_buttons.values():
            button.setEnabled(active and result in {"running", "pending"})

        self._refresh_measurement_log(records)
    def _on_measurement_log_toggled(self, checked) -> None:
        self._measurement_log_expanded = bool(checked)
        self._sync_measurement_log_visibility()
        if self._measurement_log_expanded:
            QtCore.QTimer.singleShot(0, self._scroll_measurement_log_to_bottom)

    def _refresh_measurement_log(self, records) -> None:
        record_count = len(records)
        if record_count == 0:
            self._measurement_log_expanded = False
        elif record_count > self._last_record_count:
            self._measurement_log_expanded = True
        previous_count = self._last_record_count
        self._last_record_count = record_count

        lines = []
        for row, record in enumerate(records):
            no = record.get("no", row + 1)
            nodes = self._format_nodes(record.get("nodes"))
            value = self._format_record_value(record)
            lines.append(f"#{no}  {nodes}  {value}")
        log_text = "\n".join(lines)
        if log_text != self._last_record_log_text:
            self.measurement_log_view.setPlainText(log_text)
            self._last_record_log_text = log_text
        self.measurement_log_btn.setText(f"测量记录 {record_count}")
        self.measurement_log_btn.setEnabled(record_count > 0)
        self._sync_measurement_log_visibility()
        if record_count > previous_count and self._measurement_log_expanded:
            QtCore.QTimer.singleShot(0, self._scroll_measurement_log_to_bottom)

    def _scroll_measurement_log_to_bottom(self) -> None:
        bar = self.measurement_log_view.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _sync_measurement_log_visibility(self) -> None:
        visible = self._last_record_count > 0 and self._measurement_log_expanded
        self.measurement_log_btn.blockSignals(True)
        self.measurement_log_btn.setChecked(visible)
        self.measurement_log_btn.blockSignals(False)
        self.measurement_log_view.setVisible(visible)

    def _format_nodes(self, nodes) -> str:
        if not nodes:
            return "--"
        try:
            return " - ".join(str(node) for node in nodes if node)
        except TypeError:
            return str(nodes)

    def _format_record_value(self, record) -> str:
        value = record.get("value")
        if isinstance(value, (int, float)):
            return f"{value:.2f} V"
        reading = str(record.get("reading") or "--")
        for token in ("  [正常]", "  [异常]", "  [无电压]", " [正常]", " [异常]", " [无电压]"):
            reading = reading.replace(token, "")
        return reading.replace("⚠️", "").replace("⚠", "").strip()

    def _on_mode_changed(self, value, checked) -> None:
        if checked:
            self.sim_state.system_mode = value

    def _on_grounding_changed(self, value, checked) -> None:
        if checked:
            self.sim_state.grounding_mode = value

    def _on_multimeter_toggled(self, checked) -> None:
        self.sim_state.multimeter_mode = checked
