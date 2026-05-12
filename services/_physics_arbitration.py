"""
services/_physics_arbitration.py
Bus reference resolution for the standalone exam console.

The old remote-start arbitrator has been removed. In the exam build the student
operates the engine and breaker controls manually; breaker/protection logic then
decides whether the final Gen2 close succeeds.
"""

import numpy as np

from domain.constants import GRID_AMP, GRID_FREQ
from domain.enums import BreakerPosition


class ArbitrationMixin:
    """Resolve the live bus source and reference values used by physics logic."""

    def _resolve_bus_reference_gen(self, g1_on_bus, g2_on_bus) -> int | None:
        if not g1_on_bus and not g2_on_bus:
            self.bus_reference_gen = None
        elif self.bus_reference_gen == 1 and g1_on_bus:
            pass
        elif self.bus_reference_gen == 2 and g2_on_bus:
            pass
        elif g1_on_bus:
            self.bus_reference_gen = 1
        elif g2_on_bus:
            self.bus_reference_gen = 2
        return self.bus_reference_gen

    def _update_bus_reference(self, sim, is_isolated) -> dict[str, object]:
        g1_on_bus = (sim.gen1.breaker_position == BreakerPosition.WORKING) and sim.gen1.breaker_closed
        g2_on_bus = (sim.gen2.breaker_position == BreakerPosition.WORKING) and sim.gen2.breaker_closed

        if is_isolated:
            reference_gen = self._resolve_bus_reference_gen(g1_on_bus, g2_on_bus)
            if reference_gen == 1 and g1_on_bus:
                self.bus_freq = sim.gen1.freq
                self.bus_amp = sim.gen1.actual_amp
                self.bus_phase = np.radians(sim.gen1.phase_deg)
                self.bus_source = 1 if not g2_on_bus else "both"
                self.bus_live = True
                self.bus_reference_msg = "参考基准: Gen 1"
                if g2_on_bus:
                    self.bus_status_msg = f"母排: 以 Gen 1 为基准并联运行 ({self.bus_freq:.1f}Hz, {self.bus_amp:.0f}V)"
                else:
                    self.bus_status_msg = f"母排: Gen 1 独立供电 ({self.bus_freq:.1f}Hz, {self.bus_amp:.0f}V)"
            elif reference_gen == 2 and g2_on_bus:
                self.bus_freq = sim.gen2.freq
                self.bus_amp = sim.gen2.actual_amp
                self.bus_phase = np.radians(sim.gen2.phase_deg)
                self.bus_source = 2 if not g1_on_bus else "both"
                self.bus_live = True
                self.bus_reference_msg = "参考基准: Gen 2"
                if g1_on_bus:
                    self.bus_status_msg = f"母排: 以 Gen 2 为基准并联运行 ({self.bus_freq:.1f}Hz, {self.bus_amp:.0f}V)"
                else:
                    self.bus_status_msg = f"母排: Gen 2 独立供电 ({self.bus_freq:.1f}Hz, {self.bus_amp:.0f}V)"
            else:
                self.bus_freq = 0.0
                self.bus_amp = 0.0
                self.bus_phase = 0.0
                self.bus_source = None
                self.bus_live = False
                self.bus_status_msg = "母排: 无电 (死母线)"
                self.bus_reference_msg = "参考基准: 无"
                self.bus_reference_gen = None
        else:
            self.bus_freq = GRID_FREQ
            self.bus_amp = GRID_AMP
            self.bus_phase = 0.0
            self.bus_source = "grid"
            self.bus_live = True
            self.bus_status_msg = f"母排: 电网供电 ({GRID_FREQ}Hz)"
            self.bus_reference_msg = "参考基准: 外部电网"
            self.bus_reference_gen = None

        return {
            'g1_on_bus': g1_on_bus,
            'g2_on_bus': g2_on_bus,
            'ref_freq': self.bus_freq if self.bus_live else GRID_FREQ,
            'ref_amp': self.bus_amp if self.bus_live else GRID_AMP,
            'reference_gen': self.bus_reference_gen,
        }

    def _update_arbitration(self, sim, g1_on_bus, g2_on_bus, ref_freq, ref_amp) -> None:
        """Remote automatic arbitration is intentionally disabled in exam mode."""
        self.dead_bus_timer = 0.0
        self.first_ready = None