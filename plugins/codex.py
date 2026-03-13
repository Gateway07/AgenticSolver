from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_config() -> dict[str, Any]:
    config_path = _repo_root() / "codex.yaml"
    with config_path.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
    if not isinstance(loaded, dict):
        raise ValueError("codex.yaml did not parse to a mapping")
    return loaded


def _resolve_working_dir(config: dict[str, Any]) -> Path:
    repo_root = _repo_root()

    working_dir_value = config.get("codex_cli", {}).get("working_dir")
    if working_dir_value is None:
        return repo_root

    if not isinstance(working_dir_value, str) or not working_dir_value.strip():
        raise ValueError("codex_cli.working_dir must be a non-empty string")

    working_dir_path = (repo_root / working_dir_value).resolve()
    repo_root_resolved = repo_root.resolve()

    try:
        working_dir_path.relative_to(repo_root_resolved)
    except ValueError as exc:
        raise ValueError(f"codex_cli.working_dir must be under repo root: {repo_root_resolved}") from exc

    if not working_dir_path.exists() or not working_dir_path.is_dir():
        raise ValueError(f"codex_cli.working_dir does not exist or is not a directory: {working_dir_path}")

    return working_dir_path


T = TypeVar('T', bound=BaseModel)


def run(prompt: str, return_type: type[T]) -> T:
    config = _load_config()

    schema_path = Path("result.schema.json")
    schema_json = return_type.model_json_schema()
    schema_path.write_text(json.dumps(schema_json, ensure_ascii=False, indent=2), encoding="utf-8")

    out_path = Path("result.json")
    cmd = ["codex", "exec", "--json",
           "--prompt", prompt,
           "--output-schema", str(schema_path),
           "-o", str(out_path)]
    codex_executable = shutil.which(cmd[0])
    if codex_executable is None:
        raise FileNotFoundError("'codex' executable not found on PATH")

    codex_executable_path = Path(codex_executable)
    if codex_executable_path.suffix.lower() in {".cmd", ".bat"}:
        cmd = ["cmd.exe", "/c", str(codex_executable_path), *cmd[1:]]
    else:
        cmd[0] = str(codex_executable_path)

    timeout_seconds = config.get("timeout_seconds")
    if not isinstance(timeout_seconds, (int, float)):
        timeout_seconds = 600

    working_dir = _resolve_working_dir(config)
    try:
        proc = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            check=True,
            timeout=timeout_seconds,
            env=os.environ.copy(),
            cwd=str(working_dir),
        )
    except subprocess.TimeoutExpired as exc:
        stderr_text = f"codex exec timed out after {timeout_seconds}s\n{exc}".strip()
        raise ValueError(stderr_text)

    if proc.returncode != 0:
        stdout_text = proc.stdout or ""
        stderr_text = proc.stderr or ""
        raise ValueError(stderr_text[-4000:], stdout_text[-4000:])

    return return_type.model_validate_json(out_path.read_text(encoding="utf-8"))
