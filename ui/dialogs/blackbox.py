from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from ui.tabs._step_style import apply_button_tone, set_props
from ui.widgets.gen_wiring_widget import GenWiringWidget
from ui.widgets.pt_wiring_widget import PTWiringWidget


def show_blackbox_dialog(owner, *, api, step: int, target: str) -> None:
    if not api.can_inspect_blackbox():
        return

    allow_repair = api.can_repair_in_blackbox()
    blackbox_state = api.get_blackbox_runtime_state(target)

    dlg = QtWidgets.QDialog(owner)
    set_props(dlg, themedDialog=True)
    dlg.setMinimumWidth(360)
    layout = QtWidgets.QVBoxLayout(dlg)
    layout.setSpacing(8)
    layout.setContentsMargins(12, 10, 12, 10)

    widget = None
    repair_target = blackbox_state.get("repair_target") if allow_repair else None
    initial_order = None
    initial_pri_order = None
    initial_sec_order = None
    initial_sec_polarity = None
    initial_sec_ratio_secondary = None

    if target in ("G1", "G2"):
        dlg.setWindowTitle(f"发电机 {target} 机端接线检查")
        order = blackbox_state["order"]
        mapping = {"A": order[0], "B": order[1], "C": order[2]}
        caption = QtWidgets.QLabel("上方绕组到下方接线柱，可在此调整接线顺序。")
        set_props(caption, dialogCaption=True)
        layout.addWidget(caption)
        widget = GenWiringWidget(mapping, interactive=allow_repair)
        initial_order = widget.get_order()
        layout.addWidget(widget, alignment=QtCore.Qt.AlignHCenter)

    elif target == "PT1":
        dlg.setWindowTitle("PT1 接线箱检查")
        caption = QtWidgets.QLabel("PT1 一次侧与二次侧接线均可检查和调整。")
        set_props(caption, dialogCaption=True)
        layout.addWidget(caption)
        widget = PTWiringWidget(
            blackbox_state["pri_order"],
            blackbox_state["sec_order"],
            pri_input_order=blackbox_state["pri_input_order"],
            interactive_pri=allow_repair,
            interactive_sec=allow_repair,
        )
        initial_pri_order = widget.get_pri_order()
        initial_sec_order = widget.get_sec_order()
        layout.addWidget(widget, alignment=QtCore.Qt.AlignHCenter)

    elif target == "PT3":
        dlg.setWindowTitle("PT3 接线箱检查")
        caption = QtWidgets.QLabel("PT3 二次侧接线与极性可检查和调整；一次侧只读显示。")
        set_props(caption, dialogCaption=True)
        layout.addWidget(caption)
        widget = PTWiringWidget(
            blackbox_state["pri_order"],
            blackbox_state["sec_order"],
            pri_input_order=blackbox_state["pri_input_order"],
            sec_polarity=blackbox_state.get("sec_polarity"),
            interactive_sec=allow_repair,
            interactive_polarity=allow_repair,
            sec_ratio_secondary=blackbox_state.get("sec_ratio_secondary"),
            interactive_ratio=allow_repair,
            ratio_primary=blackbox_state.get("ratio_primary", 11000),
        )
        initial_pri_order = widget.get_pri_order()
        initial_sec_order = widget.get_sec_order()
        initial_sec_polarity = widget.get_sec_polarity()
        initial_sec_ratio_secondary = widget.get_sec_ratio_secondary()
        layout.addWidget(widget, alignment=QtCore.Qt.AlignHCenter)

    else:
        raise ValueError(f"Unsupported blackbox target: {target}")

    feedback = QtWidgets.QLabel("")
    feedback.setWordWrap(True)
    set_props(feedback, feedbackText=True, tone="neutral")
    feedback.setVisible(False)
    layout.addWidget(feedback)

    button_row = QtWidgets.QWidget()
    row = QtWidgets.QHBoxLayout(button_row)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)

    if repair_target is not None:
        def _on_confirm() -> None:
            new_order = widget.get_order() if repair_target in ("G1", "G2") else None
            new_pri = widget.get_pri_order() if repair_target in ("PT1", "PT3") else None
            new_sec = widget.get_sec_order() if repair_target in ("PT1", "PT3") else None
            new_sec_polarity = (
                widget.get_sec_polarity()
                if repair_target in ("PT1", "PT3") and hasattr(widget, "get_sec_polarity")
                else None
            )
            new_sec_ratio_secondary = (
                widget.get_sec_ratio_secondary()
                if repair_target == "PT3" and hasattr(widget, "get_sec_ratio_secondary")
                else initial_sec_ratio_secondary
            )
            outcome = api.apply_blackbox_repair_attempt(
                repair_target,
                step=step,
                initial_order=initial_order,
                new_order=new_order,
                initial_pri_order=initial_pri_order,
                new_pri_order=new_pri,
                initial_sec_order=initial_sec_order,
                new_sec_order=new_sec,
                initial_sec_polarity=initial_sec_polarity,
                new_sec_polarity=new_sec_polarity,
                new_sec_ratio_secondary=new_sec_ratio_secondary,
            )
            feedback.setText("接线已保存，请关闭黑盒后继续外部测量和操作。")
            set_props(feedback, feedbackText=True, tone="info")
            feedback.setVisible(True)

        btn_save = QtWidgets.QPushButton("保存接线")
        apply_button_tone(owner, btn_save, "success")
        btn_save.clicked.connect(_on_confirm)
        row.addWidget(btn_save, 1)

    btn_close = QtWidgets.QPushButton("关闭")
    apply_button_tone(owner, btn_close, "primary")
    btn_close.clicked.connect(dlg.accept)
    row.addWidget(btn_close)
    layout.addWidget(button_row)
    dlg.exec_()
