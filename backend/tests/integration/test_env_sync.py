"""Tests for repository bootstrap guardrails."""

import subprocess
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def load_env_sync_module() -> object:
    """Load the standalone environment-sync script for direct unit coverage."""

    spec = spec_from_file_location("check_env_sync", ROOT / "scripts" / "check_env_sync.py")
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_environment_template_covers_current_settings() -> None:
    """AC-4: the checked-in template documents all Settings fields."""

    module = load_env_sync_module()

    assert module.missing_settings_keys() == []


def test_environment_sync_names_missing_setting() -> None:
    """AC-4: a new undocumented setting is reported with a clear name."""

    module = load_env_sync_module()

    assert module.missing_settings_keys({"app_env", "new_required_setting"}, {"APP_ENV"}) == [
        "NEW_REQUIRED_SETTING"
    ]


def test_port_conflict_prints_friendly_guidance(tmp_path: Path) -> None:
    """AC-3: port conflicts explain which environment value to change."""

    fake_lsof = tmp_path / "lsof"
    fake_lsof.write_text("#!/usr/bin/env sh\nexit 0\n")
    fake_lsof.chmod(0o755)
    environment = {"PATH": f"{tmp_path}:{Path('/usr/bin')}:/bin", "API_PORT": "8000"}

    result = subprocess.run(
        ["sh", str(ROOT / "scripts" / "check_ports.sh")],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    assert result.returncode == 1
    assert "Change API_PORT or FRONTEND_PORT in .env" in result.stderr
