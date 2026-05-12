from __future__ import annotations


class RecordTablesMixin:
    """Exam build does not render the old guided-step record tables."""

    def _build_record_tables(self, ax) -> None:
        return None

    def _render_pt_record_tables(self, p) -> None:
        return None
