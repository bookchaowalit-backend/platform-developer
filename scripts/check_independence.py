#!/usr/bin/env python3
"""Prove the repository templates and boundary checks are independent of product source.

Gate (BOO-155): "Keep repository templates and boundary checks independent from
product source code." This check covers every template and boundary-check file
in this repository (``scripts/``, ``tests/``, ``.github/workflows/``) and fails when:

1. a Python file imports anything other than the standard library or a module
   that lives in this repository's ``scripts/`` or ``tests/`` directories, or
   mutates ``sys.path``;
2. a file references a product source path: the Book Dev clone folder, a
   sibling checkout (parent-directory traversal), an absolute
   home directory, or the solo-empire
   control-plane source trees;
3. a default-gate script (every ``python3 scripts/*.py`` line in
   ``scripts/check.sh`` except this one) opens a file outside the repository
   root or the Python installation, or starts a process or a network
   connection, when run without arguments. This is traced with a
   ``sys.addaudithook`` hook in an isolated (``python3 -I``) subprocess whose
   environment drops the optional ``BOOK_BACKEND_CORE_DIR`` override.

Optional local tools (``check_registry_alignment.py --solo-empire PATH``,
``check_schema_pin.py --canonical PATH``) may read another checkout only through
an explicit argument; rule 2 forbids them from hard-coding where it lives.

The check is offline and read-only, needs no sibling repository, and never
reads secrets. Usage: ``python3 scripts/check_independence.py [ROOT] [--static-only]``.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF_RELATIVE = "scripts/check_independence.py"
SCOPE_GLOBS = ("scripts/*.py", "scripts/*.sh", "tests/*.py", ".github/workflows/*.yml")
LOCAL_MODULE_DIRS = ("scripts", "tests")
GATE_LINE_RE = re.compile(r"^\s*python3\s+(scripts/[\w.-]+\.py)\s*$")
DROPPED_ENV = ("BOOK_BACKEND_CORE_DIR",)
# A line may carry this marker in a trailing comment when it holds negative-test
# input (for example a traversal path the contract check must reject). Every
# allowed line is listed by ``allowed_lines`` and pinned in the gate fixture.
ALLOW_MARKER = "# independence: allow"

# Each pattern is written so that its own source text does not match it
# (``[/]`` instead of ``/``), which lets this file scan itself.
FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("book-dev clone folder", re.compile(r"projects[/]product[/]|book-dev[/]github")),
    ("sibling checkout path", re.compile(r"(?<![\w.])\.\.[/\\](?!\.)")),
    ("absolute home path", re.compile(r"(?<![\w$])(?:[/]home[/]|[/]Users[/]|~[/])")),
    ("solo-empire control-plane source", re.compile(r"infra[/](?:scripts|tasks|mcp-server|database)\b")),
    ("solo-empire checkout path", re.compile(r"solo-empire[/]")),
)

TRACER = r"""
import json, runpy, sys
script, out = sys.argv[1], sys.argv[2]
events = []
recording = [True]
def hook(event, args):
    if not recording[0]:
        return
    if event == "open":
        path = args[0]
        if isinstance(path, bytes):
            path = path.decode("utf-8", "replace")
        if isinstance(path, str):
            events.append(["open", path])
    elif event in ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork", "socket.connect", "socket.getaddrinfo", "urllib.Request"):
        events.append([event, repr(args[:1])])
sys.argv = [script]
code = 0
sys.addaudithook(hook)
try:
    runpy.run_path(script, run_name="__main__")
except SystemExit as exc:
    code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
finally:
    recording[0] = False
    with open(out, "w", encoding="utf-8") as handle:
        json.dump({"exit": code, "events": events}, handle)
"""


def scope_files(root: Path = ROOT) -> list[str]:
    """Return the template and boundary-check files this gate covers, sorted."""

    found: set[str] = set()
    for pattern in SCOPE_GLOBS:
        for path in root.glob(pattern):
            if path.is_file():
                found.add(path.relative_to(root).as_posix())
    return sorted(found)


def default_gate(root: Path = ROOT) -> list[str]:
    """Return the scripts ``scripts/check.sh`` runs without arguments (excluding this check)."""

    check_sh = root / "scripts" / "check.sh"
    if not check_sh.is_file():
        return []
    gates = []
    for line in check_sh.read_text(encoding="utf-8").splitlines():
        match = GATE_LINE_RE.match(line)
        if match and match.group(1) != SELF_RELATIVE:
            gates.append(match.group(1))
    return gates


def local_modules(root: Path = ROOT) -> set[str]:
    return {path.stem for directory in LOCAL_MODULE_DIRS for path in (root / directory).glob("*.py")}


def _imported_roots(tree: ast.AST) -> list[tuple[int, str]]:
    roots: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.extend((node.lineno, alias.name.split(".")[0]) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.append((node.lineno, node.module.split(".")[0]))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "__import__":
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                roots.append((node.lineno, node.args[0].value.split(".")[0]))
    return roots


def _sys_path_uses(tree: ast.AST) -> list[int]:
    return sorted(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr == "path"
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
    )


def allowed_lines(root: Path = ROOT) -> list[str]:
    """Return ``path:line`` for every in-scope line that carries the allow marker."""

    found = []
    for relative in scope_files(root):
        text = (root / relative).read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if ALLOW_MARKER in line and relative.startswith("tests/"):
                found.append(f"{relative}:{lineno}")
    return found


def static_errors(root: Path = ROOT) -> list[str]:
    """Return import and path-reference violations for every file in scope."""

    errors: list[str] = []
    allowed = set(sys.stdlib_module_names) | local_modules(root)
    for relative in scope_files(root):
        text = (root / relative).read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if ALLOW_MARKER in line and relative.startswith("tests/"):
                continue
            for label, pattern in FORBIDDEN_PATTERNS:
                match = pattern.search(line)
                if match:
                    errors.append(f"{relative}:{lineno}: references a {label} ({match.group(0)!r})")
        if not relative.endswith(".py"):
            continue
        try:
            tree = ast.parse(text, filename=relative)
        except SyntaxError as exc:
            errors.append(f"{relative}:{exc.lineno}: cannot parse: {exc.msg}")
            continue
        for lineno, name in _imported_roots(tree):
            if name not in allowed:
                errors.append(f"{relative}:{lineno}: imports {name!r}, which is neither stdlib nor in this repository")
        for lineno in _sys_path_uses(tree):
            errors.append(f"{relative}:{lineno}: uses sys.path; load local modules by file path instead")
    return errors


def _allowed_prefixes(root: Path) -> list[Path]:
    prefixes = {root.resolve()}
    for value in (sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix):
        prefixes.add(Path(value).resolve())
    for key in ("stdlib", "platstdlib", "purelib", "platlib"):
        value = sysconfig.get_paths().get(key)
        if value:
            prefixes.add(Path(value).resolve())
    return sorted(prefixes)


def _inside(path: Path, prefixes: list[Path]) -> bool:
    return any(path == prefix or prefix in path.parents for prefix in prefixes)


def trace_errors(root: Path = ROOT) -> list[str]:
    """Run each default-gate script under an audit hook; report reads outside the repository."""

    root = root.resolve()
    errors: list[str] = []
    gates = default_gate(root)
    if not gates:
        return ["scripts/check.sh declares no default-gate scripts to trace"]
    prefixes = _allowed_prefixes(root)
    env = {key: value for key, value in os.environ.items() if key not in DROPPED_ENV}
    with tempfile.TemporaryDirectory() as temp:
        for relative in gates:
            out = Path(temp) / "trace.json"
            script = root / relative
            if not script.is_file():
                errors.append(f"{relative}: default-gate script is missing")
                continue
            result = subprocess.run(
                [sys.executable, "-I", "-c", TRACER, str(script), str(out)],
                cwd=root, env=env, capture_output=True, text=True, timeout=120, check=False,
            )
            if not out.is_file():
                errors.append(f"{relative}: tracer produced no report: {result.stderr.strip()[-300:]}")
                continue
            report = json.loads(out.read_text(encoding="utf-8"))
            out.unlink()
            if report["exit"] != 0:
                errors.append(f"{relative}: exited {report['exit']} from the repository alone: {result.stdout.strip()[-300:]}")
            outside: list[str] = []
            for event, detail in report["events"]:
                if event != "open":
                    errors.append(f"{relative}: {event} {detail} (gate must not start processes or connect)")
                    continue
                if detail.startswith("/dev/"):
                    continue
                path = Path(detail) if os.path.isabs(detail) else root / detail
                resolved = path.resolve()
                if not _inside(resolved, prefixes) and str(resolved) not in outside:
                    outside.append(str(resolved))
            for path in outside:
                errors.append(f"{relative}: opened {path}, outside the repository")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", default=str(ROOT), help="platform repository root")
    parser.add_argument("--static-only", action="store_true", help="skip the runtime trace of the default gate")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    errors = static_errors(root)
    if not args.static_only:
        errors += trace_errors(root)
    if errors:
        for message in errors:
            print(f"FAIL: {message}")
        return 1
    traced = "static only" if args.static_only else f"traced {len(default_gate(root))} default-gate script(s)"
    print(f"OK: {len(scope_files(root))} template/boundary-check file(s) are independent of product source ({traced})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
