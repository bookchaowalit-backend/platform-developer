"""Reproducible build gate: the shared core resolves only to the reviewed commit."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_URL = "https://github.com/bookchaowalit-backend/platform-backend-core.git"


def workflow_core_commit() -> str:
    text = (ROOT / ".github" / "workflows" / "shared-runtime.yml").read_text(encoding="utf-8")
    commits = set(re.findall(r"platform-backend-core\.git@([0-9a-f]{40})", text))
    assert len(commits) == 1, commits
    return commits.pop()


def test_uv_source_pins_the_commit_ci_installs():
    # platform-backend-core is not on PyPI: without a git source pin a resolver could
    # pick a same-named PyPI upload (dependency confusion).
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    source = project.get("tool", {}).get("uv", {}).get("sources", {}).get("platform-backend-core")
    assert source == {"git": CORE_URL, "rev": workflow_core_commit()}


def test_core_dependency_is_exact():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "platform-backend-core==0.1.0" in project["project"]["dependencies"]
