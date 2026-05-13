from __future__ import annotations

from collections import OrderedDict

from PyQt5 import QtCore, QtGui, QtWidgets

from domain.constants import DEFAULT_PT_RATIO_ROWS
from domain.enums import AVAILABLE_MODES
from domain.node_map import NODES
from ui.widgets.control_panel._widget_tokens import (
    apply_badge_tone,
    apply_button_tone,
    apply_toggle_tone,
    set_props,
)


class TriangleSpinBox(QtWidgets.QSpinBox):
    """QSpinBox with explicitly painted up/down triangles for themed UIs."""

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        option = QtWidgets.QStyleOptionSpinBox()
        self.initStyleOption(option)
        style = self.style()
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor("#475569" if self.isEnabled() else "#cbd5e1"))
        for sub_control, points in (
            (QtWidgets.QStyle.SC_SpinBoxUp, ((0, -3), (-4, 3), (4, 3))),
            (QtWidgets.QStyle.SC_SpinBoxDown, ((0, 3), (-4, -3), (4, -3))),
        ):
            rect = style.subControlRect(QtWidgets.QStyle.CC_SpinBox, option, sub_control, self)
            if not rect.isValid():
                continue
            center = rect.center()
            polygon = QtGui.QPolygon([
                QtCore.QPoint(center.x() + dx, center.y() + dy)
                for dx, dy in points
            ])
            painter.drawPolygon(polygon)
        painter.end()


class RunControlsPage(QtWidgets.QWidget):
    def __init__(
        self,
        *,
        sim_state,
        on_start_free_exam,
        on_reset_free_exam,
        on_record_measurement,
        on_show_blackbox,
        on_enable_phase_seq_meter,
        on_disable_phase_seq_meter,
        on_pt_ratio_changed,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.sim_state = sim_state
        self.on_start_free_exam_cb = on_start_free_exam
        self.on_reset_free_exam_cb = on_reset_free_exam
        self.on_record_measurement_cb = on_record_measurement
        self.on_show_blackbox_cb = on_show_blackbox
        self.on_enable_phase_seq_meter_cb = on_enable_phase_seq_meter
        self.on_disable_phase_seq_meter_cb = on_disable_phase_seq_meter
        self.on_pt_ratio_changed_cb = on_pt_ratio_changed
        self._active_phase_seq_pt = None
        self._measurement_log_expanded = False
        self._last_record_count = 0
        self._last_record_signature = None
        self._measurement_records = []
        self._measurement_filter = "全部"
        self._measurement_filter_buttons = {}
        self._pt_ratio_inputs = {}
        self._pt_ratio_value_labels = {}
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
            radio = QtWidgets.QRadioButton(mode_value)
            radio.setProperty("value", mode_value)
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

        self.fp_status_lbl = QtWidgets.QLabel("未开始：等待随机故障启动。")
        self.fp_status_lbl.setWordWrap(True)
        set_props(self.fp_status_lbl, mutedText=True, badge=True, tone="warning")
        start_layout.addWidget(self.fp_status_lbl)
        layout.addWidget(start_group)

        self.exam_group = QtWidgets.QGroupBox("自由操作台")
        exam_layout = QtWidgets.QVBoxLayout(self.exam_group)
        exam_layout.setContentsMargins(8, 8, 8, 8)
        exam_layout.setSpacing(8)

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

        self.measurement_log_panel = QtWidgets.QWidget()
        self.measurement_log_panel.setProperty("measurementPanel", True)
        measurement_panel_layout = QtWidgets.QVBoxLayout(self.measurement_log_panel)
        measurement_panel_layout.setContentsMargins(8, 8, 8, 8)
        measurement_panel_layout.setSpacing(8)

        self.measurement_filter_row = QtWidgets.QWidget()
        self.measurement_filter_row.setProperty("measurementFilterRow", True)
        self.measurement_filter_layout = QtWidgets.QHBoxLayout(self.measurement_filter_row)
        self.measurement_filter_layout.setContentsMargins(0, 0, 0, 0)
        self.measurement_filter_layout.setSpacing(6)
        measurement_panel_layout.addWidget(self.measurement_filter_row)

        self.measurement_log_scroll = QtWidgets.QScrollArea()
        self.measurement_log_scroll.setWidgetResizable(True)
        self.measurement_log_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.measurement_log_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.measurement_log_scroll.setMinimumHeight(150)
        self.measurement_log_scroll.setMaximumHeight(280)
        self.measurement_log_scroll.setProperty("measurementLogScroll", True)

        self.measurement_cards_widget = QtWidgets.QWidget()
        self.measurement_cards_layout = QtWidgets.QVBoxLayout(self.measurement_cards_widget)
        self.measurement_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.measurement_cards_layout.setSpacing(8)
        self.measurement_cards_layout.setAlignment(QtCore.Qt.AlignTop)
        self.measurement_log_scroll.setWidget(self.measurement_cards_widget)
        measurement_panel_layout.addWidget(self.measurement_log_scroll)

        self.measurement_log_panel.setVisible(False)
        exam_layout.addWidget(self.measurement_log_panel)
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

        self.phase_seq_cb = QtWidgets.QCheckBox("拿取相序仪")
        self.phase_seq_cb.setChecked(False)
        apply_toggle_tone(self.phase_seq_cb, "info")
        self.phase_seq_cb.toggled.connect(self._on_phase_seq_meter_toggled)
        layout.addWidget(self.phase_seq_cb)

        self.show_gen_wires_cb = QtWidgets.QCheckBox("显示发电机与母排之间的连线")
        self.show_gen_wires_cb.setChecked(self.sim_state.show_gen_wires)
        apply_toggle_tone(self.show_gen_wires_cb, "info")
        self.show_gen_wires_cb.toggled.connect(lambda value: setattr(self.sim_state, "show_gen_wires", value))
        layout.addWidget(self.show_gen_wires_cb)

        self.pt_ratio_group = self._build_pt_ratio_group()
        layout.addWidget(self.pt_ratio_group)

        self._generator_layout = QtWidgets.QVBoxLayout()
        self._generator_layout.setContentsMargins(0, 0, 0, 0)
        self._generator_layout.setSpacing(8)
        layout.addLayout(self._generator_layout)

        self.refresh_free_exam_panel(None)

    def add_generator_card(self, card) -> None:
        self._generator_layout.addWidget(card)

    _PT_RATIO_ROWS = (
        ("PT1", "pt_gen_ratio"),
        ("PT2", "pt_bus_ratio"),
        ("PT3", "pt3_ratio"),
    )

    def _build_pt_ratio_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("PT 变比")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        header = self._build_pt_ratio_row_header()
        layout.addWidget(header)

        for label, ratio_attr in self._PT_RATIO_ROWS:
            row_widget = QtWidgets.QWidget()
            row = QtWidgets.QHBoxLayout(row_widget)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(25)

            name_lbl = QtWidgets.QLabel(label)
            name_lbl.setFixedWidth(34)
            name_lbl.setStyleSheet("font-size:12px; font-weight:800;")

            primary_spin = self._make_pt_ratio_spinbox(1, 50000, 100, 86)
            colon_lbl = QtWidgets.QLabel(":")
            colon_lbl.setFixedWidth(80)
            colon_lbl.setAlignment(QtCore.Qt.AlignCenter)
            colon_lbl.setStyleSheet("font-size:13px; font-weight:800; color:#334155;")
            secondary_spin = self._make_pt_ratio_spinbox(1, 9999, 1, 88)

            ratio_lbl = QtWidgets.QLabel()
            ratio_lbl.setFixedWidth(58)
            ratio_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            ratio_lbl.setStyleSheet("font-size:11px; color:#64748b; font-weight:700;")

            primary_value, secondary_value = DEFAULT_PT_RATIO_ROWS[ratio_attr]
            primary_spin.setValue(primary_value)
            secondary_spin.setValue(secondary_value)
            primary_spin.valueChanged.connect(
                lambda value, attr=ratio_attr: self._on_pt_ratio_row_changed(attr)
            )
            secondary_spin.valueChanged.connect(
                lambda value, attr=ratio_attr: self._on_pt_ratio_row_changed(attr)
            )

            self._pt_ratio_inputs[ratio_attr] = (primary_spin, secondary_spin)
            self._pt_ratio_value_labels[ratio_attr] = ratio_lbl
            self._refresh_pt_ratio_label(ratio_attr)

            row.addWidget(name_lbl)
            row.addWidget(primary_spin)
            row.addWidget(colon_lbl)
            row.addWidget(secondary_spin)
            row.addWidget(ratio_lbl)
            row.addStretch(1)
            layout.addWidget(row_widget)

        return group

    def _build_pt_ratio_row_header(self) -> QtWidgets.QWidget:
        header = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(header)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(5)
        for text, width in (("", 34), ("一次侧", 86), ("", 10), ("二次侧", 68), ("倍率", 58)):
            label = QtWidgets.QLabel(text)
            label.setFixedWidth(width)
            label.setAlignment(QtCore.Qt.AlignCenter)
            label.setStyleSheet("font-size:11px; color:#64748b; font-weight:700;")
            row.addWidget(label)
        row.addStretch(1)
        return header

    def _make_pt_ratio_spinbox(self, vmin: int, vmax: int, step: int, width: int) -> TriangleSpinBox:
        spinbox = TriangleSpinBox()
        spinbox.setRange(vmin, vmax)
        spinbox.setSingleStep(step)
        spinbox.setFixedWidth(width)
        spinbox.setFixedHeight(28)
        spinbox.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.UpDownArrows)
        spinbox.setProperty("compactInput", True)
        spinbox.setProperty("ptRatioInput", True)
        spinbox.setStyleSheet("""
            QSpinBox[ptRatioInput="true"] {
                padding: 3px 18px 3px 7px;
                border-radius: 7px;
                font-size: 12px;
                font-weight: 700;
            }
            QSpinBox[ptRatioInput="true"]::up-button,
            QSpinBox[ptRatioInput="true"]::down-button {
                width: 16px;
                background: #f8fafc;
                border-left: 1px solid #cbd5e1;
            }
            QSpinBox[ptRatioInput="true"]::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                border-top-right-radius: 7px;
                border-bottom: 1px solid #dbe4ee;
            }
            QSpinBox[ptRatioInput="true"]::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                border-bottom-right-radius: 7px;
            }
            QSpinBox[ptRatioInput="true"]::up-arrow,
            QSpinBox[ptRatioInput="true"]::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }
        """)
        return spinbox

    def apply_pt_ratio_row_updates(self, updates) -> None:
        for ratio_attr, row_values in dict(updates or {}).items():
            try:
                primary_value, secondary_value = row_values
            except (TypeError, ValueError):
                continue
            self._set_pt_ratio_row(ratio_attr, primary_value, secondary_value)

    def sync_pt_ratio_rows_from_state(self) -> None:
        for ratio_attr in self._pt_ratio_inputs:
            ratio = float(getattr(self.sim_state, ratio_attr, 0.0) or 0.0)
            if ratio <= 0:
                continue
            default_primary, _ = DEFAULT_PT_RATIO_ROWS[ratio_attr]
            inferred_secondary = max(1, int(round(default_primary / ratio)))
            self._set_pt_ratio_row(ratio_attr, default_primary, inferred_secondary)

    def _set_pt_ratio_row(self, ratio_attr: str, primary_value: int, secondary_value: int) -> None:
        inputs = self._pt_ratio_inputs.get(ratio_attr)
        if inputs is None:
            return
        primary_spin, secondary_spin = inputs
        primary_spin.blockSignals(True)
        secondary_spin.blockSignals(True)
        primary_spin.setValue(max(1, int(primary_value)))
        secondary_spin.setValue(max(1, int(secondary_value)))
        primary_spin.blockSignals(False)
        secondary_spin.blockSignals(False)
        self._refresh_pt_ratio_label(ratio_attr)

    def _refresh_pt_ratio_label(self, ratio_attr: str) -> None:
        inputs = self._pt_ratio_inputs.get(ratio_attr)
        label = self._pt_ratio_value_labels.get(ratio_attr)
        if inputs is None or label is None:
            return
        primary_spin, secondary_spin = inputs
        ratio = primary_spin.value() / max(1, secondary_spin.value())
        label.setText(f"{ratio:.2f}")

    def _on_pt_ratio_row_changed(self, ratio_attr: str) -> None:
        inputs = self._pt_ratio_inputs.get(ratio_attr)
        if inputs is None:
            return
        primary_spin, secondary_spin = inputs
        primary_value = primary_spin.value()
        secondary_value = secondary_spin.value()
        setattr(self.sim_state, ratio_attr, primary_value / secondary_value)
        self._refresh_pt_ratio_label(ratio_attr)
        self.on_pt_ratio_changed_cb(ratio_attr, primary_value, secondary_value)

    def refresh_free_exam_panel(self, state) -> None:
        result = getattr(state, "result", "idle") if state is not None else "idle"
        active = bool(getattr(state, "active", False)) if state is not None else False
        attempted = bool(getattr(state, "final_close_attempted", False)) if state is not None else False
        records = list(getattr(state, "measurement_records", [])) if state is not None else []

        if result == "passed":
            text, tone = "通过：Gen2 已成功并入母排。", "success"
        elif result == "failed":
            text, tone = "未通过：最终 Gen2 并母未成功。", "danger"
        elif result == "pending":
            text, tone = "已提交最终合闸，正在根据母排并入状态判定。", "warning"
        elif active:
            text, tone = "考核进行中：随机故障已隐藏注入。", "info"
        else:
            text, tone = "未开始：等待随机故障启动。", "warning"

        self.fp_status_lbl.setText(text)
        apply_badge_tone(self.fp_status_lbl, tone)
        self.fp_btn_random.setChecked(active and result in {"running", "pending"})
        self.fp_btn_random.setText("重新开始随机考核" if active or attempted else "开始随机考核")
        self.btn_record_measurement.setEnabled(active and result in {"running", "pending"})
        for button in self.blackbox_buttons.values():
            button.setEnabled(active and result in {"running", "pending"})

        self._refresh_measurement_log(records)

    def reset_measurement_tool_state(self) -> None:
        self._put_away_phase_seq_meter()
        self._put_away_multimeter()

    def _on_phase_seq_meter_toggled(self, checked) -> None:
        if checked:
            self._put_away_multimeter()
            self.on_enable_phase_seq_meter_cb()
        else:
            self.on_disable_phase_seq_meter_cb()

    def _put_away_multimeter(self) -> None:
        self.sim_state.multimeter_mode = False
        self.sim_state.probe1_node = None
        self.sim_state.probe2_node = None
        self.multimeter_cb.blockSignals(True)
        self.multimeter_cb.setChecked(False)
        self.multimeter_cb.blockSignals(False)

    def _put_away_phase_seq_meter(self) -> None:
        self.phase_seq_cb.blockSignals(True)
        self.phase_seq_cb.setChecked(False)
        self.phase_seq_cb.blockSignals(False)
        self.on_disable_phase_seq_meter_cb()

    def _on_measurement_log_toggled(self, checked) -> None:
        self._measurement_log_expanded = bool(checked)
        self._sync_measurement_log_visibility()
        if self._measurement_log_expanded:
            QtCore.QTimer.singleShot(0, self._scroll_measurement_log_to_bottom)

    def _refresh_measurement_log(self, records) -> None:
        record_count = len(records)
        previous_count = self._last_record_count
        if record_count == 0:
            self._measurement_log_expanded = False
            self._measurement_filter = "全部"
        elif record_count > self._last_record_count:
            self._measurement_log_expanded = True
        self._last_record_count = record_count
        self._measurement_records = records

        signature = self._build_measurement_signature(records)
        if signature != self._last_record_signature:
            self._last_record_signature = signature
            self._rebuild_measurement_filters(records)
            self._rebuild_measurement_cards(records)

        self.measurement_log_btn.setText(f"测量记录 {record_count}")
        self.measurement_log_btn.setEnabled(record_count > 0)
        self._sync_measurement_log_visibility()
        if record_count > previous_count and self._measurement_log_expanded:
            QtCore.QTimer.singleShot(0, self._scroll_measurement_log_to_bottom)

    def _build_measurement_signature(self, records) -> tuple:
        return tuple(
            (
                record.get("no", row + 1),
                record.get("kind", "multimeter"),
                tuple(record.get("nodes") or ()),
                self._measurement_category(record),
                self._format_record_value(record),
                record.get("phase_sequence"),
            )
            for row, record in enumerate(records)
        )

    def _measurement_category(self, record) -> str:
        if record.get("kind") == "phase_sequence":
            return "相序测量"
        nodes = list(record.get("nodes") or [])
        if len(nodes) != 2:
            return "未选测点"
        n1, n2 = nodes
        if n1.startswith("LOOP_") and n2.startswith("LOOP_"):
            return "回路测量"
        pt1 = n1.rsplit("_", 1)[0] if "_" in n1 else ""
        pt2 = n2.rsplit("_", 1)[0] if "_" in n2 else ""
        if pt1 == pt2 and pt1 in {"PT1", "PT2", "PT3"}:
            return "PT电压"
        if {pt1, pt2} & {"PT1", "PT3"} and "PT2" in {pt1, pt2}:
            return "PT压差"
        return "其他测量"

    def _measurement_counts(self, records) -> OrderedDict[str, int]:
        counts = OrderedDict()
        for record in records:
            category = self._measurement_category(record)
            counts[category] = counts.get(category, 0) + 1
        return counts

    def _rebuild_measurement_filters(self, records) -> None:
        self._clear_layout(self.measurement_filter_layout)
        counts = self._measurement_counts(records)
        available = ["全部", *counts.keys()]
        if self._measurement_filter not in available:
            self._measurement_filter = "全部"
        self._measurement_filter_buttons.clear()

        filter_specs = [("全部", len(records)), *counts.items()]
        for category, count in filter_specs:
            button = QtWidgets.QPushButton(f"{category} {count}")
            button.setCheckable(True)
            button.setChecked(category == self._measurement_filter)
            set_props(button, segment=True, segmentTone="primary")
            button.clicked.connect(lambda checked=False, c=category: self._set_measurement_filter(c))
            self._measurement_filter_buttons[category] = button
            self.measurement_filter_layout.addWidget(button)
        self.measurement_filter_layout.addStretch(1)

    def _set_measurement_filter(self, category: str) -> None:
        if category == self._measurement_filter:
            self._sync_measurement_filter_buttons()
            return
        self._measurement_filter = category
        self._sync_measurement_filter_buttons()
        self._rebuild_measurement_cards(self._measurement_records)
        QtCore.QTimer.singleShot(0, self._scroll_measurement_log_to_top)

    def _sync_measurement_filter_buttons(self) -> None:
        for category, button in self._measurement_filter_buttons.items():
            button.blockSignals(True)
            button.setChecked(category == self._measurement_filter)
            button.blockSignals(False)

    def _rebuild_measurement_cards(self, records) -> None:
        self._clear_layout(self.measurement_cards_layout)
        visible_records = [
            record for record in records
            if self._measurement_filter == "全部" or self._measurement_category(record) == self._measurement_filter
        ]
        for row, record in enumerate(visible_records):
            self.measurement_cards_layout.addWidget(self._create_measurement_card(record, row))
        self.measurement_cards_layout.addStretch(1)

    def _create_measurement_card(self, record, row: int) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setProperty("measurementCard", True)
        layout = QtWidgets.QHBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(7)

        no = record.get("no", row + 1)
        no_lbl = QtWidgets.QLabel(f"#{no}")
        no_lbl.setProperty("measurementNo", True)
        no_lbl.setMinimumWidth(28)

        type_lbl = QtWidgets.QLabel(self._measurement_category(record))
        type_lbl.setProperty("measurementType", True)
        type_lbl.setAlignment(QtCore.Qt.AlignCenter)

        target_lbl = QtWidgets.QLabel(self._format_record_target(record))
        target_lbl.setProperty("measurementNodes", True)
        target_lbl.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

        value_lbl = QtWidgets.QLabel(self._format_record_value(record))
        value_lbl.setProperty("measurementValue", True)
        value_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        value_lbl.setMinimumWidth(96)

        layout.addWidget(no_lbl)
        layout.addWidget(type_lbl)
        layout.addWidget(target_lbl, 1)
        layout.addWidget(value_lbl)
        return card

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def _scroll_measurement_log_to_bottom(self) -> None:
        bar = self.measurement_log_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _scroll_measurement_log_to_top(self) -> None:
        bar = self.measurement_log_scroll.verticalScrollBar()
        bar.setValue(0)

    def _sync_measurement_log_visibility(self) -> None:
        visible = self._last_record_count > 0 and self._measurement_log_expanded
        self.measurement_log_btn.blockSignals(True)
        self.measurement_log_btn.setChecked(visible)
        self.measurement_log_btn.blockSignals(False)
        self.measurement_log_panel.setVisible(visible)

    def _format_record_target(self, record) -> str:
        if record.get("kind") == "phase_sequence":
            return str(record.get("pt_name") or "未选择 PT")

        nodes = list(record.get("nodes") or [])
        if len(nodes) != 2:
            return "未选择测点"

        return " ↔ ".join(self._compact_node_label(node) for node in nodes)

    def _format_node_label(self, node: str) -> str:
        data = NODES.get(str(node))
        if data and len(data) >= 5:
            return str(data[4])
        return str(node).replace("_", "-")

    def _compact_node_label(self, node: str) -> str:
        parts = str(node).split("_")
        if len(parts) == 3 and parts[0] == "LOOP":
            return f"{parts[1]}-{parts[2]}"
        if len(parts) == 2 and parts[0].startswith("PT"):
            return f"{parts[0]}-{parts[1]}"
        return self._format_node_label(node).replace("回路", "")

    def _format_record_value(self, record) -> str:
        if record.get("kind") == "phase_sequence":
            sequence = str(record.get("phase_sequence") or record.get("value") or "unknown")
            reading = str(record.get("reading") or "").strip()
            if sequence and sequence not in {"unknown", "FAULT"}:
                return f"{sequence}（{self._phase_sequence_label(sequence)}）"
            return self._compact_reading(reading) or "----"

        value = record.get("value")
        nodes = list(record.get("nodes") or [])
        is_loop = len(nodes) == 2 and all(str(node).startswith("LOOP_") for node in nodes)
        if isinstance(value, (int, float)) and not is_loop:
            pt_name = self._record_intra_pt_name(nodes)
            if pt_name is not None:
                primary_value = value * self._pt_ratio_for_name(pt_name)
                return f"{value:.2f}V/{primary_value:.2f}V"
            return f"{value:.2f} V"

        reading = str(record.get("reading") or "--")
        return self._compact_reading(reading)

    @staticmethod
    def _record_intra_pt_name(nodes) -> str | None:
        if len(nodes) != 2:
            return None
        pt_names = []
        phases = []
        for node in nodes:
            parts = str(node).rsplit("_", 1)
            if len(parts) != 2:
                return None
            pt_name, phase = parts
            pt_names.append(pt_name)
            phases.append(phase)
        if pt_names[0] == pt_names[1] and pt_names[0] in {"PT1", "PT2", "PT3"} and phases[0] != phases[1]:
            return pt_names[0]
        return None

    def _pt_ratio_for_name(self, pt_name: str) -> float:
        ratio_attr = {
            "PT1": "pt_gen_ratio",
            "PT2": "pt_bus_ratio",
            "PT3": "pt3_ratio",
        }.get(pt_name)
        if ratio_attr is None:
            return 1.0
        return float(getattr(self.sim_state, ratio_attr, 1.0) or 1.0)

    @staticmethod
    def _compact_reading(reading: str) -> str:
        text = str(reading or "--").replace("⚠️", "").replace("⚠", "").strip()
        return text or "--"

    @staticmethod
    def _phase_sequence_label(sequence: str) -> str:
        if sequence in {"ABC", "BCA", "CAB"}:
            return "正序"
        if sequence in {"FAULT", "unknown"}:
            return "----"
        return "反序"

    def _on_mode_changed(self, value, checked) -> None:
        if checked:
            self.sim_state.system_mode = value

    def _on_grounding_changed(self, value, checked) -> None:
        if checked:
            self.sim_state.grounding_mode = value

    def _on_multimeter_toggled(self, checked) -> None:
        if checked and self.phase_seq_cb.isChecked():
            self._put_away_phase_seq_meter()
        self.sim_state.multimeter_mode = checked
        if not checked:
            self.sim_state.probe1_node = None
            self.sim_state.probe2_node = None
