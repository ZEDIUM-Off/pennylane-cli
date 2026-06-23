"""Session persistence for Pennylane CLI."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SESSION = Path.home() / ".config" / "cli-anything-pennylane" / "session.json"


def _locked_save_json(
    path: str | os.PathLike[str], data: dict[str, Any], **dump_kwargs: Any
) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.touch(exist_ok=True)
    with file_path.open("r+", encoding="utf-8") as f:
        locked = False
        fcntl_module = None
        try:
            import fcntl as imported_fcntl

            fcntl_module = imported_fcntl
            fcntl_module.flock(f.fileno(), fcntl_module.LOCK_EX)
            locked = True
        except (ImportError, OSError):
            pass
        try:
            f.seek(0)
            f.truncate()
            json.dump(data, f, **dump_kwargs)
            f.write("\n")
            f.flush()
        finally:
            if locked and fcntl_module is not None:
                fcntl_module.flock(f.fileno(), fcntl_module.LOCK_UN)


@dataclass
class Session:
    path: Path = DEFAULT_SESSION
    base_url: str = "https://app.pennylane.com"
    token_env: str = "PENNYLANE_API_TOKEN"
    default_limit: int = 20
    history: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | os.PathLike[str] | None = None) -> Session:
        p = Path(path) if path else DEFAULT_SESSION
        if not p.exists():
            return cls(path=p)
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls(
            path=p,
            base_url=data.get("base_url", "https://app.pennylane.com"),
            token_env=data.get("token_env", "PENNYLANE_API_TOKEN"),
            default_limit=int(data.get("default_limit", 20)),
            history=list(data.get("history", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "token_env": self.token_env,
            "default_limit": self.default_limit,
            "history": self.history[-100:],
        }

    def save(self) -> None:
        _locked_save_json(self.path, self.to_dict(), indent=2, sort_keys=True)

    def record(
        self,
        command: str,
        detail: dict[str, Any] | None = None,
        *,
        dry_run: bool = False,
    ) -> None:
        self.history.append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "command": command,
                "detail": detail or {},
                "dry_run": dry_run,
            }
        )
        if not dry_run:
            self.save()
