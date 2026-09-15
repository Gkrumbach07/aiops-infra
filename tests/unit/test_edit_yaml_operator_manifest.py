"""Tests for ensure-operator-component in scripts/edit_yaml.py."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EDIT_YAML = REPO_ROOT / "scripts" / "edit_yaml.py"


def _run_ensure(
    tmp_path: Path,
    manifest_content: str,
    component: str,
    src: str,
    dest: str,
    manifest_type: str = "",
) -> subprocess.CompletedProcess:
    manifest = tmp_path / "manifests-config.yaml"
    manifest.write_text(manifest_content, encoding="utf-8")
    cmd = [
        "uv",
        "run",
        str(EDIT_YAML),
        "ensure-operator-component",
        str(manifest),
        "--component-name",
        component,
        "--src",
        src,
        "--dest",
        dest,
    ]
    if manifest_type:
        cmd.extend(["--type", manifest_type])
    return subprocess.run(
        cmd,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )


def test_ensure_appends_new_entry(tmp_path: Path) -> None:
    result = _run_ensure(
        tmp_path,
        "map:\n",
        "my-operator",
        "config/manifests",
        "myoperator",
    )

    assert result.returncode == 0
    assert "status=appended" in result.stdout

    data = yaml.safe_load((tmp_path / "manifests-config.yaml").read_text(encoding="utf-8"))
    assert data["map"]["my-operator"] == {
        "src": "config/manifests",
        "dest": "myoperator",
    }


def test_ensure_complete_entry_is_noop(tmp_path: Path) -> None:
    original = """map:
  my-operator:
    src: config/manifests
    dest: myoperator
"""
    result = _run_ensure(tmp_path, original, "my-operator", "config/manifests", "myoperator")

    assert result.returncode == 0
    assert "status=complete" in result.stdout
    assert (tmp_path / "manifests-config.yaml").read_text(encoding="utf-8") == original


def test_ensure_updates_git_only_entry(tmp_path: Path) -> None:
    result = _run_ensure(
        tmp_path,
        """map:
  my-operator:
    git.url: https://github.com/example/my-operator
    git.commit: github.ref_name
""",
        "my-operator",
        "config/manifests",
        "myoperator",
    )

    assert result.returncode == 0
    assert "status=updated" in result.stdout

    entry = yaml.safe_load((tmp_path / "manifests-config.yaml").read_text(encoding="utf-8"))["map"]["my-operator"]
    assert entry["src"] == "config/manifests"
    assert entry["dest"] == "myoperator"
    assert entry["git.url"] == "https://github.com/example/my-operator"
    assert entry["git.commit"] == "github.ref_name"


def test_ensure_updates_missing_dest_only(tmp_path: Path) -> None:
    result = _run_ensure(
        tmp_path,
        """map:
  my-operator:
    src: config/manifests
    git.url: https://github.com/example/my-operator
""",
        "my-operator",
        "config/manifests",
        "myoperator",
    )

    assert result.returncode == 0
    assert "status=updated" in result.stdout

    entry = yaml.safe_load((tmp_path / "manifests-config.yaml").read_text(encoding="utf-8"))["map"]["my-operator"]
    assert entry["dest"] == "myoperator"


def test_ensure_appends_chart_entry(tmp_path: Path) -> None:
    result = _run_ensure(
        tmp_path,
        "map:\n",
        "odh-observability",
        "charts/odh-observability",
        "odh-observability",
        manifest_type="chart",
    )

    assert result.returncode == 0
    assert "status=appended" in result.stdout

    entry = yaml.safe_load((tmp_path / "manifests-config.yaml").read_text(encoding="utf-8"))["map"]["odh-observability"]
    assert entry == {
        "src": "charts/odh-observability",
        "dest": "odh-observability",
        "type": "chart",
    }


def test_ensure_updates_entry_missing_type_chart(tmp_path: Path) -> None:
    result = _run_ensure(
        tmp_path,
        """map:
  odh-observability:
    src: charts/odh-observability
    dest: odh-observability
    git.url: https://github.com/red-hat-data-services/odh-observability
    git.commit: abc123
""",
        "odh-observability",
        "charts/odh-observability",
        "odh-observability",
        manifest_type="chart",
    )

    assert result.returncode == 0
    assert "status=updated" in result.stdout

    entry = yaml.safe_load((tmp_path / "manifests-config.yaml").read_text(encoding="utf-8"))["map"]["odh-observability"]
    assert entry["type"] == "chart"
    assert entry["git.url"] == "https://github.com/red-hat-data-services/odh-observability"


def test_ensure_complete_chart_entry_is_noop(tmp_path: Path) -> None:
    original = """map:
  odh-observability:
    src: charts/odh-observability
    dest: odh-observability
    type: chart
"""
    result = _run_ensure(
        tmp_path,
        original,
        "odh-observability",
        "charts/odh-observability",
        "odh-observability",
        manifest_type="chart",
    )

    assert result.returncode == 0
    assert "status=complete" in result.stdout
    assert (tmp_path / "manifests-config.yaml").read_text(encoding="utf-8") == original
