from PyQt5 import QtCore, QtWidgets

from domain.enums import BreakerPosition

from ui.widgets.control_panel._widget_tokens import (
    apply_badge_tone,
    apply_button_tone,
)


class GeneratorCard(QtWidgets.QGroupBox):
    def __init__(
        self,
        *,
        sim_state,
        gen_id: int,
        on_toggle_engine,
        on_toggle_breaker,
        on_change_breaker_position,
        parent=None,
    ) -> None:
        title = f"发电机 {gen_id} (Gen {gen_id} - {'虚线' if gen_id == 1 else '点划线'})"
        super().__init__(title, parent)
        self.sim_state = sim_state
        self.gen_id = gen_id
        self.toggle_engine_cb = on_toggle_engine
        self.toggle_breaker_cb = on_toggle_breaker
        self.change_breaker_position_cb = on_change_breaker_position
        self.entry_map = {}
        self._build()

    def _generator(self):
        return self.sim_state.gen1 if self.gen_id == 1 else self.sim_state.gen2

    def _build(self):
        gen = self._generator()
        self.setProperty("cardTone", "info" if self.gen_id == 1 else "default")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(6)

        specs = [
            ("频率(Hz)", 450, 550, int(gen.freq * 10), 10, "freq", 48.0, 52.0),
            ("幅值(V)", 0, 15000, int(gen.amp), 1, "amp", 0.0, 15000.0),
            ("相位(°)", -1800, 1800, int(gen.phase_deg * 10), 10, "phase_deg", -180.0, 180.0),
        ]
        for label, vmin, vmax, init, scale, attr, clamp_lo, clamp_hi in specs:
            row_widget = QtWidgets.QWidget()
            row = QtWidgets.QHBoxLayout(row_widget)
            row.setContentsMargins(0, 0, 0, 0)

            lbl = QtWidgets.QLabel(label)
            lbl.setFixedWidth(80)
            lbl.setStyleSheet("font-size:12px;")

            slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            slider.setRange(vmin, vmax)
            slider.setValue(init)
            slider.setFixedWidth(145)

            entry = QtWidgets.QLineEdit(f"{getattr(gen, attr):.1f}")
            entry.setFixedWidth(68)
            entry.setStyleSheet("font-size:12px;")

            slider.valueChanged.connect(
                lambda val, a=attr, s=scale, e=entry, lo=clamp_lo, hi=clamp_hi:
                self._on_slider_changed(a, s, e, lo, hi, val)
            )
            entry.returnPressed.connect(
                lambda a=attr, s=scale, sl=slider, e=entry, lo=clamp_lo, hi=clamp_hi:
                self._on_entry_changed(a, s, sl, e, lo, hi)
            )
            entry.editingFinished.connect(
                lambda a=attr, s=scale, sl=slider, e=entry, lo=clamp_lo, hi=clamp_hi:
                self._on_entry_changed(a, s, sl, e, lo, hi)
            )

            row.addWidget(lbl)
            row.addWidget(slider)
            row.addWidget(entry)
            layout.addWidget(row_widget)
            self.entry_map[attr] = (slider, entry)

        mode_position_row = QtWidgets.QWidget()
        mode_position_layout = QtWidgets.QGridLayout(mode_position_row)
        mode_position_layout.setContentsMargins(0, 0, 0, 0)
        mode_position_layout.setHorizontalSpacing(55)
        mode_position_layout.setVerticalSpacing(20)

        mode_position_layout.addWidget(QtWidgets.QLabel("PCC模式:"), 0, 0)
        self.mode_bg = QtWidgets.QButtonGroup(self)
        mode_options = [("停机(0)", "stop"), ("手动", "manual")]
        for col, (text, value) in enumerate(mode_options, start=1):
            radio = QtWidgets.QRadioButton(text)
            radio.setProperty("value", value)
            radio.setChecked(gen.mode == value)
            radio.toggled.connect(lambda checked, v=value: self._on_mode_toggled(v, checked))
            self.mode_bg.addButton(radio)
            mode_position_layout.addWidget(radio, 0, col)

        mode_position_layout.addWidget(QtWidgets.QLabel("开关柜:"), 1, 0)
        self.pos_bg = QtWidgets.QButtonGroup(self)
        for col, (text, value) in enumerate([
            ("脱开", BreakerPosition.DISCONNECTED),
            ("试验", BreakerPosition.TEST),
            ("工作", BreakerPosition.WORKING),
        ], start=1):
            radio = QtWidgets.QRadioButton(text)
            radio.setProperty("value", value)
            radio.setChecked(gen.breaker_position == value)
            radio.toggled.connect(lambda checked, v=value: self._on_position_toggled(v, checked))
            self.pos_bg.addButton(radio)
            mode_position_layout.addWidget(radio, 1, col)

        mode_position_layout.setColumnStretch(4, 1)
        layout.addWidget(mode_position_row)

        self.status_lbl = QtWidgets.QLabel("断路器: OPEN")
        apply_badge_tone(self.status_lbl, "info")
        self.status_lbl.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.status_lbl)

        button_row = QtWidgets.QWidget()
        button_layout = QtWidgets.QHBoxLayout(button_row)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(6)

        self.engine_btn = QtWidgets.QPushButton("起机 (Start)")
        self.engine_btn.setFixedWidth(130)
        apply_button_tone(self.engine_btn, "success")
        self.engine_btn.clicked.connect(lambda: self.toggle_engine_cb(self.gen_id))

        self.breaker_btn = QtWidgets.QPushButton("控合 (Close)")
        self.breaker_btn.setFixedWidth(130)
        apply_button_tone(self.breaker_btn, "primary")
        self.breaker_btn.clicked.connect(lambda: self.toggle_breaker_cb(self.gen_id))

        button_layout.addWidget(self.engine_btn)
        button_layout.addWidget(self.breaker_btn)
        layout.addWidget(button_row)

    def _on_slider_changed(self, attr, scale, entry, clamp_lo, clamp_hi, value):
        result = round(value / scale, 3)
        result = max(clamp_lo, min(clamp_hi, result))
        setattr(self._generator(), attr, result)
        entry.setText(f"{result:.1f}")

    def _on_entry_changed(self, attr, scale, slider, entry, clamp_lo, clamp_hi):
        try:
            value = max(clamp_lo, min(clamp_hi, float(entry.text())))
        except ValueError:
            return
        setattr(self._generator(), attr, value)
        slider.blockSignals(True)
        slider.setValue(int(value * scale))
        slider.blockSignals(False)
        entry.setText(f"{value:.1f}")

    def _on_mode_toggled(self, value, checked):
        if checked:
            self._generator().mode = value

    def _on_position_toggled(self, value, checked):
        if not checked:
            return
        gen = self._generator()
        if value == gen.breaker_position:
            return
        if not self.change_breaker_position_cb(self.gen_id, value):
            self._sync_button_group(self.pos_bg, gen.breaker_position)

    def refresh(self):
        gen = self._generator()
        is_manual = gen.mode == "manual"
        is_running = gen.running
        breaker_closed = gen.breaker_closed
        allow_engine_toggle = is_running or is_manual

        self.engine_btn.setEnabled(allow_engine_toggle)
        self.engine_btn.setText("停机 (Stop)" if is_running else "起机 (Start)")
        if is_running:
            apply_button_tone(self.engine_btn, "warning")
        elif allow_engine_toggle:
            apply_button_tone(self.engine_btn, "success")
        else:
            apply_button_tone(self.engine_btn, "primary", muted=True)

        self.breaker_btn.setEnabled(is_manual)
        self.breaker_btn.setText("控分 (Open)" if breaker_closed else "控合 (Close)")
        if breaker_closed:
            apply_button_tone(self.breaker_btn, "danger")
        else:
            apply_button_tone(self.breaker_btn, "primary")

        for attr, (slider, entry) in self.entry_map.items():
            value = getattr(gen, attr)
            scale = 10 if attr in ("freq", "phase_deg") else 1
            slider.blockSignals(True)
            slider.setValue(int(value * scale))
            slider.blockSignals(False)
            if not entry.hasFocus():
                entry.blockSignals(True)
                entry.setText(f"{value:.1f}")
                entry.blockSignals(False)

        self._sync_button_group(self.mode_bg, gen.mode)
        self._sync_button_group(self.pos_bg, gen.breaker_position)

    @staticmethod
    def _sync_button_group(group, value):
        for button in group.buttons():
            button.blockSignals(True)
            button.setChecked(button.property("value") == value)
            button.blockSignals(False)
