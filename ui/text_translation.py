from __future__ import annotations

from typing import Any, Callable


TEXT_TRANSLATION = {
    "三相电并网考核系统": "Three-Phase Grid Synchronization Exam System",
    "实时波形与同期表": "Real-Time Waveforms and Synchronization Meter",
    "母排拓扑与环流监测": "Bus Topology and Circulating Current Monitor",
    "考核模式：自由操作台": "Exam Mode: Free Operation Console",
    "系统运行模式": "System Operating Mode",
    "隔离母排": "Isolated Bus",
    "考核启动": "Exam Start",
    "自由操作台": "Free Operation Console",
    "开始随机考核": "Start Random Exam",
    "重新开始随机考核": "Restart Random Exam",
    "未开始：点击随机故障开始考核。": "Not started: click random fault to start the exam.",
    "未开始：等待随机故障启动。": "Not started: waiting for a random fault.",
    "考核进行中：随机故障已隐藏注入。": "Exam in progress: a hidden random fault has been injected.",
    "已提交最终合闸，正在根据母排并入状态判定。": (
        "Final close submitted. Evaluating the bus synchronization state."
    ),
    "通过：Gen2 已成功并入母排。": "Passed: Gen2 has been synchronized to the bus.",
    "未通过：最终 Gen2 并母未成功。": "Failed: final Gen2 bus synchronization did not succeed.",
    "未通过：考核条件未满足": "Failed: exam conditions were not met.",
    "Gen2 未能成功合闸并入母排": "Gen2 failed to close and synchronize to the bus.",
    "Gen2 合闸后未形成双机并母运行": "Gen2 closed, but dual-generator bus operation was not established.",
    "Gen2 最终并母状态未满足通过条件": "The final Gen2 bus state did not meet the pass conditions.",
    "发电机": "Generator",
    "母排": "Bus",
    "母线": "Bus",
    "断路器": "Circuit Breaker",
    "脱开位置": "Disconnected Position",
    "试验位置": "Test Position",
    "工作位置": "Working Position",
    "停机": "Stopped",
    "停止": "Stopped",
    "手动": "Manual",
    "自动": "Automatic",
    "启动": "Start",
    "合闸": "Close Breaker",
    "分闸": "Open Breaker",
    "万用表": "Multimeter",
    "相序仪": "Phase Sequence Meter",
    "表笔": "Probe",
    "电压": "Voltage",
    "频率": "Frequency",
    "相角": "Phase Angle",
    "相序": "Phase Sequence",
    "正序": "Positive Sequence",
    "反序": "Negative Sequence",
    "逆序": "Reverse Sequence",
    "一次侧": "Primary Side",
    "二次侧": "Secondary Side",
    "倍率": "Ratio",
    "中性点接地": "Neutral Grounding",
    "中性点接地（三相四线 N 线）": "Neutral Grounding (Three-Phase Four-Wire N Line)",
    "断开": "Open",
    "小电阻(10Ω)": "Small Resistance (10Ω)",
    "小电阻接地": "Small-Resistance Grounding",
    "直接接地": "Solid Grounding",
    "黑盒": "Black Box",
    "黑盒检查": "Black Box Inspection",
    "保存接线": "Save Wiring",
    "关闭": "Close",
    "重置": "Reset",
    "运行控制": "Run Control",
    "参数设置": "Parameter Settings",
    "记录当前测量": "Record Current Measurement",
    "分类看板": "Category Board",
    "测量数据分类看板": "Measurement Data Category Board",
    "测量记录 0": "Measurement Records 0",
    "展开或收起已记录的测量数据": "Expand or collapse recorded measurement data",
    "打开已记录测量数据的分类看板": "Open the category board for recorded measurements",
    "拿取万用表": "Pick Up Multimeter",
    "拿取相序仪": "Pick Up Phase Sequence Meter",
    "显示发电机与母排之间的连线": "Show generator-to-bus wiring",
    "PT 变比": "PT Ratio",
    "全部": "All",
    "其他": "Other",
    "其他测量": "Other Measurements",
    "通断": "Continuity",
    "回路": "Loop",
    "回路测量": "Loop Measurement",
    "PT电压": "PT Voltage",
    "PT压差": "PT Voltage Difference",
    "相序测量": "Phase Sequence Measurement",
    "压差": "Voltage Difference",
    "频差": "Frequency Difference",
    "相角差": "Phase Angle Difference",
    "运行模式": "Operating Mode",
    "机组状态": "Generator State",
    "同期参数": "Synchronization Parameters",
    "同期参数面板": "Synchronization Parameter Panel",
    "同期参数范围": "Synchronization Parameter Range",
    "参考源": "Reference Source",
    "母线状态": "Bus Status",
    "母线总览": "Bus Overview",
    "相量图": "Phasor Diagram",
    "三相实时波形": "Real-Time Three-Phase Waveforms",
    "实时显示频差、压差、相角差与波形状态。": (
        "Displays frequency difference, voltage difference, phase angle difference, and waveform status in real time."
    ),
    "观察母线、Gen1、Gen2 三组波形是否持续收敛。": (
        "Observe whether the bus, Gen1, and Gen2 waveforms continue to converge."
    ),
    "仅保留母线三相总览，作为次级趋势信息。": (
        "Shows only the bus three-phase overview as secondary trend information."
    ),
    "独立相量图只负责展示相位关系。": "The standalone phasor diagram shows phase relationships only.",
    "未开始监视": "Monitoring Not Started",
    "显示频差、压差和相角差。": "Displays frequency, voltage, and phase angle differences.",
    "电压 (V)": "Voltage (V)",
    "窗口角度 (°)": "Window Angle (°)",
    "相对参考频率": "Relative Reference Frequency",
    "相对参考电压": "Relative Reference Voltage",
    "相对参考相角": "Relative Reference Phase Angle",
    "当前机组方式": "Current Generator Mode",
    "当前无母排参考": "No current bus reference",
    "当前无母排参考。": "No current bus reference.",
    "无参考源": "No Reference Source",
    "母排未带电，Δf / ΔV / Δθ 暂不计算。": (
        "The bus is de-energized; Δf / ΔV / Δθ are not calculated."
    ),
    "母排未带电，按额定值显示参考差值。": (
        "The bus is de-energized; reference differences are shown against rated values."
    ),
    "待评估": "Pending",
    "范围内": "In Range",
    "邻近": "Near",
    "范围外": "Out of Range",
    "Gen2 停止": "Gen2 Stopped",
    "Gen2 当前未输出运行参数。": "Gen2 is not currently outputting operating parameters.",
    "无母排参考": "No Bus Reference",
    "母排未带电": "Bus De-Energized",
    "母线未带电": "Bus De-Energized",
    "母线带电": "Bus Energized",
    "同期窗口内": "Within Synchronization Window",
    "接近同期窗口": "Near Synchronization Window",
    "同期窗口外": "Outside Synchronization Window",
    "频差、压差和相角差位于同期窗口。": (
        "Frequency, voltage, and phase angle differences are within the synchronization window."
    ),
    "频差、压差和相角差接近同期窗口。": (
        "Frequency, voltage, and phase angle differences are near the synchronization window."
    ),
    "频差、压差或相角差位于同期窗口外。": (
        "Frequency, voltage, or phase angle difference is outside the synchronization window."
    ),
    "A 相": "Phase A",
    "B 相": "Phase B",
    "C 相": "Phase C",
    "PCC模式:": "PCC Mode:",
    "开关柜:": "Switchgear:",
    "频率(Hz)": "Frequency (Hz)",
    "幅值(V)": "Amplitude (V)",
    "相位(°)": "Phase (°)",
    "停机(0)": "Stopped (0)",
    "脱开": "Disconnected",
    "试验": "Test",
    "工作": "Working",
    "断路器: OPEN": "Circuit Breaker: OPEN",
    "起机 (Start)": "Start Engine",
    "停机 (Stop)": "Stop Engine",
    "控合 (Close)": "Close Breaker",
    "控分 (Open)": "Open Breaker",
    "⏱️ 仿真全局时间流速": "⏱️ Global Simulation Time Speed",
    "速度: ": "Speed: ",
    "相量图：绝对参考系 (电网旋转)": "Phasor Diagram: Absolute Reference Frame (Grid Rotation)",
    "🛡️ 继电保护系统: 监控中 (阈值 ": "🛡️ Relay Protection System: Monitoring (Threshold ",
    "⏸ 暂停波形动画": "⏸ Pause Waveform Animation",
    "恢复波形动画时间": "Resume Waveform Animation Time",
    "暂停波形动画时间": "Pause Waveform Animation Time",
    "恢复物理时空": "Resume Physics Time",
    "暂停整个物理空间": "Pause Entire Physics Space",
    "未选择 PT": "No PT Selected",
    "未选择测点": "No Measurement Point Selected",
    "未选测点": "No Point Selected",
    "暂无通断记录。": "No continuity records.",
    "暂无 PT 电压记录。": "No PT voltage records.",
    "暂无核相压差记录。": "No phase-check voltage-difference records.",
    "暂无相序记录。": "No phase-sequence records.",
    "G1 ↔ G2 通断": "G1 ↔ G2 Continuity",
    "PT1 接线箱检查": "PT1 Wiring Box Inspection",
    "PT2 接线箱检查": "PT2 Wiring Box Inspection",
    "PT3 接线箱检查": "PT3 Wiring Box Inspection",
    "PT1 一次侧与二次侧接线均可检查和调整。": (
        "PT1 primary and secondary wiring can be inspected and adjusted."
    ),
    "PT2 二次侧接线可检查和调整；一次侧只读显示。": (
        "PT2 secondary wiring can be inspected and adjusted; primary wiring is read-only."
    ),
    "PT3 二次侧接线与极性可检查和调整；一次侧只读显示。": (
        "PT3 secondary wiring and polarity can be inspected and adjusted; primary wiring is read-only."
    ),
    "上方绕组到下方接线柱，可在此调整接线顺序。": (
        "The upper winding connects to the lower terminals; adjust the wiring order here."
    ),
    "接线已保存。": "Wiring saved.",
    "接线已保存，请关闭黑盒后继续外部测量和操作。": (
        "Wiring saved. Close the black box and continue external measurement and operation."
    ),
    "发电机 ": "Generator ",
    " 机端接线检查": " Terminal Wiring Inspection",
    "⚡  变压器铁芯（黑盒）": "⚡  Transformer Core (Black Box)",
    "── 二次侧测量端口 ──": "── Secondary Measurement Ports ──",
    "── 一次侧输入电缆 ──": "── Primary Input Cable ──",
    "── 内闭绕组 ──": "── Internal Windings ──",
    "── 输出接线柱 ──": "── Output Terminals ──",
    "实际输出: ": "Actual Output: ",
    "    极性: ": "    Polarity: ",
    "一次侧结果: ": "Primary Result: ",
    "实际来相: ": "Actual Incoming Phase: ",
    "相序仪\n顺时针=正序  逆时针=反序": (
        "Phase Sequence Meter\nClockwise=Positive  Counterclockwise=Negative"
    ),
    "正序 ↻": "Positive ↻",
    "反序 ↺": "Negative ↺",
    "未接入": "Not Connected",
    "待接线 ": "Waiting for wiring ",
    "接待线 0/3": "Wired 0/3",
    "未接": "Not Connected",
    "Dead Bus (无电)": "Dead Bus (De-Energized)",
    "二次端子排": "Secondary Terminal Block",
    "机端": "Generator Terminal",
    "三相回路连通测点": "Three-Phase Loop Continuity Points",
    "N线: 未接地": "N Line: Ungrounded",
    "机组间无环流": "No Circulating Current Between Generators",
    "万用表未开启": "Multimeter Not Enabled",
    "N线: 悬浮脱开 (Vn = 漂移电位)": "N Line: Floating Open (Vn = drifting potential)",
    "N线: 直接接地 (Vn = 0V, 存在短路隐患)": (
        "N Line: Solidly Grounded (Vn = 0V, short-circuit risk)"
    ),
    "N线: 10Ω小电阻接地 (Vn=": "N Line: 10Ω Resistance Grounding (Vn=",
    "Err / 输入保护": "Err / Input Protection",
    "≈0Ω / 蜂鸣": "≈0Ω / Beep",
    "OL / 无蜂鸣": "OL / No Beep",
    "线电压: ": "Line Voltage: ",
    " | 一次侧=": " | Primary=",
    " kV（二次侧=": " kV (Secondary=",
    " | 机组相电压=": " | Generator Phase Voltage=",
    " V  母排相电压=": " V  Bus Phase Voltage=",
    " V  压差=": " V  Voltage Difference=",
    "参考基准: Gen 1": "Reference: Gen 1",
    "参考基准: Gen 2": "Reference: Gen 2",
    "参考基准: Gen1": "Reference: Gen1",
    "参考基准: Gen2": "Reference: Gen2",
    "参考基准: 无": "Reference: None",
    "参考基准: 母排": "Reference: Bus",
    "参考基准: 额定值": "Reference: Rated Value",
    "参考基准：无": "Reference: None",
    "参考基准: ": "Reference: ",
    "母排: 无电": "Bus: De-Energized",
    "母排: 无电 (死母线)": "Bus: De-Energized (Dead Bus)",
    "母排: Gen 1 独立供电 (": "Bus: Gen 1 Supplying Independently (",
    "母排: Gen 2 独立供电 (": "Bus: Gen 2 Supplying Independently (",
    "母排: 以 Gen 1 为基准并联运行 (": "Bus: Parallel Operation Referenced to Gen 1 (",
    "母排: 以 Gen 2 为基准并联运行 (": "Bus: Parallel Operation Referenced to Gen 2 (",
    "母排：无电": "Bus: De-Energized",
    "🛡️ 继电保护监控中 (跳闸阈值: 一次侧 ": "🛡️ Relay Protection Monitoring (Trip Threshold: Primary ",
    "A / CT二次侧 ": "A / CT Secondary ",
    "⚠️ 保护: Gen 1 引擎停机失压，断路器自动脱扣！": (
        "⚠️ Protection: Gen 1 engine stopped and lost voltage; breaker tripped automatically."
    ),
    "⚠️ 保护: Gen 2 引擎停机失压，断路器自动脱扣！": (
        "⚠️ Protection: Gen 2 engine stopped and lost voltage; breaker tripped automatically."
    ),
    "⚠️ 警告：Gen2 B/C相序接反！合闸后产生短路电流！（模拟中无保护器，实际系统将立即跳闸）": (
        "⚠️ Warning: Gen2 B/C phase sequence is reversed. Closing creates short-circuit current."
    ),
    "💥 保护: Gen 1 环流过大，跳闸！": "💥 Protection: Gen 1 circulating current too high; tripped.",
    "💥 保护: Gen 2 环流过大，跳闸！": "💥 Protection: Gen 2 circulating current too high; tripped.",
    "机组环流: Gen1 ": "Circulating Current: Gen1 ",
    " Gen2 | CT二次: ": " Gen2 | CT Secondary: ",
    "机组间未形成直接环流回路": "No direct circulating-current loop formed between generators",
    ">>> 有功 >>>": ">>> Active Power >>>",
    "<<< 有功 <<<": "<<< Active Power <<<",
    ">>> 无功 >>>": ">>> Reactive Power >>>",
    "<<< 无功 <<<": "<<< Reactive Power <<<",
    "<-> 平衡 <->": "<-> Balanced <->",
    "非同期合闸爆炸！频差:": "Out-of-sync close fault. Frequency difference:",
    "Hz, 压差:": "Hz, voltage difference:",
    "V, 角差:": "V, phase angle difference:",
    "断路器: 炸毁": "Circuit Breaker: Damaged",
    "一次侧: 并网运行 (工作位)": "Primary: Grid-Synchronized Operation (Working Position)",
    "二次侧: 模拟闭合 (试验位)": "Secondary: Simulated Closed (Test Position)",
    "无效: 触头闭合 (脱开位)": "Invalid: Contact Closed (Disconnected Position)",
    ": 同期窗口内": ": Within Synchronization Window",
    "断路器: OPEN (": "Circuit Breaker: OPEN (",
    "操作闭锁": "Operation Interlock",
    "位置闭锁": "Position Interlock",
    "合闸闭锁": "Close Interlock",
    "考核已结束": "Exam Ended",
    "当前操作未被执行。": "The current operation was not executed.",
    "断路器位置未改变。": "Breaker position was not changed.",
    "断路器未动作。": "Breaker did not operate.",
    "尚未开始考核": "Exam Not Started",
    "当前未处于考核进行状态。": "The exam is not currently in progress.",
    "一次侧带电接触": "Energized Primary Contact",
    "万用表绝缘击穿": "Multimeter Insulation Breakdown",
    "普通表笔接触带电一次侧，高压击穿表笔绝缘并损坏仪表。": (
        "A standard probe touched the energized primary side; high voltage punctured the probe insulation and damaged the meter."
    ),
    "小伙汁，万用表替你扛了一下，但现场它不一定扛得住。": (
        "The multimeter absorbed this one in simulation; in the field it may not survive."
    ),
    "弧光闪络": "Arc Flashover",
    "一次侧高压点发生弧光闪络，柜内保护动作，操作中止。": (
        "An arc flashover occurred at the primary high-voltage point; cabinet protection operated and the task stopped."
    ),
    "小伙汁，这一下在屏幕里只是弹窗，现场就是弧光和冲击波了。": (
        "On screen this is only a dialog; in the field it means arc flash and blast pressure."
    ),
    "相间短路": "Phase-to-Phase Short Circuit",
    "表笔跨越高压相间距离，引发相间短路和开关柜跳闸。": (
        "The probe bridged high-voltage phases, causing a phase-to-phase short circuit and switchgear trip."
    ),
    "小伙汁，三相不是这么“握手”的，现场这一碰可能直接炸柜。": (
        "Three phases do not connect this way; in the field this contact can destroy the cabinet."
    ),
    "对地放电": "Discharge to Ground",
    "高压侧经表笔形成对地放电路径，接地保护动作。": (
        "The high-voltage side formed a discharge path to ground through the probe, triggering ground protection."
    ),
    "小伙汁，电流已经给自己找路了，现场你可能也在路上。": (
        "The current has found a path; in the field you may become part of it."
    ),
    "表笔熔毁": "Probe Melted",
    "测试线绝缘和金属端部过热熔毁，仪表端口损坏。": (
        "The test lead insulation and metal tip overheated and melted, damaging the meter port."
    ),
    "小伙汁，表笔先融了算你运气好，现场下一步可能就轮到人了。": (
        "If only the probe melts first, that is luck; in the field the next failure may involve the operator."
    ),
    "人身触电风险": "Electric Shock Risk",
    "带电一次侧接触形成严重人身触电风险，安全闭锁动作。": (
        "Contact with the energized primary side creates severe electric-shock risk; safety interlock operated."
    ),
    "小伙汁，在这里我能救你一命，现场就没这么好运了。": (
        "The simulator can save you here; the field may not be so forgiving."
    ),
    "风险：": "Risk:",
    "后果：": "Consequence:",
    "本次考核终止。": "This exam attempt has been terminated.",
    "我知道了": "Acknowledged",
    "访问验证": "Access Verification",
    "请输入访问密码：": "Enter access password:",
    "密码错误": "Incorrect Password",
    "密码错误，还可重试 ": "Incorrect password. Attempts remaining: ",
    " 次。": ".",
    "验证失败": "Verification Failed",
    "密码错误次数过多，程序退出。": "Too many incorrect password attempts. The program will exit.",
    "物理帧更新连续失败 ": "Physics frame update failed consecutively ",
    " 次（阶段: ": " times (stage: ",
    "），控制台错误日志包含详细信息。": "); see console error logs for details.",
    "物理引擎已熔断停止（阶段: ": "Physics engine stopped by circuit breaker (stage: ",
    "，连续失败 ": ", consecutive failures ",
    " 次）。": ").",
}


TEXT_REPLACEMENTS = (
    ("🛡️ 继电保护系统: 监控中 (阈值 ", "🛡️ Relay Protection System: Monitoring (Threshold "),
    ("速度: ", "Speed: "),
    ("参考基准：", "Reference: "),
    ("参考基准:", "Reference:"),
    ("同期参数：", "Synchronization Parameters: "),
    ("同期参数:", "Synchronization Parameters:"),
    ("测量记录 ", "Measurement Records "),
    ("N线: 10Ω小电阻接地 (Vn=", "N Line: 10Ω Resistance Grounding (Vn="),
    ("N线", "N Line"),
    ("小电阻接地", "Resistance Grounding"),
    ("全部", "All"),
    ("虚线", "Dashed Line"),
    ("点划线", "Dash-Dot Line"),
    (" 电压", " Voltage"),
    (" ↔ PT2 压差", " ↔ PT2 Voltage Difference"),
    (" 相序：----", " Phase Sequence: ----"),
    (" 相序：", " Phase Sequence: "),
    (" 相序仪接线未完成：已接 ", "Phase sequence meter wiring incomplete: connected "),
    ("线电压", "Line Voltage"),
    ("一次侧", "Primary"),
    ("二次侧", "Secondary"),
    ("母排", "Bus"),
    ("母线", "Bus"),
    ("发电机", "Generator"),
    ("断路器", "Circuit Breaker"),
    ("机组", "Generator"),
    ("相序仪", "Phase Sequence Meter"),
    ("万用表", "Multimeter"),
    ("相序", "Phase Sequence"),
    ("正序", "Positive Sequence"),
    ("反序", "Negative Sequence"),
    ("逆序", "Reverse Sequence"),
    ("停机", "Stopped"),
    ("停止", "Stopped"),
    ("手动", "Manual"),
    ("自动", "Automatic"),
    ("通断", "Continuity"),
    ("压差", "Voltage Difference"),
    ("频差", "Frequency Difference"),
    ("相角差", "Phase Angle Difference"),
    ("相角", "Phase Angle"),
    ("频率", "Frequency"),
    ("电压", "Voltage"),
    ("未选择", "No "),
    ("未选", "No "),
    ("未接入", "Not Connected"),
    ("未接", "Not Connected"),
    ("无电", "De-Energized"),
    ("带电", "Energized"),
    ("无参考源", "No Reference Source"),
    ("额定值", "Rated Value"),
    ("通过", "Passed"),
    ("未通过", "Failed"),
    ("范围内", "In Range"),
    ("范围外", "Out of Range"),
    ("邻近", "Near"),
    ("待评估", "Pending"),
    ("当前", "Current"),
    ("已接", "connected "),
    ("次。", "."),
    ("次", "times"),
    ("：", ": "),
    ("；", "; "),
    ("，", ", "),
    ("。", "."),
    ("（", " ("),
    ("）", ")"),
)


_INSTALLED = False


def translate_text(text: str) -> str:
    if not isinstance(text, str) or not text:
        return text
    translated = TEXT_TRANSLATION.get(text)
    if translated is not None:
        return translated
    if not any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return text
    translated = text
    for source, target in TEXT_REPLACEMENTS:
        translated = translated.replace(source, target)
    return translated


def _translate_value(value: Any) -> Any:
    return translate_text(value) if isinstance(value, str) else value


def _patch_method(cls: type, name: str, translator: Callable[[tuple, dict], tuple[tuple, dict]]) -> None:
    original = getattr(cls, name, None)
    if original is None or getattr(original, "_text_translation_patched", False):
        return

    def patched(self, *args, **kwargs):
        new_args, new_kwargs = translator(args, kwargs)
        return original(self, *new_args, **new_kwargs)

    patched._text_translation_patched = True
    setattr(cls, name, patched)


def _translate_all_strings(args: tuple, kwargs: dict) -> tuple[tuple, dict]:
    return tuple(_translate_value(arg) for arg in args), {
        key: _translate_value(value) for key, value in kwargs.items()
    }


def _translate_first_string(args: tuple, kwargs: dict) -> tuple[tuple, dict]:
    args = list(args)
    if args and isinstance(args[0], str):
        args[0] = translate_text(args[0])
    for key in ("text", "title"):
        if isinstance(kwargs.get(key), str):
            kwargs[key] = translate_text(kwargs[key])
    return tuple(args), kwargs


def _translate_header_labels(args: tuple, kwargs: dict) -> tuple[tuple, dict]:
    args = list(args)
    if args and isinstance(args[0], (list, tuple)):
        args[0] = [translate_text(value) if isinstance(value, str) else value for value in args[0]]
    return tuple(args), kwargs


def _patch_qt() -> None:
    try:
        from PyQt5 import QtGui, QtWidgets
    except Exception:
        return

    for cls in (
        QtWidgets.QLabel,
        QtWidgets.QPushButton,
        QtWidgets.QToolButton,
        QtWidgets.QRadioButton,
        QtWidgets.QCheckBox,
        QtWidgets.QGroupBox,
        QtWidgets.QAction,
        QtWidgets.QTableWidgetItem,
    ):
        _patch_method(cls, "__init__", _translate_first_string)

    for cls, methods in (
        (QtWidgets.QWidget, ("setWindowTitle", "setToolTip", "setStatusTip", "setWhatsThis")),
        (QtWidgets.QLabel, ("setText",)),
        (QtWidgets.QAbstractButton, ("setText",)),
        (QtWidgets.QGroupBox, ("setTitle",)),
        (QtWidgets.QStatusBar, ("showMessage",)),
        (QtWidgets.QMessageBox, ("setText", "setInformativeText", "setDetailedText", "setWindowTitle")),
        (QtWidgets.QComboBox, ("addItem",)),
        (QtWidgets.QMenu, ("addAction",)),
    ):
        for method in methods:
            _patch_method(cls, method, _translate_all_strings)

    _patch_method(QtWidgets.QComboBox, "addItems", _translate_header_labels)
    _patch_method(QtWidgets.QTableWidget, "setHorizontalHeaderLabels", _translate_header_labels)
    _patch_method(QtWidgets.QTableWidget, "setVerticalHeaderLabels", _translate_header_labels)
    _patch_method(QtWidgets.QTabWidget, "addTab", _translate_all_strings)

    for method in ("information", "warning", "critical", "question"):
        _patch_method(QtWidgets.QMessageBox, method, _translate_all_strings)

    _patch_method(QtGui.QPainter, "drawText", _translate_all_strings)


def _patch_matplotlib() -> None:
    try:
        from matplotlib.axes import Axes
        from matplotlib.text import Text
    except Exception:
        return

    for method in ("text", "set_title", "set_xlabel", "set_ylabel"):
        _patch_method(Axes, method, _translate_all_strings)
    _patch_method(Text, "set_text", _translate_all_strings)


def install_text_translation() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True
    _patch_qt()
    _patch_matplotlib()
