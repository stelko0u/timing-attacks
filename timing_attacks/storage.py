from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class RunState:
    run_id: str
    status: str  # queued | running | done | error
    created_at: float
    updated_at: float
    progress: dict
    result: dict | None
    error: str | None


class RunStore:
    def __init__(self, root: Path):
        self._root = root
        self._lock = threading.Lock()
        self._states: dict[str, RunState] = {}
        self._root.mkdir(parents=True, exist_ok=True)

    def create(self) -> RunState:
        run_id = f"run_{int(time.time() * 1000)}_{os.getpid()}"
        now = time.time()
        st = RunState(
            run_id=run_id,
            status="queued",
            created_at=now,
            updated_at=now,
            progress={},
            result=None,
            error=None,
        )
        with self._lock:
            self._states[run_id] = st
        (self._root / run_id).mkdir(parents=True, exist_ok=True)
        self._write_state(st)
        return st

    def get(self, run_id: str) -> RunState | None:
        with self._lock:
            return self._states.get(run_id)

    def update(self, run_id: str, **kwargs) -> RunState:
        with self._lock:
            st = self._states[run_id]
            for k, v in kwargs.items():
                setattr(st, k, v)
            st.updated_at = time.time()
        self._write_state(st)
        return st

    def run_dir(self, run_id: str) -> Path:
        return self._root / run_id

    def write_json(self, run_id: str, name: str, data: dict) -> None:
        p = self.run_dir(run_id) / name
        p.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")

    def write_csv(self, run_id: str, name: str, header: list[str], rows: list[dict]) -> None:
        p = self.run_dir(run_id) / name
        out = [",".join(header)]
        for r in rows:
            out.append(",".join(_csv_cell(r.get(h)) for h in header))
        p.write_text("\n".join(out) + "\n", encoding="utf-8")

    def _write_state(self, st: RunState) -> None:
        self.write_json(st.run_id, "state.json", asdict(st))


def _csv_cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if any(c in s for c in [",", "\n", "\r", '"']):
        s = s.replace('"', '""')
        return f'"{s}"'
    return s
