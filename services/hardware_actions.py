from __future__ import annotations

from typing import Callable

from domain.enums import BreakerPosition


class HardwareActions:
    """Direct hardware operations for the exam console."""

    def __init__(
        self,
        *,
        sim_state,
        show_warning: Callable[[str, str], None],
        is_free_exam_active: Callable[[], bool] | None = None,
        on_free_exam_final_close_attempt: Callable[[], bool] | None = None,
    ):
        self._sim_state = sim_state
        self._show_warning = show_warning
        self._is_free_exam_active = is_free_exam_active or (lambda: False)
        self._on_free_exam_final_close_attempt = on_free_exam_final_close_attempt or (lambda: True)

    def toggle_engine(self, gen_id: int) -> None:
        gen = self._get_generator_state(gen_id)
        if not gen.running and gen.mode != "manual":
            self._show_warning(
                "操作闭锁",
                "当前操作未被执行。",
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
                "位置闭锁",
                "断路器位置未改变。",
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
                "合闸闭锁",
                "断路器未动作。",
            )
            return
        if gen.breaker_position == BreakerPosition.DISCONNECTED:
            self._show_warning(
                "合闸闭锁",
                "断路器未动作。",
            )
            return
        if gen.breaker_position == BreakerPosition.WORKING and not gen.running:
            self._show_warning(
                "合闸闭锁",
                "断路器未动作。",
            )
            return

        is_final_gen2_close = (
            self._is_free_exam_active()
            and gen_id == 2
            and gen.breaker_position == BreakerPosition.WORKING
        )
        if is_final_gen2_close and not self._on_free_exam_final_close_attempt():
            self._show_warning("考核已结束", "当前操作未被执行。")
            return

        gen.cmd_close = True

    def _get_generator_state(self, gen_id: int):
        return self._sim_state.gen1 if gen_id == 1 else self._sim_state.gen2
