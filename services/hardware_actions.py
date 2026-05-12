from __future__ import annotations

import math
from typing import Callable

from domain.constants import GRID_AMP, GRID_FREQ
from domain.enums import BreakerPosition


class HardwareActions:
    """Direct hardware operations for the exam console."""

    def __init__(
        self,
        *,
        sim_state,
        get_physics: Callable[[], object],
        show_warning: Callable[[str, str], None],
        is_free_exam_active: Callable[[], bool] | None = None,
        on_free_exam_final_close_attempt: Callable[[], bool] | None = None,
    ):
        self._sim_state = sim_state
        self._get_physics = get_physics
        self._show_warning = show_warning
        self._is_free_exam_active = is_free_exam_active or (lambda: False)
        self._on_free_exam_final_close_attempt = on_free_exam_final_close_attempt or (lambda: True)

    def instant_sync(self) -> None:
        physics = self._get_physics()
        target_phase_deg = math.degrees(getattr(physics, "bus_phase", 0.0)) if getattr(physics, "bus_live", False) else 0.0
        for gen in (self._sim_state.gen1, self._sim_state.gen2):
            gen.freq = GRID_FREQ
            gen.amp = GRID_AMP
            gen.phase_deg = target_phase_deg

    def toggle_engine(self, gen_id: int) -> None:
        gen = self._get_generator_state(gen_id)
        if not gen.running and gen.mode != "manual":
            self._show_warning(
                "起机条件不满足",
                f"Gen {gen_id} 只有在手动工作模式下才能起机。请先切换为手动模式。",
            )
            return
        gen.running = not gen.running
        if not gen.running:
            gen.breaker_closed = False
            gen.cmd_close = False

    def change_breaker_position(self, gen_id: int, position: str) -> bool:
        gen = self._get_generator_state(gen_id)
        if position == gen.breaker_position:
            return True
        if gen.breaker_closed or gen.cmd_close:
            self._show_warning(
                "禁止切换开关柜位置",
                f"Gen {gen_id} 断路器已闭合或正在合闸，不能切换脱开/试验/工作位置。请先控分，再切换位置。",
            )
            return False
        gen.breaker_position = position
        return True

    def toggle_breaker(self, gen_id: int) -> None:
        gen = self._get_generator_state(gen_id)
        if gen.breaker_closed:
            gen.breaker_closed = False
            gen.cmd_close = False
            return

        if gen.mode != "manual":
            self._show_warning(
                "合闸条件不满足",
                f"Gen {gen_id} 断路器当前只能在手动模式下由按钮合闸。",
            )
            return
        if gen.breaker_position == BreakerPosition.WORKING and not gen.running:
            self._show_warning(
                "合闸条件不满足",
                f"Gen {gen_id} 尚未起机，工作位合闸会被失压保护拒绝。",
            )
            return

        is_final_gen2_close = (
            self._is_free_exam_active()
            and gen_id == 2
            and gen.breaker_position == BreakerPosition.WORKING
        )
        if is_final_gen2_close and not self._on_free_exam_final_close_attempt():
            self._show_warning("考核已结束", "Gen2 最终并母合闸只允许尝试一次。")
            return

        gen.cmd_close = True

    def _get_generator_state(self, gen_id: int):
        return self._sim_state.gen1 if gen_id == 1 else self._sim_state.gen2
