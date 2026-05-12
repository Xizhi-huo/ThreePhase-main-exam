# ThreePhase 三相电并网考核系统

这是从教学版项目拆分出来的独立考核版桌面程序，基于 PyQt5、Matplotlib 和 NumPy 实现三相发电机并母仿真、测量、故障注入、黑盒修复和最终并网判定。

当前版本定位为自由操作考核平台：学员不再按固定五步流程推进，也不再查看成绩单或评分明细。系统隐藏注入随机故障，学员自行测量、记录、检查黑盒并完成修复，最后通过普通 Gen2 合闸按钮尝试并入由 Gen1 建立的母排。考核结果只由这一次最终并母是否成功决定。

详细需求记录见 [EXAM_MODE_REQUIREMENTS.md](EXAM_MODE_REQUIREMENTS.md)。

## 快速开始

建议使用项目内已有虚拟环境运行：

```powershell
.\.venv\Scripts\python.exe app\main.py
```

如果需要重新安装依赖，基础依赖为：

```powershell
pip install PyQt5 matplotlib numpy
python app\main.py
```

基础编译检查：

```powershell
python -m compileall -q app domain services ui adapters
```

## 当前考核流程

```text
进入程序
→ 点击“开始随机考核”
→ 系统隐藏注入一个随机故障
→ 学员自由操作、测量、记录、查线和修复
→ 学员使用普通 Gen2 合闸按钮尝试并母
→ 系统根据 Gen2 本次并母结果判定通过或未通过
```

当前规则：

- 不显示原教学版五步步骤进度。
- 不要求学员选择最终故障场景。
- 不生成成绩单。
- 不显示过程评分和评分明细。
- 允许学员打开黑盒检查并修复。
- 测量记录只展示学员实际记录过的数据，不预置测点清单。
- Gen2 工作位第一次合闸尝试即视为最终提交，只允许一次。
- 最终是否通过由 Gen2 是否成功并入母排决定。

## 右侧自由操作台

右侧控制台保留考核需要的操作入口：

- 系统运行模式：当前只开放隔离母排模式。
- 考核启动：开始随机考核、显示当前考核状态。
- 自由操作台：记录当前测量、重置考核。
- 黑盒检查：G1、G2、PT1、PT3。
- 测量记录：折叠日志形式，默认不展开，记录后只显示实际记录内容。
- 中性点接地：断开、小电阻接地、直接接地。
- 万用表和发电机连线显示开关。
- Gen1 / Gen2 机组控制卡片。

已从考核版界面移除：

- “仲裁器：待命”显示。
- “闭合全局远程启动信号”开关。
- 旧远程启动自动仲裁控制入口。

## 测量记录

测量记录采用“折叠入口 + 日志”的形式，避免预设表格暴露考生需要测哪些点。

初始状态只显示：

```text
测量记录 0
```

当学员点击“记录当前测量”后，记录区自动展开，内容类似：

```text
#1  PT2_A - PT2_B  105.00 V
#2  G1_A - G2_A    通路 / 蜂鸣
```

记录区特点：

- 不显示正常、异常、合格、不合格等判定字样。
- 不显示标准答案或缺失测点。
- 不预置表格行和表头。
- 多条记录可滚动查看。
- 新增记录后自动定位到最新记录。
- 普通 UI 刷新不会重置用户手动滚动位置。

底层仍会保留必要判断，用于故障物理表现、保护动作、事故合闸和最终并母判定。

## 最终并母判定

最终动作定义为：

```text
Gen2 工作位合闸，并入由 Gen1 建立的母排。
```

通过条件收敛为：

```text
Gen1 处于工作位且断路器闭合
Gen2 处于工作位且断路器闭合
母排带电
母排来源为双机并联运行
未触发待处理事故场景
未因保护或非同期条件导致 Gen2 合闸失败
```

实现上由 `FreeExamService` 和 `HardwareActions` 协同完成：

- `HardwareActions.toggle_breaker()` 监听 Gen2 工作位第一次合闸。
- `FreeExamService.on_gen2_final_close_attempt()` 标记最终合闸已尝试。
- `FreeExamService.update_after_physics()` 在物理帧更新后判定通过或失败。
- 失败后不允许再次通过重新合闸补救。

## 物理与保护逻辑

核心物理帧入口为 `services/physics_engine.py`。

当前保留：

- 三相波形生成与历史缓存。
- 母排带电状态和母排基准计算。
- 发电机实际输出幅值爬升。
- 断路器合闸、分闸、保护和非同期判断。
- 机组间环流计算。
- PT 二次侧电压计算。
- 万用表测量逻辑。
- 中性点接地显示与零序相关状态。

已清理：

- 旧远程启动信号 `remote_start_signal`。
- 由远程启动驱动的自动起机、自动投死母线、自动同期捕获旧仲裁逻辑。
- 面向右侧 UI 的 `arb_msg / arb_color` 仲裁器状态输出。

注意：`services/_physics_arbitration.py` 仍保留母排基准计算，不能整体删除。它现在只负责判断母排来源、母排电压频率和参考机组。

## 黑盒检查与修复

考核版允许学员打开黑盒并修复，因为部分故障如果不修复，最终 Gen2 并母条件无法满足。

当前入口：

- `G1`：Gen1 机端接线。
- `G2`：Gen2 机端接线。
- `PT1`：Gen1 侧 PT 接线。
- `PT3`：Gen2 侧 PT 接线。

黑盒相关代码：

- `ui/dialogs/blackbox.py`
- `ui/widgets/gen_wiring_widget.py`
- `ui/widgets/pt_wiring_widget.py`
- `services/blackbox_repair_handler.py`
- `services/fault_manager.py`
- `domain/phase_order_state.py`

## 中性点接地与回路测量

右侧控制台保留中性点接地方式选择：

- 断开。
- 小电阻接地。
- 直接接地。

工程逻辑上，做通断或回路类测量前应断开中性点小电阻，避免通过中性点接地支路形成寄生回路，造成不该导通的测点蜂鸣或读数异常。

机组带电且小电阻接地投入时，小电阻属于接入带电系统的运行回路。三相平衡时其中性点电压和接地电流可能接近 0；不平衡、接地故障或零序电压出现时，小电阻会承受中性点电压并流过接地电流。

## 项目结构

```text
ThreePhase-main-exam/
├── app/
│   ├── main.py                  # 应用入口与 PowerSyncController
│   └── controller_signals.py
├── adapters/
│   └── render_state.py          # 物理层到 UI 的渲染快照
├── domain/
│   ├── models.py                # GeneratorState、SimulationState
│   ├── free_exam_state.py       # 自由考核状态
│   ├── fault_scenarios.py       # 随机故障场景
│   ├── phase_order_state.py     # 黑盒接线状态
│   ├── node_map.py              # 拓扑测点坐标
│   ├── enums.py
│   └── constants.py
├── services/
│   ├── physics_engine.py        # 物理引擎入口
│   ├── _physics_core.py         # 波形生成
│   ├── _physics_arbitration.py  # 母排基准计算
│   ├── _physics_protection.py   # 断路器、保护、环流
│   ├── _physics_measurement.py  # 接地、PT、万用表测量
│   ├── free_exam_service.py     # 最终考核判定
│   ├── hardware_actions.py      # 机组启停、合分闸、位置切换
│   ├── fault_manager.py
│   ├── blackbox_repair_handler.py
│   └── phase_order_resolver.py
├── ui/
│   ├── main_window.py
│   ├── panels/control_panel.py
│   ├── widgets/control_panel/
│   │   ├── run_controls.py      # 右侧自由操作台
│   │   ├── param_controls.py
│   │   └── generator_card.py
│   ├── tabs/waveform_tab.py
│   ├── tabs/circuit_tab/
│   ├── dialogs/blackbox.py
│   └── styles/
├── EXAM_MODE_REQUIREMENTS.md
├── ThreePhase.spec
└── README.md
```

## 主要代码入口

- 应用入口：[app/main.py](app/main.py)
- 自由考核状态：[domain/free_exam_state.py](domain/free_exam_state.py)
- 最终合闸判定：[services/free_exam_service.py](services/free_exam_service.py)
- 硬件操作：[services/hardware_actions.py](services/hardware_actions.py)
- 物理引擎：[services/physics_engine.py](services/physics_engine.py)
- 测量逻辑：[services/_physics_measurement.py](services/_physics_measurement.py)
- 保护与断路器逻辑：[services/_physics_protection.py](services/_physics_protection.py)
- 右侧操作台：[ui/widgets/control_panel/run_controls.py](ui/widgets/control_panel/run_controls.py)
- 母排拓扑：[ui/tabs/circuit_tab/_draw_topology.py](ui/tabs/circuit_tab/_draw_topology.py)

## 当前实现状态

已完成：

- 独立考核版项目结构。
- 自由操作台 UI。
- 隐藏随机故障启动。
- 黑盒检查与修复入口。
- Gen2 最终并母一次性判定。
- 测量记录从预设表格改为折叠日志。
- 右侧无效“仲裁器”和“全局远程启动信号”入口清理。
- 旧远程自动仲裁逻辑清理，保留母排基准计算。
- Gen2 合闸后禁止通过切换开关柜位置绕过最终判定。

后续可继续细化：

- 教师端是否需要查看隐藏故障编号。
- 失败后是否显示详细失败原因，还是只显示未通过。
- 测量记录是否需要导出。
- 是否记录完整操作日志。
- 是否加入考核超时机制。
- 回路测量时未断开小电阻的无效/危险测量表现是否需要进一步强化。