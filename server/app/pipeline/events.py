"""In-memory event bus for GET /cases/{id}/events (Server-Sent Events). History is replayed to late subscribers."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any

DONE = "done"


class EventBus:
    def __init__(self, max_cases: int = 200) -> None:
        self._history: dict[int, list[dict[str, Any]]] = defaultdict(list)
        self._subs: dict[int, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)
        self._max_cases = max_cases

    def publish(self, case_id: int, type: str, **data: Any) -> None:
        event = {"type": type, "case_id": case_id, "t": round(time.time(), 3), **data}
        self._history[case_id].append(event)
        for q in self._subs[case_id]:
            q.put_nowait(event)
        while len(self._history) > self._max_cases:
            self._history.pop(next(iter(self._history)))

    def history(self, case_id: int) -> list[dict[str, Any]]:
        return list(self._history.get(case_id, []))

    async def subscribe(self, case_id: int, timeout_s: float = 120.0) -> AsyncIterator[dict[str, Any]]:
        """Replay history, then stream live events until the pipeline says done (or the timeout)."""
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subs[case_id].append(q)
        try:
            past = self.history(case_id)
            for event in past:
                yield event
            if past and past[-1]["type"] == DONE:
                return
            while True:
                event = await asyncio.wait_for(q.get(), timeout=timeout_s)
                yield event
                if event["type"] == DONE:
                    return
        except TimeoutError:
            return
        finally:
            self._subs[case_id].remove(q)


BUS = EventBus()
