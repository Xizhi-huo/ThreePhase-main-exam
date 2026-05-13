"""
services/_physics_measurement.py
接地、PT 测量与万用表仿真 Mixin ── PhysicsEngine 的测量职责。
"""

import numpy as np

from domain.constants import NEUTRAL_RESISTOR_OHMS
from domain.enums import BreakerPosition
from domain.node_map import NODES

# 三相标准相位角：A=0°, B=-120°, C=+120°
_PHASE_ANGLES: dict = {'A': 0.0, 'B': -2 * np.pi / 3, 'C': 2 * np.pi / 3}


class MeasurementMixin:
    """中性点接地状态、PT 二次电压计算与万用表交互仿真。"""

    def _compute_intra_pt_voltage(self, pt_name: str, term1: str, term2: str,
                                  pt_line_v: float, sim) -> float:
        """
        计算同一 PT 内两端子间的实际线电压。

        通用相量差公式：V_ph = pt_line_v / √3，对每个端子：
          1. 通过 _resolve_terminal_actual_phase 得到实际物理相
          2. 查表得相位角（A=0°, B=-120°, C=+120°）
          3. 若该端子极性反接（E03: PT3 A 端子），相位角 +180°
          4. 返回 |V_ph·e^(jθ₁) − V_ph·e^(jθ₂)|

        正常三相不同相对间：√3·V_ph = pt_line_v（与原逻辑一致）。
        E03 PT3_AB/CA（含 A 端子）：V_ph = pt_line_v / √3（约低 42%）。
        """
        _SQRT3 = np.sqrt(3)
        gen_ph = pt_line_v / _SQRT3
        phase1 = self._resolve_terminal_actual_phase(pt_name, term1)
        phase2 = self._resolve_terminal_actual_phase(pt_name, term2)
        angle1 = _PHASE_ANGLES[phase1]
        angle2 = _PHASE_ANGLES[phase2]
        # 极性反接：E03 PT3 A 端子输出 −V，相位偏移 180°
        fc = sim.fault_config
        if (fc.active and not fc.repaired
                and fc.scenario_id == 'E03' and pt_name == 'PT3'
                and fc.params.get('pt3_a_reversed')):
            if term1 == 'A':
                angle1 += np.pi
            if term2 == 'A':
                angle2 += np.pi
        vx = gen_ph * np.cos(angle1) - gen_ph * np.cos(angle2)
        vy = gen_ph * np.sin(angle1) - gen_ph * np.sin(angle2)
        return float(np.sqrt(vx ** 2 + vy ** 2))

    def _whole_cycle_rms_raw(self, wave: np.ndarray, freq_hz: float,
                             n_cycles: int = 3) -> float:
        """整周期截断后的纯 RMS，不修改任何 EMA 状态。"""
        freq_hz = max(freq_hz, 1.0)
        spc = 1.0 / (freq_hz * self.wave_sample_dt)
        n_use = max(1, round(min(n_cycles, len(wave) / spc) * spc))
        n_use = min(n_use, len(wave))
        return float(np.sqrt(np.mean(wave[-n_use:] ** 2)))

    def _ema_update(self, key: str, raw_value: float) -> float:
        """
        对指定 key 独立维护 EMA，各测量路径互不串扰。
        key 示例: 'intra_diff', 'cross_rms1', 'cross_rms2'
        """
        if not hasattr(self, '_meter_ema_dict'):
            self._meter_ema_dict: dict = {}
        if key not in self._meter_ema_dict:
            self._meter_ema_dict[key] = raw_value
        else:
            a = self._meter_ema_alpha
            self._meter_ema_dict[key] = a * raw_value + (1.0 - a) * self._meter_ema_dict[key]
        return self._meter_ema_dict[key]

    def _ema_reset(self, *keys) -> None:
        """探针切换时清除指定 key 的历史，避免拖尾。"""
        if hasattr(self, '_meter_ema_dict'):
            for k in keys:
                self._meter_ema_dict.pop(k, None)

    def _update_grounding(self, sim) -> None:
        ga_data = self.plot_data['ga']
        gb_data = self.plot_data['gb']
        gc_data = self.plot_data['gc']
        v_sum_rms = np.sqrt(np.mean((ga_data + gb_data + gc_data) ** 2))

        if sim.grounding_mode == "断开":
            self.ground_msg = "N线: 悬浮脱开 (Vn = 漂移电位)"
            self.ground_color = "red"
        elif sim.grounding_mode == "直接接地":
            self.ground_msg = "N线: 直接接地 (Vn = 0V, 存在短路隐患)"
            self.ground_color = "orange"
        else:
            i0_rms = v_sum_rms / (3 * NEUTRAL_RESISTOR_OHMS + 0.001)
            vn_rms = i0_rms * NEUTRAL_RESISTOR_OHMS
            self.ground_msg = f"N线: 10Ω小电阻接地 (Vn={vn_rms:.1f}V)"
            self.ground_color = "green"

    def _resolve_terminal_actual_phase(self, pt_name: str, terminal: str) -> str:
        """将 PT 端子标签（A/B/C）解析为实际物理相（受 pt_phase_orders 与 fault_reverse_bc 影响）。"""
        if terminal not in ('A', 'B', 'C'):
            raise ValueError(f"Unsupported terminal label: {terminal}")
        idx = ('A', 'B', 'C').index(terminal)
        phase = self._get_pt_phase_orders()[pt_name][idx]
        # fault_reverse_bc 物理上对调 Gen2 B/C 绕组；
        # PT3 端子的实际相需跟随修正（PT1/PT2 不受影响）
        if self._sim_state.fault_reverse_bc and pt_name == 'PT3':
            if phase == 'B':
                phase = 'C'
            elif phase == 'C':
                phase = 'B'
        return phase
    
    def _update_pt_measurements(self, bus_a, a1, a2) -> None:
        # a1/a2/bus_a 均为线电压 RMS，直接除以变比得 PT 二次侧线电压
        sim = self._sim_state
        fc = sim.fault_config
        self.pt1_v = a1    / sim.pt_gen_ratio
        self.pt2_v = bus_a / sim.pt_bus_ratio
        # E04：PT3 使用故障变比（铭牌错误导致二次侧读数偏低/高）
        if fc.active and not fc.repaired and fc.scenario_id == 'E04':
            self.pt3_v = a2 / fc.params.get('pt3_ratio', sim.pt3_ratio)
        else:
            self.pt3_v = a2 / sim.pt3_ratio

    def _handle_loop_measurement(self, sim, n1, n2, info1, info2) -> None:
        self.meter_voltage = None
        self.meter_nodes = (n1, n2)

        if sim.gen1.running or sim.gen2.running:
            self.meter_status = "protect"
            self.meter_color = "black"
            self.meter_reading = "Err / 输入保护"
            return

        if sim.grounding_mode != "断开":
            self.meter_status = "ok"
            self.meter_color = "black"
            self.meter_reading = "≈0Ω / 蜂鸣"
            return

        loop_ready = (
            sim.gen1.breaker_position == BreakerPosition.TEST
            and sim.gen2.breaker_position == BreakerPosition.TEST
            and sim.gen1.breaker_closed
            and sim.gen2.breaker_closed
        )
        if not loop_ready:
            self.meter_status = "open"
            self.meter_color = "black"
            self.meter_reading = "OL / 无蜂鸣"
            return

        if info1[2] == info2[2]:
            self.meter_status = "not_connected"
            self.meter_color = "black"
            self.meter_reading = "----"
            return

        phase1 = self._phase_resolver.resolve_loop_node_phase(n1)
        phase2 = self._phase_resolver.resolve_loop_node_phase(n2)
        fc = sim.fault_config
        nominal_match = info1[3] == info2[3]
        actual_match = phase1 == phase2
        expected_result = nominal_match == actual_match
        point = f'{info1[3]}{info2[3]}'

        if actual_match:
            self.meter_status = "ok"
            self.meter_color = "black"
            self.meter_reading = "≈0Ω / 蜂鸣"
        else:
            self.meter_status = "open"
            self.meter_color = "black"
            self.meter_reading = "OL / 无蜂鸣"

        if (not expected_result
                and fc.active and not fc.repaired
                and (fc.scenario_id in ('E01', 'E02')
                     or fc.params.get('g1_loop_swap')
                     or fc.params.get('g2_loop_swap'))):
            self._mark_fault_detected(
                step=1,
                source='loop_measurement',
                target='loop',
                point=point,
            )

    def _handle_intra_pt_measurement(self, sim, n1, n2, info1, info2, pt_name, ph1, ph2) -> None:
        _sim_r = self._sim_state
        _pt_ratio = (_sim_r.pt_gen_ratio if pt_name == 'PT1'
                     else _sim_r.pt3_ratio if pt_name == 'PT3'
                     else _sim_r.pt_bus_ratio)
        if pt_name == 'PT1':
            _pt_line_v = self.pt1_v
        elif pt_name == 'PT3':
            _pt_line_v = self.pt3_v
        else:
            _pt_line_v = self.pt2_v

        meter_v = self._compute_intra_pt_voltage(pt_name, ph1, ph2, _pt_line_v, sim)
        self.meter_voltage = meter_v
        self.meter_nodes = (n1, n2)
        _fc_e04 = _sim_r.fault_config
        if (pt_name == 'PT3' and _fc_e04.active and not _fc_e04.repaired
                and _fc_e04.scenario_id == 'E04'):
            _pt_ratio = 11000.0 / 193.0

        _ok_lo = 8925.0 / _pt_ratio
        _ok_hi = 12075.0 / _pt_ratio
        if _ok_lo <= meter_v <= _ok_hi:
            self.meter_status = "ok"
            self.meter_color = "green"
        elif meter_v < 1.0:
            self.meter_status = "idle"
            self.meter_color = "black"
        else:
            self.meter_status = "danger"
            self.meter_color = "red"

        primary_display = meter_v * _pt_ratio
        fc = sim.fault_config
        if (fc.active and not fc.repaired
                and pt_name == 'PT3'
                and self.meter_status == 'danger'):
            if fc.scenario_id == 'E04':
                self._mark_fault_detected(
                    step=2,
                    source='pt_voltage_measurement',
                    target='PT3',
                    point=f'{ph1}{ph2}',
                )
            elif fc.scenario_id == 'E03' and 'A' in (ph1, ph2):
                self._mark_fault_detected(
                    step=2,
                    source='pt_voltage_measurement',
                    target='PT3',
                    point=f'{ph1}{ph2}',
                )

        self.meter_reading = (
            f"线电压: {info1[4]} ↔ {info2[4]} | "
            f"一次侧={primary_display/1000:.2f} kV"
            f"（二次侧={meter_v:.1f} V）"
        )

    def _handle_cross_pt_measurement(self, sim, n1, n2) -> None:
        gen_node = n1 if not n1.startswith('PT2_') else n2
        bus_node = n2 if not n1.startswith('PT2_') else n1
        gen_pt_name = gen_node.split('_')[0]
        gen_term = gen_node.split('_')[1]
        bus_phase = bus_node.split('_')[1]

        gen_phase_actual = self._resolve_terminal_actual_phase(gen_pt_name, gen_term)
        bus_phase_actual = self._resolve_terminal_actual_phase('PT2', bus_phase)
        sqrt3 = np.sqrt(3)
        gen_line = self.pt1_v if gen_pt_name == 'PT1' else self.pt3_v
        bus_line = self.pt2_v
        gen_ph = gen_line / sqrt3
        bus_ph = bus_line / sqrt3
        fc = sim.fault_config
        is_same_phase = (gen_phase_actual == bus_phase_actual)

        e03_active = (fc.active and not fc.repaired
                      and fc.scenario_id == 'E03'
                      and gen_pt_name == 'PT3' and gen_term == 'A')
        if e03_active:
            if bus_phase_actual == gen_phase_actual:
                meter_v = gen_ph + bus_ph
            else:
                meter_v = np.sqrt(max(0.0, gen_ph**2 + bus_ph**2 - gen_ph * bus_ph))
        elif is_same_phase:
            meter_v = abs(gen_ph - bus_ph)
        else:
            meter_v = np.sqrt(max(0.0, gen_ph**2 + bus_ph**2 + gen_ph * bus_ph))

        if fc.active and not fc.repaired:
            if e03_active:
                self._mark_fault_detected(
                    step=4,
                    source='pt_exam_measurement',
                    target=gen_pt_name,
                    point=f'{gen_term}-{bus_phase}',
                )
            elif fc.scenario_id == 'E04' and gen_pt_name == 'PT3' and is_same_phase:
                self._mark_fault_detected(
                    step=4,
                    source='pt_exam_measurement',
                    target=gen_pt_name,
                    point=f'{gen_term}-{bus_phase}',
                )
            elif (gen_pt_name == 'PT1'
                  and fc.params.get('pt1_phase_order') is not None
                  and not is_same_phase):
                self._mark_fault_detected(
                    step=4,
                    source='pt_exam_measurement',
                    target=gen_pt_name,
                    point=f'{gen_term}-{bus_phase}',
                )

        self.meter_phase_match = False if e03_active else is_same_phase
        self.meter_voltage = meter_v
        self.meter_nodes = (n1, n2)
        self.meter_color = "green"
        self.meter_status = "ok"
        self.meter_reading = (
            f"{gen_pt_name}_{gen_term} ↔ PT2_{bus_phase} | "
            f"机组相电压={gen_ph:.2f} V  母排相电压={bus_ph:.2f} V"
            f"  压差={meter_v:.2f} V"
        )

    def _update_multimeter(self, sim) -> None:
        ui_nodes = NODES

        self.meter_color = "black"
        self.meter_voltage = None
        self.meter_status = "idle"
        self.meter_nodes = None
        self.meter_phase_match = None

        cur_probes = (sim.probe1_node, sim.probe2_node)
        if not hasattr(self, '_meter_last_probes'):
            self._meter_last_probes = cur_probes
        if cur_probes != self._meter_last_probes:
            self._ema_reset('intra_diff', 'cross_rms1', 'cross_rms2')
            self._meter_last_probes = cur_probes

        if sim.multimeter_mode:
            n1, n2 = sim.probe1_node, sim.probe2_node
            if n1 and n2:
                if n1 not in ui_nodes or n2 not in ui_nodes:
                    self.meter_status = "invalid"
                    self.meter_color = "red"
                    self.meter_nodes = (n1, n2)
                    self.meter_reading = "----"
                    return
                self.meter_nodes = (n1, n2)
                info1, info2 = ui_nodes[n1], ui_nodes[n2]
                loop_pair = info1[2].startswith('Loop') and info2[2].startswith('Loop')
                valid_pairs = {
                    frozenset({f'PT{gn}_{gp}', f'PT2_{bp}'})
                    for gn in (1, 3) for gp in 'ABC' for bp in 'ABC'
                }
                pt1 = n1.rsplit('_', 1)[0] if '_' in n1 else ''
                pt2 = n2.rsplit('_', 1)[0] if '_' in n2 else ''
                ph1 = n1.rsplit('_', 1)[1] if '_' in n1 else ''
                ph2 = n2.rsplit('_', 1)[1] if '_' in n2 else ''
                intra_pt_pair = (
                    pt1 == pt2 and
                    pt1 in ('PT1', 'PT2', 'PT3') and
                    ph1 in ('A', 'B', 'C') and
                    ph2 in ('A', 'B', 'C') and
                    ph1 != ph2
                )
                if loop_pair:
                    self._handle_loop_measurement(sim, n1, n2, info1, info2)
                elif intra_pt_pair:
                    self._handle_intra_pt_measurement(sim, n1, n2, info1, info2, pt1, ph1, ph2)
                elif frozenset({n1, n2}) in valid_pairs:
                    self._handle_cross_pt_measurement(sim, n1, n2)
                else:
                    self.meter_status = "invalid"
                    self.meter_reading = "----"
            elif n1:
                if n1 in ui_nodes:
                    self.meter_status = "waiting"
                    self.meter_reading = "----"
                else:
                    self.meter_status = "invalid"
                    self.meter_color = "red"
                    self.meter_reading = "----"
            else:
                self.meter_status = "waiting"
                self.meter_reading = "----"
        else:
            sim.probe1_node = None
            sim.probe2_node = None
            self.meter_reading = "万用表未开启"
