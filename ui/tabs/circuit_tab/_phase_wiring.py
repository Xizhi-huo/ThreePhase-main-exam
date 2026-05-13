from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from domain.node_map import NODES


class PhaseWiringStatus(StrEnum):
    IDLE = "idle"
    WIRING = "wiring"
    READY = "ready"


@dataclass
class PhaseWiringSession:
    enabled: bool = False
    active_pt: str | None = None
    wired: set[str] = field(default_factory=set)


class PhaseWiringMixin:
    _PHASE_SEQ_PTS = ("PT1", "PT2", "PT3")

    def _place_phase_seq_meter(self) -> None:
        mw, mh = self.phase_seq_meter.width(), self.phase_seq_meter.height()
        bbox = self.ax_circuit.get_position()
        xlim = self.ax_circuit.get_xlim()
        ylim = self.ax_circuit.get_ylim()
        cw, ch = self.canvas2.width(), self.canvas2.height()
        if xlim[1] == xlim[0] or ylim[1] == ylim[0]:
            px, py = cw // 2, ch // 2
        else:
            ax_fx = (0.50 - xlim[0]) / (xlim[1] - xlim[0])
            ax_fy = (0.72 - ylim[0]) / (ylim[1] - ylim[0])
            fig_fx = bbox.x0 + ax_fx * (bbox.x1 - bbox.x0)
            fig_fy = bbox.y0 + ax_fy * (bbox.y1 - bbox.y0)
            px = int(fig_fx * cw)
            py = int((1.0 - fig_fy) * ch)

        mx = px - mw // 2
        my = py - mh // 2
        self.phase_seq_meter.move(mx, my)
        self.phase_seq_meter.setVisible(True)
        self.phase_seq_meter.raise_()

    def get_phase_wiring_status(self) -> PhaseWiringStatus:
        if not self._phase_wiring.enabled:
            return PhaseWiringStatus.IDLE
        if self._phase_wiring.active_pt is not None and self._phase_wiring.wired == {"A", "B", "C"}:
            return PhaseWiringStatus.READY
        return PhaseWiringStatus.WIRING

    def get_phase_wiring_active_pt(self) -> str | None:
        return self._phase_wiring.active_pt

    def _phase_target_nodes(self) -> tuple[str, ...]:
        if not self._phase_wiring.enabled:
            return ()
        active_pt = self._phase_wiring.active_pt
        if active_pt in self._PHASE_SEQ_PTS and self.get_phase_wiring_status() != PhaseWiringStatus.READY:
            pts = (active_pt,)
        else:
            pts = self._PHASE_SEQ_PTS
        return tuple(f"{pt}_{phase}" for pt in pts for phase in ("A", "B", "C"))

    def enable_phase_seq_meter(self) -> None:
        self._phase_wiring.enabled = True
        self._phase_wiring.active_pt = None
        self._phase_wiring.wired.clear()
        self.phase_seq_meter.set_waiting("相序仪", 0, 3)
        self.phase_seq_meter.set_freq(50.0)
        self._place_phase_seq_meter()
        self._psm_result_lbl.setVisible(False)
        self.canvas2.draw_idle()

    def connect_phase_seq_meter(self, pt_name: str) -> None:
        pt_name = pt_name.upper()
        if pt_name not in self._PHASE_SEQ_PTS:
            return
        self._phase_wiring.enabled = True
        self._phase_wiring.active_pt = pt_name
        self._phase_wiring.wired.clear()

        self.phase_seq_meter.set_waiting(pt_name, 0, 3)
        self.phase_seq_meter.set_freq(self._phase_meter_frequency(pt_name))
        self._place_phase_seq_meter()
        self._psm_result_lbl.setVisible(False)
        self.canvas2.draw_idle()

    def disconnect_phase_seq_meter(self) -> None:
        self._phase_wiring.enabled = False
        self._phase_wiring.active_pt = None
        self._phase_wiring.wired.clear()
        self.phase_seq_meter.disconnect()
        self.phase_seq_meter.setVisible(False)
        self._psm_result_lbl.setVisible(False)
        self.canvas2.draw_idle()

    def _phase_meter_frequency(self, pt_name: str) -> float:
        sim = self._api.sim_state
        if pt_name == "PT3":
            return sim.gen2.freq
        if pt_name == "PT2" and getattr(self, "bus_live", False):
            return getattr(self, "bus_freq", 50.0)
        return sim.gen1.freq

    def _start_phase_wiring_target(self, pt_name: str) -> None:
        self._phase_wiring.active_pt = pt_name
        self._phase_wiring.wired.clear()
        self.phase_seq_meter.set_waiting(pt_name, 0, 3)
        self.phase_seq_meter.set_freq(self._phase_meter_frequency(pt_name))
        self._psm_result_lbl.setVisible(False)

    def _show_phase_seq_result(self, pt_name: str, seq: str) -> None:
        self.phase_seq_meter.connect_pt(pt_name, seq)
        self._place_phase_seq_meter()

        if seq in {"ABC", "BCA", "CAB"}:
            color, label = "#e5e7eb", "正序"
        elif seq == "FAULT":
            color, label = "#e5e7eb", "----"
        else:
            color, label = "#e5e7eb", "反序"

        self._psm_result_lbl.setText(f"{pt_name} -> {label}")
        self._psm_result_lbl.setStyleSheet(
            f"color:{color}; font-size:10px;"
            " background: rgba(30, 39, 46, 200);"
            " border-radius: 4px;"
            " padding: 2px 6px;"
        )
        self._psm_result_lbl.adjustSize()

        mw, mh = self.phase_seq_meter.width(), self.phase_seq_meter.height()
        px = self.phase_seq_meter.x() + mw // 2
        py = self.phase_seq_meter.y() + mh
        lw = self._psm_result_lbl.width()
        self._psm_result_lbl.move(max(0, px - lw // 2), py + 4)
        self._psm_result_lbl.setVisible(True)
        self._psm_result_lbl.raise_()
        self.canvas2.draw_idle()

    def handle_phase_wiring_click(self, event) -> bool:
        if self.get_phase_wiring_status() == PhaseWiringStatus.IDLE:
            return False
        if event.inaxes != self.ax_circuit or event.xdata is None or event.ydata is None:
            return True

        closest_node = None
        min_dist = 0.04
        for node_name in self._phase_target_nodes():
            x, y = NODES[node_name][:2]
            dist = ((event.xdata - x) ** 2 + (event.ydata - y) ** 2) ** 0.5
            if dist < min_dist:
                closest_node = node_name
                min_dist = dist

        if closest_node is None:
            return True

        pt_name, phase = closest_node.split("_", 1)
        if self._phase_wiring.active_pt != pt_name or self.get_phase_wiring_status() == PhaseWiringStatus.READY:
            self._start_phase_wiring_target(pt_name)

        if phase not in self._phase_wiring.wired:
            self._phase_wiring.wired.add(phase)
            self.phase_seq_meter.set_waiting(
                self._phase_wiring.active_pt,
                len(self._phase_wiring.wired),
                3,
            )
            if self._phase_wiring.wired == {"A", "B", "C"}:
                seq = self._api.get_pt_phase_sequence(self._phase_wiring.active_pt)
                self._show_phase_seq_result(self._phase_wiring.active_pt, seq)

        self.canvas2.draw_idle()
        return True

    def _render_phase_wiring(self) -> None:
        active_pt = self._phase_wiring.active_pt
        wired = self._phase_wiring.wired
        status = self.get_phase_wiring_status()

        for node_name, pack in self._psm_terminal_markers.items():
            pt_name, phase = node_name.split("_", 1)
            if status == PhaseWiringStatus.IDLE:
                is_target = False
            elif active_pt is None:
                is_target = True
            else:
                is_target = active_pt == pt_name
            is_wired = is_target and active_pt == pt_name and phase in wired

            pack["ring"].set_visible(is_target)
            pack["fill"].set_visible(is_wired)


__all__ = ["PhaseWiringMixin", "PhaseWiringSession", "PhaseWiringStatus"]