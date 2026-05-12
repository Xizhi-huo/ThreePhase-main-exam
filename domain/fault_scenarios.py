"""
domain/fault_scenarios.py
故障场景元数据字典。

每个场景键值对应一个教学故障场景，包含：
  - title        : 显示名称
  - category     : 故障大类（I 接线 / II 运行 / III 数值 / IV 危险操作）
  - label        : 大类中文标签
  - description  : 故障原因说明（面向管理员/教师）
  - danger_level : 'recoverable'（可恢复）或 'accident'（事故级别）
  - params       : 故障注入参数（由控制器读取）

命名约定说明：
  - `pt1_pri_blackbox_order` 对应控制器运行态 `pt1_pri_blackbox_order`
  - `pt1_sec_blackbox_order` 对应控制器运行态 `pt1_sec_blackbox_order`
"""

from domain.constants import E04_PT3_RATIO


SCENARIOS: dict = {
    '': {
        'title': '正常场景（无故障）',
        'category': None,
        'label': '正常',
        'description': '标准流程，无任何故障注入。',
        'danger_level': 'recoverable',
        'params': {},
    },

    'E01': {
        'title': 'E01 — Gen1 A/B 相接线对调',
        'category': 'I',
        'label': '接线错误',
        'description': (
            'Gen1 机端 A 相与 B 相端子接线对调：A 端子接了 B 相绕组，B 端子接了 A 相绕组。'
            '导致 PT1 相序显示异常（ACB 逆序），第一步 AA/BB 回路断路，第四步压差矩阵异常。'
        ),
        'danger_level': 'recoverable',
        'params': {
            'pt1_phase_order': ['B', 'A', 'C'],   # PT1 端子 A→B相, B→A相, C→C相
            'g1_loop_swap': ('A', 'B'),             # G1 回路测试相序交换对
            'g1_blackbox_order': ['B', 'A', 'C'],   # 黑箱数据源，使学员可在 G1 黑盒还原 A/B 后清除故障
        },
    },

    'E02': {
        'title': 'E02 — Gen2 B/C 相接线对调',
        'category': 'I',
        'label': '接线错误',
        'description': (
            'Gen2 机端 B 相与 C 相端子接线对调：B 端子接了 C 相绕组，C 端子接了 B 相绕组。'
            '导致 PT3 相序逆序，第一步 BB/CC 回路断路，第四步压差矩阵异常。'
        ),
        'danger_level': 'recoverable',
        'params': {
            'pt3_phase_order': ['A', 'C', 'B'],   # PT3 端子 A→A相, B→C相, C→B相
            'g2_loop_swap': ('B', 'C'),             # G2 回路测试相序交换对
            'g2_blackbox_order': ['A', 'C', 'B'],   # G2 机端接线盒黑盒显示用
        },
    },

    'E03': {
        'title': 'E03 — PT3 A 相极性反接',
        'category': 'II',
        'label': '运行条件错误',
        'description': (
            'PT3 A 相二次端子极性反接（K/k 端子对调）：A 端子实际输出 −VA。'
            '第四步 PT3_A 行所有压差均异常：AA 组显示约 166V，AB/AC 组显示约 92V。'
            '第五步：同期装置以 PT3 A 相作为相角参考，极性反接导致参考角偏差 180°，'
            '自动同期收敛至错误相位；若强行并网将发生非同期合闸事故。'
        ),
        'danger_level': 'accident',
        'params': {
            'pt3_a_reversed': True,   # PT3 A 相二次侧极性反接
        },
    },

    'E04': {
        'title': 'E04 — PT3 变比铭牌参数错误',
        'category': 'III',
        'label': '数值异常',
        'description': (
            'PT3 实际硬件变比为 11000:93（= 118.28），正确额定值为 11000:193（= 56.99）。'
            '控制台按额定值录入 56.99，但物理测量以实际变比 118.28 计算，'
            '导致 PT3 二次线电压读数约 88.8V（额定约 184V），严重偏低，超出 ±15% 容差下限。'
        ),
        'danger_level': 'recoverable',
        'params': {
            'pt3_ratio': E04_PT3_RATIO,   # PT3 实际硬件变比（额定应为 11000:193 = 56.99）
        },
    },

    # ════════════════════════════════════════════════════════════════════════
    # Gen1/PT1 接线场景矩阵（E05–E14）
    # 信号链：Gen1 → [G节点] → Bus → [P1节点] → PT1一次侧 → [P2节点] → PT1二次侧
    # 反(同)  = 同对换位 A↔B；反(不同) = 混合换位（P1=A↔B, P2=B↔C 或 G=A↔B, Px=B↔C）
    # ════════════════════════════════════════════════════════════════════════

    'E05': {
        'title': 'E05 — 反反反(同) G=A↔B, PT1一次=A↔B, PT1二次=A↔B',
        'category': 'I',
        'label': '接线错误',
        'description': (
            'Gen1机端、PT1一次侧、PT1二次侧三处均为A/B相对调（奇数次相同换位）。\n'
            '净效果等同于一次A↔B对调：PT1二次A端子输出B相、B端子输出A相（ACB逆序）。\n'
            '步骤一暴露G节点反序；步骤四A端压差虚假为0V（两侧均为B相，数值相消），迷惑性强。'
        ),
        'danger_level': 'recoverable',
        'params': {
            'pt1_phase_order': ['B', 'A', 'C'],
            'g1_loop_swap': ('A', 'B'),

            'g1_blackbox_order': ['B', 'A', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保G1/PT1一致反序
            'pt1_pri_blackbox_order': ['B', 'A', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保P1/PT1一致反序
            'pt1_sec_blackbox_order': ['B', 'A', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保PT2/PT1一致反序
        },

    },

    'E06': {
        'title': 'E06 — 正反正 仅PT1一次侧A↔B接反',
        'category': 'I',
        'label': '接线错误',
        'description': (
            '仅PT1一次侧A/B相端子对调，Gen1机端与PT1二次侧均正常。\n'
            'Bus电压正常，PT1一次A端子接入B相、B端子接入A相，导致PT1二次输出ACB逆序。\n'
            '步骤一Gen1直测正常，学员可能放松警惕；步骤三、四联合指向PT1一次侧故障。'
        ),
        'danger_level': 'recoverable',
        'params': {
            'pt1_phase_order': ['B', 'A', 'C'],

            'pt1_pri_blackbox_order': ['B', 'A', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保P1/PT1一致反序
            'pt1_sec_blackbox_order': ['A', 'B', 'C'],   # 仅一次侧错接，二次侧保持正序
        },
    },

    'E07': {
        'title': 'E07 — 正正反 仅PT1二次侧A↔B接反',
        'category': 'I',
        'label': '接线错误',
        'description': (
            '仅PT1二次侧端子排A/B相对调，Gen1机端与PT1一次侧均正常。\n'
            'PT1内部变压正常，但二次侧接出时A/B端子接线互换，导致测量端呈ACB逆序。\n'
            '外部观测与E06（正反正）完全相同，区分需物理拆检PT1二次侧端子排。'
        ),
        'danger_level': 'recoverable',
        'params': {
            'pt1_phase_order': ['B', 'A', 'C'],

            'pt1_pri_blackbox_order': ['A', 'B', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保P1/PT1一致反序
            'pt1_sec_blackbox_order': ['B', 'A', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保PT2/PT1一致反序
        },
    },

    'E08': {
        'title': 'E08 — 正反反(同) PT1一次+二次同对A↔B（完全隐性）',
        'category': 'I',
        'label': '接线错误',
        'description': (
            'PT1一次侧与二次侧均为A/B相对调，Gen1机端正常。两次相同换位互相抵消，\n'
            '测量端净效果为ABC正序，四步全部通过——这是功能性"完全隐性错误"。\n'
            '只有物理拆检PT1端子排，或更换PT1后仅复接一侧才能暴露（变为E06或E07）。'
        ),
        'danger_level': 'recoverable',
        'params': {
            'pt1_phase_order': ['A', 'B', 'C'],   # 净效果正常，隐性错误

            'pt1_pri_blackbox_order': ['B', 'A', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保P1/PT1一致反序
            'pt1_sec_blackbox_order': ['B', 'A', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保PT2/PT1一致反序
        },
    },

    'E09': {
        'title': 'E09 — 反正反(同) Gen1+PT1二次同对A↔B',
        'category': 'I',
        'label': '接线错误',
        'description': (
            'Gen1机端A/B对调，PT1二次侧A/B对调，PT1一次侧正常。\n'
            'G与P2双反相消，PT1二次侧测量呈ABC正序（虚假正常）；\n'
            '但Bus本身因G反接为B相，而PT1二次A端子输出A相，步骤四暴露跨相位差。'
        ),
        'danger_level': 'recoverable',
        'params': {
            'pt1_phase_order': ['A', 'B', 'C'],   # 净效果正序，但Bus与PT不同相
            'g1_loop_swap': ('A', 'B'),

            'g1_blackbox_order': ['B', 'A', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保G1/PT1一致反序
            'pt1_pri_blackbox_order': ['A', 'B', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保P1/PT1一致反序
            'pt1_sec_blackbox_order': ['B', 'A', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保PT2/PT1一致反序
        },
    },

    'E10': {
        'title': 'E10 — 反反正(同) Gen1+PT1一次同对A↔B',
        'category': 'I',
        'label': '接线错误',
        'description': (
            'Gen1机端A/B对调，PT1一次侧A/B对调，PT1二次侧正常。\n'
            'G与P1双反相消，PT1二次侧测量呈ABC正序（虚假正常）；\n'
            '同E09，Bus为B相而PT1输出A相，步骤四暴露相位差。'
        ),
        'danger_level': 'recoverable',
        'params': {
            'pt1_phase_order': ['A', 'B', 'C'],   # 净效果正序，但Bus与PT不同相
            'g1_loop_swap': ('A', 'B'),
            'g1_blackbox_order': ['B', 'A', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保G1/PT1一致反序
            'pt1_pri_blackbox_order': ['B', 'A', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保P1/PT1一致反序
            'pt1_sec_blackbox_order': ['A', 'B', 'C'],   # 仅一次侧错接，二次侧保持正序

        },
    },

    'E11': {
        'title': 'E11 — 正反反(不同) PT1一次A↔B + 二次B↔C',
        'category': 'I',
        'label': '接线错误',
        'description': (
            'Gen1机端正常，PT1一次侧A/B对调，二次侧B/C对调。\n'
            '两个不同换位合成三轮换（A→B→C→A循环），测量端净相序为BCA——\n'
            '三相电压均存在120°相位平移，但旋转方向不变，相序仪仍显正序（虚假正常）。\n'
            '步骤四是唯一有效检测：同相端子对比全部暴露≈183V相位差。'
        ),
        'danger_level': 'recoverable',
        'params': {
            'pt1_phase_order': ['B', 'C', 'A'],   # BCA轮换，相序仪仍显正序

            'pt1_pri_blackbox_order': ['B', 'A', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保P1/PT1一致反序
            'pt1_sec_blackbox_order': ['A', 'C', 'B'],   # 黑箱数据源，覆盖pt1_phase_order，确保PT2/PT1一致反序
        },
    },

    'E12': {
        'title': 'E12 — 反正反(不同) Gen1 A↔B + PT1二次B↔C',
        'category': 'I',
        'label': '接线错误',
        'description': (
            'Gen1机端A/B对调，PT1二次侧B/C对调，PT1一次侧正常。\n'
            '测量端相序为CAB（正序轮换，步骤三虚假正常）。\n'
            '步骤四陷阱：A相核相Bus_A=B相与PT1_A=B相恰好吻合（0V），\n'
            '必须检查B相或C相才能发现120°相位偏差——揭示单相核相的盲区。'
        ),
        'danger_level': 'recoverable',
        'params': {
            'pt1_phase_order': ['B', 'C', 'A'],
            'g1_loop_swap': ('A', 'B'),

            'g1_blackbox_order': ['B', 'A', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保G1/PT1一致反序
            'pt1_pri_blackbox_order': ['A', 'B', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保P1/PT1一致反序
            'pt1_sec_blackbox_order': ['A', 'C', 'B'],   # 黑箱数据源，覆盖pt1_phase_order，确保PT2/PT1一致反序
        },
    },

    'E13': {
        'title': 'E13 — 反反正(不同) Gen1 A↔B + PT1一次B↔C',
        'category': 'I',
        'label': '接线错误',
        'description': (
            'Gen1机端A/B对调，PT1一次侧B/C对调，PT1二次侧正常。\n'
            '与E12外部现象完全相同（步骤三虚假正序，步骤四A端0V陷阱，B/C端183V）。\n'
            '区别在于错误位于PT1一次侧而非二次侧，需物理拆检定位。'
        ),
        'danger_level': 'recoverable',
        'params': {
            'pt1_phase_order': ['B', 'C', 'A'],
            'g1_loop_swap': ('A', 'B'),
            'g1_blackbox_order': ['B', 'A', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保G1/PT1一致反序
            'pt1_pri_blackbox_order': ['A', 'C', 'B'],   # 黑箱数据源，覆盖pt1_phase_order，确保P1/PT1一致反序
            'pt1_sec_blackbox_order': ['A', 'B', 'C'],
        },
    },

    'E14': {
        'title': 'E14 — 三级复合 Gen1 BAC × PT1一次 ACB × PT1二次 CAB（三错互消）',
        'category': 'I',
        'label': '接线错误',
        'description': (
            'Gen1机端BAC（A↔B），PT1一次侧ACB（B↔C），PT1二次侧CAB（三轮换A→C→B→A）。\n'
            '三处错误叠加净效果为ABC正序（完全相消）：步骤二/三/四/五全部正常。\n'
            '仅步骤一回路检查因Gen1机端A↔B对调暴露AA/BB断路，是唯一破绽。\n'
            '步骤四C相同相压差≈0V（陷阱），A/B相压差≈183V。'
        ),
        'danger_level': 'recoverable',
        'params': {
            'pt1_phase_order': ['A', 'B', 'C'],   # 净效果正序，三错相消
            'g1_loop_swap': ('A', 'B'),
            'g1_blackbox_order': ['B', 'A', 'C'],   # 黑箱数据源，覆盖pt1_phase_order，确保G1/PT1一致反序
            'pt1_pri_blackbox_order': ['A', 'C', 'B'],   # 黑箱数据源，覆盖pt1_phase_order，确保P1/PT1一致反序
            'pt1_sec_blackbox_order': ['C', 'A', 'B'],
            
        },
    },

    # ── 暂时禁用（开发中）────────────────────────────────────────────────────
}
