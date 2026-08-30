from __future__ import annotations

from typing import Type

from ..errors import ConfigError
from .codex_exec import CodexExecAdapter


ADAPTERS: dict[str, Type[CodexExecAdapter]] = {"codex-exec": CodexExecAdapter}


def create_adapter(name: str, executable: str) -> CodexExecAdapter:
    adapter = ADAPTERS.get(name)
    if adapter is None:
        raise ConfigError(f"unsupported adapter: {name}")
    return adapter(executable)
