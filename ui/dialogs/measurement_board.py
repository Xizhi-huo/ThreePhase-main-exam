from __future__ import annotations

from collections import OrderedDict

from PyQt5 import QtCore, QtWidgets


_PHASES = ("A", "B", "C")
_SEQUENCE_LABELS = {
    "ABC": "正序",
    "BCA": "正序",
    "CAB": "正序",
    "ACB": "反序",
    "BAC": "反序",
    "CBA": "反序",
}


def show_measurement_board_dialog(owner, *, records, sim_state) -> None:
    dialog = MeasurementBoardDialog(owner, records=list(records or ()), sim_state=sim_state)
    dialog.exec_()


class MeasurementBoardDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, *, records, sim_state) -> None:
        super().__init__(parent)
        self.records = list(records or ())
        self.sim_state = sim_state
        self.setWindowTitle("测量数据分类看板")
        self.resize(860, 620)
        self.setMinimumSize(760, 520)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QtWidgets.QLabel("测量数据分类看板")
        header.setStyleSheet("font-size:18px; font-weight:700; color:#1f2937;")
        layout.addWidget(header)

        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs, 1)

        self._build_loop_tab()
        self._build_voltage_tab()
        self._build_phase_diff_tab()
        self._build_sequence_tab()

        close_btn = QtWidgets.QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_row = QtWidgets.QHBoxLayout()
        close_row.addStretch(1)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

    def _build_loop_tab(self) -> None:
        tab = self._scroll_tab()
        body = tab.widget().layout()
        matrix = {(g1, g2): None for g1 in _PHASES for g2 in _PHASES}
        for record in self.records:
            nodes = list(record.get("nodes") or [])
            if len(nodes) != 2 or not all(str(node).startswith("LOOP_") for node in nodes):
                continue
            parsed = [str(node).split("_") for node in nodes]
            if any(len(parts) != 3 for parts in parsed):
                continue
            left = parsed[0]
            right = parsed[1]
            if left[1] == "G2":
                left, right = right, left
            if left[1] == "G1" and right[1] == "G2":
                matrix[(left[2], right[2])] = self._format_value(record)

        if not any(value is not None for value in matrix.values()):
            body.addWidget(self._empty_label("暂无通断记录。"))
        else:
            body.addWidget(self._matrix_card("G1 ↔ G2 通断", [f"G2-{p}" for p in _PHASES], [f"G1-{p}" for p in _PHASES], matrix))
        self.tabs.addTab(tab, "通断")

    def _build_voltage_tab(self) -> None:
        tab = self._scroll_tab()
        body = tab.widget().layout()
        groups = {"PT1": OrderedDict(), "PT2": OrderedDict(), "PT3": OrderedDict()}
        for record in self.records:
            nodes = list(record.get("nodes") or [])
            parsed = self._parse_pt_pair(nodes)
            if parsed is None:
                continue
            pt1, ph1, pt2, ph2 = parsed
            if pt1 == pt2 and ph1 != ph2 and pt1 in groups:
                key = self._line_voltage_key(ph1, ph2)
                groups[pt1][key] = self._format_value(record)

        has_any = False
        for pt_name, values in groups.items():
            if not values:
                continue
            has_any = True
            body.addWidget(self._section_title(f"{pt_name} 电压"))
            body.addWidget(self._pair_list_card(values))
        if not has_any:
            body.addWidget(self._empty_label("暂无 PT 电压记录。"))
        self.tabs.addTab(tab, "电压")

    def _build_phase_diff_tab(self) -> None:
        tab = self._scroll_tab()
        body = tab.widget().layout()
        matrices = {
            "PT1": {(row, col): None for row in _PHASES for col in _PHASES},
            "PT3": {(row, col): None for row in _PHASES for col in _PHASES},
        }
        seen = {"PT1": False, "PT3": False}

        for record in self.records:
            nodes = list(record.get("nodes") or [])
            parsed = self._parse_pt_pair(nodes)
            if parsed is None:
                continue
            pt1, ph1, pt2, ph2 = parsed
            pair = {pt1, pt2}
            if "PT2" not in pair:
                continue
            other = "PT1" if "PT1" in pair else "PT3" if "PT3" in pair else None
            if other is None:
                continue
            other_phase = ph1 if pt1 == other else ph2
            pt2_phase = ph1 if pt1 == "PT2" else ph2
            matrices[other][(other_phase, pt2_phase)] = self._format_value(record)
            seen[other] = True

        has_any = False
        for other in ("PT1", "PT3"):
            if not seen[other]:
                continue
            has_any = True
            body.addWidget(self._matrix_card(
                f"{other} ↔ PT2 压差",
                [f"PT2-{p}" for p in _PHASES],
                [f"{other}-{p}" for p in _PHASES],
                matrices[other],
            ))
        if not has_any:
            body.addWidget(self._empty_label("暂无核相压差记录。"))
        self.tabs.addTab(tab, "压差")

    def _build_sequence_tab(self) -> None:
        tab = self._scroll_tab()
        body = tab.widget().layout()
        rows = []
        for record in self.records:
            if record.get("kind") != "phase_sequence":
                continue
            pt_name = str(record.get("pt_name") or "PT")
            rows.append((pt_name, self._format_value(record)))

        if not rows:
            body.addWidget(self._empty_label("暂无相序记录。"))
        else:
            values = OrderedDict(rows)
            body.addWidget(self._pair_list_card(values))
        self.tabs.addTab(tab, "相序")

    def _scroll_tab(self) -> QtWidgets.QScrollArea:
        area = QtWidgets.QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QtWidgets.QFrame.NoFrame)
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        layout.setAlignment(QtCore.Qt.AlignTop)
        area.setWidget(widget)
        return area

    def _matrix_card(self, title: str, columns: list[str], rows: list[str], data: dict) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setStyleSheet(self._card_style())
        layout = QtWidgets.QVBoxLayout(card)
        layout.setSpacing(8)
        layout.addWidget(self._section_title(title))

        matrix = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(matrix)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)

        fm = matrix.fontMetrics()
        row_header_w = max([fm.horizontalAdvance(row) for row in rows] + [0]) + 26
        col_w = max([fm.horizontalAdvance(col) for col in columns] + [0]) + 30
        value_w = max(
            [fm.horizontalAdvance(str(value)) for value in data.values() if value is not None]
            + [fm.horizontalAdvance("--")]
        ) + 34
        cell_w = max(72, col_w, value_w)

        grid.addWidget(self._matrix_header_label(""), 0, 0)
        for col_idx, col_name in enumerate(columns, start=1):
            label = self._matrix_header_label(col_name)
            label.setMinimumWidth(cell_w)
            grid.addWidget(label, 0, col_idx)
            grid.setColumnMinimumWidth(col_idx, cell_w)
            grid.setColumnStretch(col_idx, 1)

        grid.setColumnMinimumWidth(0, row_header_w)
        for row_idx, row_name in enumerate(rows, start=1):
            row_label = self._matrix_header_label(row_name)
            row_label.setMinimumWidth(row_header_w)
            grid.addWidget(row_label, row_idx, 0)
            row_phase = row_name.rsplit("-", 1)[-1]
            for col_idx, col_name in enumerate(columns, start=1):
                col_phase = col_name.rsplit("-", 1)[-1]
                text = data.get((row_phase, col_phase)) or "--"
                value_label = self._matrix_value_label(text)
                value_label.setMinimumWidth(cell_w)
                grid.addWidget(value_label, row_idx, col_idx)

        layout.addWidget(matrix)
        return card

    def _matrix_header_label(self, text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setMinimumHeight(30)
        label.setStyleSheet(
            "background:#f1f5f9; color:#334155; border:1px solid #cbd5e1; "
            "border-radius:5px; padding:5px 8px; font-weight:700;"
        )
        return label

    def _matrix_value_label(self, text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(str(text))
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setMinimumHeight(34)
        label.setStyleSheet(
            "background:#ffffff; color:#111827; border:1px solid #e2e8f0; "
            "border-radius:5px; padding:5px 8px; font-weight:700;"
        )
        return label

    def _pair_list_card(self, values: OrderedDict) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setStyleSheet(self._card_style())
        layout = QtWidgets.QGridLayout(card)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(8)
        for row, (name, value) in enumerate(values.items()):
            name_lbl = QtWidgets.QLabel(str(name))
            value_lbl = QtWidgets.QLabel(str(value))
            value_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            value_lbl.setStyleSheet("font-weight:700; color:#111827;")
            layout.addWidget(name_lbl, row, 0)
            layout.addWidget(value_lbl, row, 1)
        layout.setColumnStretch(1, 1)
        return card

    def _record_card(self, record: dict, title: str | None = None) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setStyleSheet(self._card_style())
        layout = QtWidgets.QVBoxLayout(card)
        layout.setSpacing(4)
        if title:
            layout.addWidget(self._section_title(title))
        top = QtWidgets.QLabel(f"#{record.get('no', '--')}  {self._category(record)}")
        top.setStyleSheet("color:#2563eb; font-weight:700;")
        target = QtWidgets.QLabel(self._format_target(record))
        value = QtWidgets.QLabel(self._format_value(record))
        value.setStyleSheet("font-size:15px; font-weight:800; color:#111827;")
        layout.addWidget(top)
        layout.addWidget(target)
        layout.addWidget(value)
        return card

    def _section_title(self, text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setStyleSheet("font-size:14px; font-weight:700; color:#111827;")
        return label

    def _empty_label(self, text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setStyleSheet("color:#64748b; padding:24px; font-size:13px;")
        return label

    @staticmethod
    def _card_style() -> str:
        return (
            "QFrame { background:#ffffff; border:1px solid #dbe4f0; "
            "border-radius:8px; padding:6px; }"
        )

    def _category(self, record: dict) -> str:
        if record.get("kind") == "phase_sequence":
            return "相序"
        nodes = list(record.get("nodes") or [])
        if len(nodes) != 2:
            return "其他"
        if all(str(node).startswith("LOOP_") for node in nodes):
            return "通断"
        parsed = self._parse_pt_pair(nodes)
        if parsed is None:
            return "其他"
        pt1, ph1, pt2, ph2 = parsed
        if pt1 == pt2 and pt1 in {"PT1", "PT2", "PT3"} and ph1 != ph2:
            return "电压"
        if "PT2" in {pt1, pt2} and ({pt1, pt2} & {"PT1", "PT3"}):
            return "压差"
        return "其他"

    def _format_target(self, record: dict) -> str:
        if record.get("kind") == "phase_sequence":
            return str(record.get("pt_name") or "未选择 PT")
        nodes = list(record.get("nodes") or [])
        if len(nodes) != 2:
            return "未选择测点"
        return " ↔ ".join(self._compact_node_label(node) for node in nodes)

    def _format_value(self, record: dict) -> str:
        if record.get("kind") == "phase_sequence":
            sequence = str(record.get("phase_sequence") or record.get("value") or "unknown")
            if sequence and sequence not in {"unknown", "FAULT"}:
                return f"{sequence}（{_SEQUENCE_LABELS.get(sequence, '反序')}）"
            return "----"

        value = record.get("value")
        nodes = list(record.get("nodes") or [])
        if isinstance(value, (int, float)):
            pt_name = self._record_intra_pt_name(nodes)
            if pt_name is not None:
                return f"{value:.2f}V/{value * self._pt_ratio_for_name(pt_name):.2f}V"
            return f"{value:.2f} V"
        return self._compact_reading(record.get("reading"))

    @staticmethod
    def _parse_pt_pair(nodes) -> tuple[str, str, str, str] | None:
        if len(nodes) != 2:
            return None
        parsed = []
        for node in nodes:
            parts = str(node).rsplit("_", 1)
            if len(parts) != 2:
                return None
            pt_name, phase = parts
            if pt_name not in {"PT1", "PT2", "PT3"} or phase not in _PHASES:
                return None
            parsed.append((pt_name, phase))
        return parsed[0][0], parsed[0][1], parsed[1][0], parsed[1][1]

    @staticmethod
    def _record_intra_pt_name(nodes) -> str | None:
        parsed = MeasurementBoardDialog._parse_pt_pair(nodes)
        if parsed is None:
            return None
        pt1, ph1, pt2, ph2 = parsed
        if pt1 == pt2 and ph1 != ph2:
            return pt1
        return None

    @staticmethod
    def _line_voltage_key(ph1: str, ph2: str) -> str:
        pair = {ph1, ph2}
        if pair == {"A", "B"}:
            return "A-B"
        if pair == {"B", "C"}:
            return "B-C"
        if pair == {"A", "C"}:
            return "C-A"
        return f"{ph1}-{ph2}"

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
    def _compact_node_label(node: str) -> str:
        parts = str(node).split("_")
        if len(parts) == 3 and parts[0] == "LOOP":
            return f"{parts[1]}-{parts[2]}"
        if len(parts) == 2 and parts[0].startswith("PT"):
            return f"{parts[0]}-{parts[1]}"
        return str(node).replace("_", "-")

    @staticmethod
    def _compact_reading(reading) -> str:
        text = str(reading or "--").replace("⚠️", "").replace("⚠", "").strip()
        return text or "--"