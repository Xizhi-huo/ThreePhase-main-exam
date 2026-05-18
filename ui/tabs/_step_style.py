def refresh_styles(*widgets):
    for widget in widgets:
        if widget is None:
            continue
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()


def set_props(widget, **props):
    for key, value in props.items():
        widget.setProperty(key, value)
    refresh_styles(widget)


def apply_button_tone(owner, button, tone="primary", *, hero=False, secondary=False, muted=False):
    if hasattr(owner, "_apply_button_tone"):
        owner._apply_button_tone(
            button,
            tone,
            hero=hero,
            secondary=secondary,
            muted=muted,
        )
        return

    for prop in ("secondary", "success", "warning", "danger", "muted", "hero"):
        button.setProperty(prop, False)
    if secondary:
        button.setProperty("secondary", True)
    elif tone in ("success", "warning", "danger"):
        button.setProperty(tone, True)
    elif muted:
        button.setProperty("muted", True)
    button.setProperty("hero", hero)
    refresh_styles(button)


def normalize_qt_color(color: str) -> str:
    color_map = {
        "gray": "#808080",
        "grey": "#808080",
        "green": "#008000",
        "red": "#cc0000",
        "orange": "#ff8800",
        "blue": "#0000cc",
        "black": "#000000",
        "white": "#ffffff",
        "k": "#000000",
    }
    return color_map.get((color or "").lower(), color or "#000000")
