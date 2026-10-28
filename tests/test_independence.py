"""Tests for scripts/check_independence.py and the BOO-155 gate fixture."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "gates" / "template-independence.json"
NESTED_ENV = "PLATFORM_INDEPENDENCE_NESTED"
IGNORED = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "dist", "build", ".venv")


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


independence = _load("platform_independence", "scripts/check_independence.py")


def _copy_repository(destination: Path) -> Path:
    """Copy this repository alone into ``destination/platform-developer``."""

    target = destination / "platform-developer"
    shutil.copytree(ROOT, target, ignore=IGNORED)
    return target


class IndependenceCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = _copy_repository(Path(self._temp.name))

    def tearDown(self) -> None:
        self._temp.cleanup()

    def append(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")

    def inject(self, relative: str, code: str) -> None:
        """Insert module-level ``code`` before the script's ``__main__`` guard so it runs."""

        path = self.root / relative
        text = path.read_text(encoding="utf-8")
        guard = '\nif __name__ == "__main__":'
        self.assertIn(guard, text)
        path.write_text(text.replace(guard, f"\n{code}\n{guard}", 1), encoding="utf-8")

    def test_repository_is_independent(self) -> None:
        self.assertEqual(independence.static_errors(ROOT), [])
        self.assertEqual(independence.trace_errors(ROOT), [])

    def test_third_party_import_fails(self) -> None:
        self.append("scripts/check_registry_alignment.py", "\nimport yaml\n")
        errors = independence.static_errors(self.root)
        self.assertTrue(any("imports 'yaml'" in error for error in errors), errors)

    def test_product_package_import_fails(self) -> None:
        self.append("tests/test_drift_checks.py", "\nfrom platform_finance import ledger\n")
        errors = independence.static_errors(self.root)
        self.assertTrue(any("imports 'platform_finance'" in error for error in errors), errors)

    def test_sys_path_use_fails(self) -> None:
        self.append("scripts/check.py", "\nsys.path.insert(0, str(ROOT))\n")
        errors = independence.static_errors(self.root)
        self.assertTrue(any("uses sys.path" in error for error in errors), errors)

    def test_hard_coded_sibling_checkout_fails(self) -> None:
        # Built at run time so this file does not itself hold the path the check forbids.
        sibling = "/".join(["..", "solo-empire", "repository-catalog"])  # noqa: FLY002
        self.append("scripts/check_registry_alignment.py", f'\nDEFAULT_SOLO = "{sibling}"\n')
        errors = independence.static_errors(self.root)
        self.assertTrue(any("sibling checkout path" in error for error in errors), errors)
        self.assertTrue(any("solo-empire checkout path" in error for error in errors), errors)

    def test_product_source_paths_fail(self) -> None:
        cases = {
            "book-dev clone folder": "projects" + "/product/engineering/book-dev",
            "solo-empire control-plane source": "infra" + "/tasks/platform.yml",
            "absolute home path": "/" + "home/someone/repo",
        }
        for label, text in cases.items():
            with self.subTest(label=label):
                root = _copy_repository(Path(tempfile.mkdtemp(dir=self._temp.name)))
                path = root / ".github" / "workflows" / "check.yml"
                path.write_text(path.read_text(encoding="utf-8") + f"\n# {text}\n", encoding="utf-8")
                errors = independence.static_errors(root)
                self.assertTrue(any(label in error for error in errors), errors)

    def test_allow_marker_only_applies_to_tests(self) -> None:
        marker = independence.ALLOW_MARKER
        self.append("scripts/check.py", f'\nX = "..{"/"}x"  {marker}\n')
        errors = independence.static_errors(self.root)
        self.assertTrue(any("scripts/check.py" in error and "sibling" in error for error in errors), errors)

    def test_default_gate_reading_outside_repository_fails(self) -> None:
        outside = Path(self._temp.name) / "outside.txt"
        outside.write_text("product source\n", encoding="utf-8")
        self.inject("scripts/check_schema_pin.py", "_ = (Path(__file__).resolve().parents[2] / 'outside.txt').read_text()")
        self.assertEqual(independence.static_errors(self.root), [])
        errors = independence.trace_errors(self.root)
        self.assertTrue(any(str(outside.resolve()) in error for error in errors), errors)

    def test_default_gate_starting_a_process_fails(self) -> None:
        self.inject("scripts/check.py", "import subprocess\nsubprocess.run(['true'], check=False)")
        errors = independence.trace_errors(self.root)
        self.assertTrue(any("subprocess.Popen" in error for error in errors), errors)

    def test_default_gate_ignores_canonical_override(self) -> None:
        missing = Path(self._temp.name) / "no-such-core"
        previous = os.environ.get("BOOK_BACKEND_CORE_DIR")
        os.environ["BOOK_BACKEND_CORE_DIR"] = str(missing)
        try:
            self.assertEqual(independence.trace_errors(self.root), [])
        finally:
            if previous is None:
                os.environ.pop("BOOK_BACKEND_CORE_DIR")
            else:
                os.environ["BOOK_BACKEND_CORE_DIR"] = previous

    def test_main_exit_codes(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(independence.main([str(self.root), "--static-only"]), 0)
        self.assertIn("OK:", out.getvalue())
        self.append("scripts/check.py", "\nimport requests\n")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(independence.main([str(self.root), "--static-only"]), 1)
        self.assertIn("FAIL:", out.getvalue())


FIXTURE_HINT = (
    "update platform_developer.files in fixtures/gates/template-independence.json "
    "and the inventory in docs/gates/BOO-155-template-independence.md"
)


def fixture_drift(section: dict, actual: list[str]) -> tuple[list[str], list[str]]:
    """Return ``(unlisted, absent)``; a listed file may be absent only with the pending marker."""

    marker = section["pending_marker"]
    listed = {item["path"] for item in section["files"]}
    unlisted = sorted(set(actual) - listed)
    absent = sorted(
        item["path"]
        for item in section["files"]
        if item["path"] not in actual and not str(item.get("present_on", "")).startswith(marker)
    )
    return unlisted, absent


class GateFixtureTests(unittest.TestCase):
    """Fail when fixtures/gates/template-independence.json drifts from the repository."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_lists_every_file_in_scope(self) -> None:
        section = self.fixture["platform_developer"]
        listed = [item["path"] for item in section["files"]]
        self.assertEqual(len(listed), len(set(listed)), "fixture lists a file twice")
        unlisted, absent = fixture_drift(section, independence.scope_files(ROOT))
        self.assertEqual(unlisted, [], f"in-scope files missing from the fixture: {unlisted}; {FIXTURE_HINT}")
        self.assertEqual(absent, [], f"fixture lists files that do not exist: {absent}; {FIXTURE_HINT}")

    def test_present_files_carry_no_pending_marker(self) -> None:
        # A pending marker only covers a file that has not landed yet; once the file is
        # in the repository the marker is stale and must be removed (BOO-155 gap 5).
        section = self.fixture["platform_developer"]
        actual = set(independence.scope_files(ROOT))
        stale = sorted(item["path"] for item in section["files"] if "present_on" in item and item["path"] in actual)
        self.assertEqual(stale, [], f"remove present_on from files that now exist: {stale}; {FIXTURE_HINT}")

    def test_pending_marker_tolerates_only_absent_listed_files(self) -> None:
        section = json.loads(json.dumps(self.fixture["platform_developer"]))
        # a synthetic not-yet-landed file keeps this rule exercised when nothing is pending
        section["files"].append({"path": ".github/workflows/not-landed.yml", "present_on": section["pending_marker"] + "synthetic"})
        pending = [item["path"] for item in section["files"] if "present_on" in item]
        actual = [path for path in independence.scope_files(ROOT) if path not in pending]
        self.assertEqual(fixture_drift(section, actual), ([], []))
        # an unlisted in-scope file still fails, whatever is pending
        self.assertEqual(fixture_drift(section, actual + [".github/workflows/extra.yaml"])[0], [".github/workflows/extra.yaml"])
        # a listed-but-absent file without the pending marker fails
        for item in section["files"]:
            item.pop("present_on", None)
        self.assertEqual(fixture_drift(section, actual), ([], sorted(pending)))

    def test_fixture_default_gate_matches_check_sh(self) -> None:
        self.assertEqual(self.fixture["platform_developer"]["default_gate"], independence.default_gate(ROOT))

    def test_ci_flags_match_check_sh(self) -> None:
        check_sh = (ROOT / "scripts" / "check.sh").read_text(encoding="utf-8")
        for item in self.fixture["platform_developer"]["files"]:
            path = item["path"]
            if path.startswith("scripts/") and path.endswith(".py"):
                with self.subTest(path=path):
                    self.assertEqual(item["in_ci"], f"python3 {path}" in check_sh)

    def test_fixture_pins_allowed_lines(self) -> None:
        self.assertEqual(self.fixture["platform_developer"]["allowed_lines"], independence.allowed_lines(ROOT))

    def test_fixture_rules_match_check(self) -> None:
        labels = [label for label, _ in independence.FORBIDDEN_PATTERNS]
        self.assertEqual(self.fixture["rules"]["forbidden_path_patterns"], labels)
        self.assertEqual(self.fixture["rules"]["dropped_env"], list(independence.DROPPED_ENV))

    def test_fixture_contract_and_decision(self) -> None:
        self.assertEqual(self.fixture["contract"]["path"], "systems/architecture/repository-boundaries.md")
        decision = self.fixture["owner_decision"]
        self.assertEqual(decision["status"], "accepted")
        self.assertEqual(decision["date"], "2026-10-16")
        self.assertTrue(decision["answer_verbatim"])
        self.assertEqual(len(decision["policies"]), 3)
        self.assertTrue(decision["open_follow_ups"])
        doc = ROOT / "docs" / "gates" / "BOO-155-template-independence.md"
        self.assertTrue(doc.is_file())
        text = doc.read_text(encoding="utf-8")
        self.assertIn(self.fixture["next_gate"], text)
        self.assertIn(f"## Owner decision — ACCEPTED (owner decision {decision['date']})", text)
        self.assertIn(decision["answer_verbatim"], text)
        self.assertNotIn("PROPOSED, NOT ACCEPTED", text)

    def test_solo_empire_inventory_has_evidence(self) -> None:
        items = self.fixture["solo_empire_inventory"]["items"]
        self.assertTrue(items)
        for item in items:
            with self.subTest(path=item["path"]):
                self.assertTrue(item["evidence"])
                self.assertIn(item["product_source"], (True, False, "unknown"))
                self.assertIsInstance(item["present"], bool)


@unittest.skipIf(os.environ.get(NESTED_ENV) == "1", "already running inside the clean-checkout copy")
class CleanCheckoutTests(unittest.TestCase):
    """Copy the repository alone into an empty directory and run its full local check there."""

    def test_full_check_runs_without_sibling_repositories(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            isolated = Path(temp) / "isolated"
            home = Path(temp) / "home"
            isolated.mkdir()
            home.mkdir()
            root = _copy_repository(isolated)
            self.assertEqual(sorted(p.name for p in isolated.iterdir()), ["platform-developer"])
            env = {key: value for key, value in os.environ.items() if key not in independence.DROPPED_ENV}
            env.update({NESTED_ENV: "1", "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1"})
            result = subprocess.run(
                ["bash", str(root / "scripts" / "check.sh")],
                cwd=home, env=env, capture_output=True, text=True, timeout=300, check=False,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output[-2000:])
            self.assertIn("are independent of product source", output)
            self.assertIn("OK: platform-developer", output)


if __name__ == "__main__":
    unittest.main()
