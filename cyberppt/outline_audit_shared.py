"""Private shared primitives for Outline audit rule modules."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AuditIssue:
    code: str
    message: str
    pages: tuple[str, ...] = ()
    retry_strategy: str = "rebuild_outline"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _text(value: object) -> str:
    return re.sub(r"[\s，。；：、,.!?！？—_-]+", "", str(value or "")).casefold()


def _page_id(page: dict[str, object]) -> str:
    return str(page.get("page_id") or f"sequence-{page.get('sequence', '?')}")


def _core_message(page: dict[str, object]) -> str:
    """Read the v2 semantic center while retaining v1 compatibility."""

    return str(page.get("core_message") or page.get("main_message") or "").strip()


def _page_mission(page: dict[str, object]) -> str:
    return str(
        page.get("page_mission")
        or page.get("page_job")
        or page.get("business_question")
        or ""
    ).strip()

def _onscreen_conclusion(page: dict[str, object]) -> str:
    return str(
        page.get("onscreen_conclusion") or page.get("onscreen_judgment") or ""
    ).strip()
