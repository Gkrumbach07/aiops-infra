"""Tests for ensure-operator-component in scripts/edit_yaml.py."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EDIT_YAML = REPO_ROOT / "scripts" / "edit_yaml.py"


def _run_ensure(tmp_path: Path, manifest_content: str, component: str, src: str, dest: str) -> subprocess.CompletedProcess:
    manifest = tmp_path / "manifests-config.yaml"
    manifest.write_text(manifest_content, encoding="utf-8")
    return subprocess.run(
        [
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
        ],
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
