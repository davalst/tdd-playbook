#!/usr/bin/env python3
"""mutation_run — runs a mutation pass with its preflight ON THE EXECUTION PATH.

NOT §4b-SCOPED (stated 2026-09-09, v1.51.1): --scope is CHECKED against the configured source
scope, never used to NARROW it — mutmut mutates every configured source path and runs the whole
configured test directory, and the baseline runs before the scope check. Narrowing both halves
per run in a disposable worktree is the downstream gate's job until the `mutation-preflight`
debt in capabilities.json is paid or assigned; the word "scoped" was removed from the summary
so the wrapper does not claim what it does not do.

SKILL §4 has required a preflight for a long time, stated in three places (§4, commands/mutate.md,
the mutation-runner brief). In a downstream three-hour session on 2026-08-18 it was skipped anyway
and four runs produced ONE score: #2 died on a RED baseline, #3 timed out at 1800s because the
baseline had grown by four suites and the timeout was never resized. ~1.5 of 3 hours, to two
checks costing thirty seconds.

§10 says why writing it a fourth time would not help: "Trust gates must fire AUTOMATICALLY on the
diffs that can break them — 'remember to run it' is the honor-system seam §13 calls gameable."
So this INVOKES the mutation tool. A tool that checks and advises is another document.

WHAT IT COVERS: §4's (b) collection and (c) green baseline. Roster integrity (a) and tracer
attribution (d) remain the operator's, unchanged in the brief. This ADDS; it replaces no rule.

SCOPE: pytest + mutmut only, and it refuses anything else rather than guessing a denominator.

CORRECTED 2026-08-19 after a script-adversary review returned UNSAFE(9) on the first draft. The
findings are load-bearing and each is now a test:
  * the draft never invoked mutmut — it printed advice and exited 0 under four documents saying
    the pass "cannot be skipped". A wrapper that only prints is the failure its own docstring
    indicted.
  * `rc==0 and collected>0` is NOT evidence anything RAN. An all-skipped suite is green and
    collected and measures nothing; `--collect-only` defeats both checks at once AND collapses
    the measured baseline, so any scope would then look affordable. Outcome is parsed now, and
    `--collect-only` is refused.
  * every non-zero pytest exit was diagnosed as "RED baseline" citing a named plant, discarding
    what pytest actually said. rc 2/3/4/5 are not red suites. The real output is reported.
  * the shell-metacharacter blocklist defended against a shell that is never used, while
    refusing legitimate node ids like `test_p[<lambda>0]`. shlex now, and the blocklist covers
    what actually breaks a run.
  * the child inherited stdin (an invisible hang behind capture_output) and `subprocess.run`'s
    timeout kills only the direct child, orphaning xdist workers — the origin session's 15-minute
    cost, reproduced by construction. New session + process-group kill now.
"""
from __future__ import annotations

import argparse
import shutil
import contextlib
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time

_COLLECTED = re.compile(r"collected (\d+) item")
# The OUTCOME, not the collection. "5 passed", "3 failed, 2 passed", "no tests ran".
_PASSED = re.compile(r"(\d+) passed")
_FAILED = re.compile(r"(\d+) (?:failed|error)")
_NO_TESTS = re.compile(r"no tests ran", re.IGNORECASE)
# A summary that exists but reports no passes — "700 skipped in 1s" — is ZERO passed, which is a
# different (and more useful) refusal than "I could not read the summary".
_OTHER_OUTCOME = re.compile(r"\d+ (?:skipped|deselected|xfailed|xpassed|warning)")
# Args that make a "green baseline" meaningless because nothing executes.
_NON_EXECUTING = ("--collect-only", "--co")


def parse_collected(text):
    """Collected count, or None for UNKNOWN. Never coerced to zero — unmeasured is not empty."""
    m = _COLLECTED.search(text or "")
    return int(m.group(1)) if m else None


def parse_passed(text):
    """Tests that actually PASSED, or None if the summary is unreadable. Collection is not
    execution: 700 skipped tests are green and collected and measure nothing."""
    if _NO_TESTS.search(text or ""):
        return 0
    m = _PASSED.search(text or "")
    if m:
        return int(m.group(1))
    return 0 if _OTHER_OUTCOME.search(text or "") else None


def forbidden_composition(suite_args):
    """Why these args cannot serve as a baseline, or None.

    Deliberately NOT a shell-metacharacter blocklist: the suite runs as an argv list and never
    reaches a shell, so `;`/`>`/backtick have no meaning here — while `test_p[<lambda>0]` is a
    real pytest node id the old blocklist refused. What matters is args under which nothing
    executes, because those defeat the check itself."""
    try:
        parts = shlex.split(suite_args or "")
    except ValueError as exc:
        return f"cannot parse --suite-args ({exc}); quote it as you would for a shell"
    for part in parts:
        if part in _NON_EXECUTING:
            return (f"refusing `{part}` in --suite-args: it collects without executing, so a GREEN "
                    "baseline would prove nothing and the measured time would make any scope "
                    "look affordable")
    return None


def projection_problem(mutants, baseline_seconds, max_minutes, factor=1.0):
    """Refuse an unaffordable pass BEFORE it starts, naming the projection.

    STATED LIMIT: this is only as good as the measured baseline. A near-instant suite makes
    every scope look affordable — which is precisely why `--collect-only` is refused upstream,
    and why a baseline that collected tests but passed none is refused rather than timed. Those
    two refusals are what keep this number honest; the projection alone cannot police itself."""
    projected = (mutants * baseline_seconds * factor) / 60.0
    if projected > max_minutes:
        return (f"refusing before the expensive pass: {mutants} mutants x {baseline_seconds:.1f}s measured baseline "
                f"projects ~{round(projected)} minutes, over the {max_minutes}-minute budget. Raise --max-minutes, "
                "shrink mutmut's configured scope (setup.cfg [mutmut] source_paths / only_mutate — this "
                "wrapper leaves that config as it finds it), or speed the suite — but know the number first"
                )
    return None


def run_bounded(argv, deadline_s, run=None, cwd=None, grace_s=30):
    """Run in its OWN process group with stdin closed, under an ABSOLUTE deadline (Q3, v1.52.0):
    SIGINT to the group at `deadline_s - grace_s` so the tool can flush what it measured, then
    SIGKILL at `deadline_s` — never deadline + grace. Returns a CompletedProcess carrying
    `timed_out` (bool) and `elapsed_s`; a child that honours SIGINT returns its OWN exit code
    with `timed_out=True`, a stubborn one returns a negative code. Callers read `timed_out`
    rather than catching TimeoutExpired, because a cut-off run still has EVIDENCE (partial
    results) and an exception throws it away.

    subprocess.run's timeout kills the direct child only; pytest-xdist workers and anything the
    tests spawned survive as orphans — hence the group. stdin is closed because capture_output
    hides a prompt, so a suite that hits breakpoint()/--pdb would hang invisibly."""
    if run is not None:                      # injected for argv-shape tests ONLY (bypasses Popen)
        proc = run(argv, capture_output=True, text=True, timeout=deadline_s)
        proc.timed_out = False
        proc.elapsed_s = 0.0
        return proc
    grace_s = max(0.0, min(float(grace_s), float(deadline_s)))
    started = time.monotonic()
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, start_new_session=True,
                            cwd=cwd)
    timed_out = False
    try:
        out, _ = proc.communicate(timeout=max(0.0, deadline_s - grace_s))
    except subprocess.TimeoutExpired:
        timed_out = True
        _signal_group(proc, signal.SIGINT)
        try:
            out, _ = proc.communicate(timeout=max(0.0, deadline_s - (time.monotonic() - started)))
        except subprocess.TimeoutExpired:
            _signal_group(proc, signal.SIGKILL)
            out, _ = proc.communicate()
    result = subprocess.CompletedProcess(argv, proc.returncode, out or "", "")
    result.timed_out = timed_out
    result.elapsed_s = time.monotonic() - started
    return result


def _signal_group(proc, sig):
    try:
        os.killpg(os.getpgid(proc.pid), sig)
    except (ProcessLookupError, PermissionError):
        try:
            proc.send_signal(sig)
        except ProcessLookupError:
            pass


def baseline(suite_argv, run=None, timeout=None, cwd=None):
    """(ok, why, seconds, collected) — green AND actually executed, in `cwd` (the worktree)."""
    started = time.time()
    try:
        proc = run_bounded(suite_argv, timeout, run=run, cwd=cwd)
    except subprocess.TimeoutExpired:
        return False, (f"baseline exceeded its {timeout}s bound — UNMEASURED, never assumed green "
                       "(child process group killed)"), time.time() - started, None
    except (OSError, ValueError) as exc:
        return False, f"baseline suite could not be run: {exc}", 0.0, None
    seconds = time.time() - started
    if getattr(proc, "timed_out", False):
        return False, (f"baseline exceeded its {timeout}s bound — UNMEASURED, never assumed green "
                       "(SIGINT then SIGKILL to the child process group)"), seconds, None
    text = (proc.stdout or "") + (proc.stderr or "")
    tail = text.strip()[-1200:]
    if proc.returncode != 0:
        failed = _FAILED.search(text)
        cause = (f"the suite is RED ({failed.group(1)} failing) — a mutation score measured against it is "
                 "meaningless (the `red-baseline-false-green` plant)"
                 if failed else
                 f"pytest exited {proc.returncode} — that is NOT necessarily a red suite (2=interrupted, "
                 "3=internal, 4=usage/ini, 5=no tests). What pytest said:")
        return False, f"baseline refused — {cause}\n{tail}", seconds, None
    collected = parse_collected(text)
    if collected is None:
        return False, ("UNKNOWN collection — no pytest `collected N items` line. This wrapper "
                       "supports pytest + mutmut only and fails closed rather than guessing a "
                       f"denominator. Output was:\n{tail}"), seconds, None
    if collected == 0:
        return False, ("zero tests collected — a vacuous killing suite reports 0 survivors and "
                       "sails every guard (§4: `generated > 0 != measured`)"), seconds, 0
    passed = parse_passed(text)
    if passed is None:
        return False, (f"UNKNOWN outcome — {collected} collected but no `N passed` summary, so nothing "
                       f"proves a test EXECUTED. Output was:\n{tail}"), \
            seconds, collected
    if passed == 0:
        return False, (f"{collected} collected but ZERO passed — a suite that executes nothing is green "
                       "and measures nothing (all-skipped is the common shape). UNMEASURED, "
                       "never green"), seconds, collected
    return True, "", seconds, collected


class ConfigProblem(Exception):
    """mutmut's effective configuration cannot be learned or is not one this wrapper will rewrite."""


class ScopeError(Exception):
    """The scope mapping is missing, malformed, or names something that is not a fact."""


class EffectiveConfig:
    """What mutmut will ACTUALLY use, learned from mutmut's own loader in `cwd` (v1.52.0 D3).

    Never re-implements precedence: pyproject `[tool.mutmut]` wins outright, else setup.cfg
    (`mutmut/configuration.py:19-45`); tox.ini is never read by mutmut and is refused by name.
    `legacy_tests_dir` is surfaced separately because mutmut APPENDS it to the selection
    (`configuration.py:105-110`) — leaving it in a rewritten copy silently widens the baseline."""
    def __init__(self, **kw):
        self.config_file = kw["config_file"]
        self.source_paths = list(kw["source_paths"])
        self.only_mutate = list(kw.get("only_mutate", []))
        self.do_not_mutate = list(kw.get("do_not_mutate", []))
        self.pytest_add_cli_args = list(kw.get("pytest_add_cli_args", []))
        self.selection = list(kw.get("selection", []))
        self.legacy_tests_dir = list(kw.get("legacy_tests_dir", []))


_EFFECTIVE_CONFIG_PROBE = r"""
import json, os, sys
out = {"config_file": None, "tox_ini_has_mutmut": False, "legacy_tests_dir": []}
try:
    import tomllib
except ImportError:
    tomllib = None
try:
    if os.path.exists("pyproject.toml") and tomllib is not None:
        with open("pyproject.toml", "rb") as fh:
            data = tomllib.load(fh)
        table = data.get("tool", {}).get("mutmut")
        if table is not None:
            out["config_file"] = "pyproject.toml"
            td = table.get("tests_dir", [])
            out["legacy_tests_dir"] = [td] if isinstance(td, str) else list(td)
    if out["config_file"] is None:
        import configparser
        cp = configparser.ConfigParser(); cp.read("setup.cfg")
        if cp.has_section("mutmut"):
            out["config_file"] = "setup.cfg"
            if cp.has_option("mutmut", "tests_dir"):
                raw = cp.get("mutmut", "tests_dir")
                out["legacy_tests_dir"] = [x for x in raw.split("\n") if x] if "\n" in raw else [raw]
        cp2 = configparser.ConfigParser(); cp2.read("tox.ini")
        out["tox_ini_has_mutmut"] = cp2.has_section("mutmut")
except Exception as exc:
    out["probe_error"] = repr(exc)
try:
    import warnings
    warnings.simplefilter("ignore")
    from mutmut.configuration import Config
    Config.ensure_loaded(); c = Config.get()
    out.update(source_paths=[str(p) for p in c.source_paths], only_mutate=list(c.only_mutate),
               do_not_mutate=list(c.do_not_mutate), pytest_add_cli_args=list(c.pytest_add_cli_args),
               selection=list(c.pytest_add_cli_args_test_selection))
except ImportError as exc:
    out["mutmut_error"] = "import: " + str(exc)
except FileNotFoundError as exc:
    out["mutmut_error"] = "unconfigured: " + str(exc)
except Exception as exc:
    out["mutmut_error"] = "load: " + repr(exc)
print(json.dumps(out))
"""


def effective_mutmut_config(cwd, python=None):
    """Ask mutmut (in `cwd`, with `python`) what it will use. Raises ConfigProblem with the exact
    remedy; never guesses and never reads a file mutmut would not."""
    proc = subprocess.run([python or sys.executable, "-c", _EFFECTIVE_CONFIG_PROBE], cwd=cwd,
                          capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
    try:
        data = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise ConfigProblem("could not read mutmut's effective config in {}: {}".format(
            cwd, (proc.stdout + proc.stderr)[-400:]))
    if "mutmut_error" in data and data["mutmut_error"].startswith("import:"):
        raise ConfigProblem("mutmut is not importable by {} ({}) — install it in that interpreter "
                            "or pass the one that has it".format(python or sys.executable, data["mutmut_error"]))
    if data.get("config_file") is None:
        if data.get("tox_ini_has_mutmut"):
            raise ConfigProblem("mutmut config found ONLY in tox.ini — mutmut never reads tox.ini "
                                "(configuration.py reads pyproject.toml [tool.mutmut], then "
                                "setup.cfg [mutmut]); move the section to one of those")
        raise ConfigProblem("mutmut is NOT CONFIGURED in {} — add to setup.cfg:\n\n    [mutmut]\n"
                            "    source_paths=<dir>\n\n(or a [tool.mutmut] table in pyproject.toml); "
                            "refusing rather than invoking a tool that will die on its own config".format(cwd))
    if "mutmut_error" in data:
        raise ConfigProblem("mutmut refused its own config in {}: {}".format(cwd, data["mutmut_error"]))
    return EffectiveConfig(**{k: data[k] for k in ("config_file", "source_paths", "only_mutate",
                                                   "do_not_mutate", "pytest_add_cli_args",
                                                   "selection", "legacy_tests_dir")})


SCOPES_REL = os.path.join(".tdd-playbook", "mutation-scopes.json")
SCOPES_MAX_BYTES = 256 * 1024
_SCAFFOLD = """{
  "<scope-name>": {
    "sources": ["pkg/module.py", "pkg/sub/*"],
    "tests":   ["tests/test_module.py", "tests/test_other.py::TestThing"],
    "cost":    "a survivor here costs <the irreversible/security/money consequence>"
  }
}"""


def _no_dup_keys(pairs):
    seen = set(); out = {}
    for k, v in pairs:
        if k in seen:
            raise ScopeError("duplicate scope name {!r} in {} — JSON is last-wins and would hide "
                             "one of them".format(k, SCOPES_REL))
        seen.add(k); out[k] = v
    return out


def load_scopes(root):
    """The repo's machine-readable mutation roster (v1.52.0 D1). Missing → refuse with a scaffold
    to copy (never written for you); duplicate names → refuse; over the size cap → refuse."""
    path = os.path.join(root, SCOPES_REL)
    if not os.path.isfile(path):
        raise ScopeError("no scope mapping at {} — create it (tracked) from this scaffold:\n{}\n"
                         "The mapping IS the mutation roster: exact sources, pytest selectors, and "
                         "the §4 cost line per entry.".format(SCOPES_REL, _SCAFFOLD))
    if os.path.getsize(path) > SCOPES_MAX_BYTES:
        raise ScopeError("{} exceeds {} bytes — a roster, not a database".format(SCOPES_REL, SCOPES_MAX_BYTES))
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        scopes = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_dup_keys)
    except ValueError as exc:
        raise ScopeError("{} is not valid JSON: {}".format(SCOPES_REL, exc))
    if not isinstance(scopes, dict) or not scopes:
        raise ScopeError("{} must be a non-empty object of scope entries".format(SCOPES_REL))
    return scopes


class Scope:
    def __init__(self, name, sources, tests, cost, mapping_sha256):
        self.name = name; self.sources = sources; self.tests = tests; self.cost = cost
        self.mapping_sha256 = mapping_sha256
        self.source_count = len(sources); self.test_count = len(tests)


def _tracked_files(root):
    proc = subprocess.run(["git", "-C", root, "ls-files", "-z"], capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise ScopeError("git ls-files failed in {}: {}".format(root, proc.stderr.strip()))
    return [p for p in proc.stdout.split("\0") if p]


def _glob_match(pattern, path):
    import fnmatch
    return fnmatch.fnmatchcase(path, pattern)


def resolve_scope(root, name, cfg):
    """Turn a mapping entry into FACTS: exact tracked files inside mutmut's parsed source_paths
    (realpath containment — never substring, the `--scope b` class), not excluded by
    do_not_mutate, with ≥1 selector and a cost line."""
    import hashlib
    scopes = load_scopes(root)
    if name not in scopes:
        raise ScopeError("unknown scope {!r}; the mapping defines: {}".format(name, ", ".join(sorted(scopes))))
    entry = scopes[name]
    for key in ("sources", "tests", "cost"):
        if key not in entry:
            raise ScopeError("scope {!r} lacks {!r} (every entry needs sources, tests, cost)".format(name, key))
    if not isinstance(entry["sources"], list) or not entry["sources"]:
        raise ScopeError("scope {!r}: 'sources' must be a non-empty list — an empty scope is a vacuous run".format(name))
    if not isinstance(entry["tests"], list) or not entry["tests"]:
        raise ScopeError("scope {!r}: 'tests' must be a non-empty list of pytest selectors".format(name))
    if not isinstance(entry["cost"], str) or not entry["cost"].strip():
        raise ScopeError("scope {!r}: 'cost' must state what a survivor here costs (§4 roster rule)".format(name))
    real_root = os.path.realpath(root)
    roots = [os.path.realpath(os.path.join(real_root, sp)) for sp in cfg.source_paths]
    tracked = _tracked_files(root)
    files = []
    for pat in entry["sources"]:
        if not isinstance(pat, str) or os.path.isabs(pat) or ".." in pat.split("/"):
            raise ScopeError("scope {!r}: source {!r} must be a relative path or glob without '..'".format(name, pat))
        hits = [t for t in tracked if _glob_match(pat, t)] if any(c in pat for c in "*?[") else ([pat] if pat in tracked else [])
        if not hits:
            raise ScopeError("scope {!r}: source {!r} matches no TRACKED file".format(name, pat))
        for hit in hits:
            rp = os.path.realpath(os.path.join(real_root, hit))
            if not any(rp == r or rp.startswith(r + os.sep) for r in roots):
                raise ScopeError("scope {!r}: {!r} is outside mutmut's source_paths {} — mutmut would "
                                 "never mutate it, and a scope check by substring would have let it "
                                 "through".format(name, hit, cfg.source_paths))
            if any(_glob_match(d, hit) for d in cfg.do_not_mutate):
                raise ScopeError("scope {!r}: {!r} is excluded by do_not_mutate {} — mutmut would "
                                 "silently generate zero mutants for it".format(name, hit, cfg.do_not_mutate))
            if hit not in files:
                files.append(hit)
    for sel in entry["tests"]:
        if not isinstance(sel, str) or os.path.isabs(sel) or ".." in sel.split("/"):
            raise ScopeError("scope {!r}: test selector {!r} must be relative without '..'".format(name, sel))
    with open(os.path.join(root, SCOPES_REL), "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    return Scope(name, files, list(entry["tests"]), entry["cost"], digest)


def collect_selection(cwd, tests, add_args, python=None):
    """(count, problem): how many tests the mapped selectors collect in `cwd`, with mutmut's
    pytest_add_cli_args replayed. Zero is the §4b ROSTER GAP, named as such."""
    argv = [python or sys.executable, "-m", "pytest", "--collect-only"] + list(add_args) + list(tests)
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=600, stdin=subprocess.DEVNULL)
    text = proc.stdout + proc.stderr
    n = parse_collected(text)
    # a node id naming a test that does not exist is pytest "ERROR: not found" (exit 4), which is
    # the same fact as collecting zero: no test reaches the mapped sources
    not_found = proc.returncode == 4 and "not found" in text
    if not not_found and (proc.returncode not in (0, 5) or n is None):
        return 0, ("could not collect {} in {} (pytest exit {}): {}".format(tests, cwd, proc.returncode, text[-300:]))
    if not_found or n == 0:
        return 0, ("could not narrow: no test reaches the mapped selection {} — a ROSTER gap, not a "
                   "gate defect; write the test that reaches these sources, or fix the selector".format(tests))
    return n, None


class NarrowReport:
    def __init__(self, config_file, notes, real_sha256, copy_sha256):
        self.config_file = config_file; self.notes = list(notes)
        self.real_sha256 = real_sha256; self.copy_sha256 = copy_sha256


_MIGRATION_HINT = (
    "Migration: put each rewritten key on ONE line — setup.cfg: `only_mutate=<path>` per line under "
    "[mutmut]; pyproject.toml: `only_mutate = [\"a.py\", \"b/*\"]` on one line under [tool.mutmut]. "
    "Unsupported shapes this wrapper refuses rather than reformats: multi-line arrays, inline "
    "tables, comment-carrying arrays, and the legacy `paths_to_mutate` + `tests_dir` LIST shape "
    "(both keys are deprecated upstream; `tests_dir` is appended to the test selection by mutmut "
    "and must not survive in a narrowed copy)."
)


def _sha256_file(path):
    import hashlib
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _rewrite_setup_cfg(text, sources, tests):
    """Line-anchored rewrite of the [mutmut] section: set only_mutate and
    pytest_add_cli_args_test_selection (multi-line values, one entry per continuation line —
    the form mutmut's setup_cfg_conf splits on '\\n'), drop tests_dir, leave everything else."""
    lines = text.splitlines()
    out, notes = [], []
    in_section = False
    skipping = False
    replaced = set()
    def block(key, values):
        return [key + "="] + ["    " + v for v in values] if len(values) > 1 else [key + "=" + values[0]]
    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if in_section:
                # leaving [mutmut]: insert any keys we never saw
                for key, vals in (("only_mutate", sources), ("pytest_add_cli_args_test_selection", tests)):
                    if key not in replaced:
                        out.extend(block(key, vals)); replaced.add(key); notes.append("inserted " + key)
            in_section = (stripped == "[mutmut]")
            skipping = False
            out.append(ln); continue
        if in_section:
            if ln[:1] in (" ", "\t") and skipping:
                continue                      # continuation line of a key we are replacing/dropping
            skipping = False
            key = stripped.split("=", 1)[0].strip() if "=" in stripped else None
            if key in ("only_mutate", "pytest_add_cli_args_test_selection"):
                vals = sources if key == "only_mutate" else tests
                out.extend(block(key, vals)); replaced.add(key); skipping = True
                notes.append("replaced " + key); continue
            if key == "tests_dir":
                skipping = True; notes.append("neutralised legacy tests_dir (mutmut appends it to the selection)"); continue
            if key == "paths_to_mutate":
                notes.append("left deprecated paths_to_mutate as the source root (only_mutate narrows)")
        out.append(ln)
    if in_section:
        for key, vals in (("only_mutate", sources), ("pytest_add_cli_args_test_selection", tests)):
            if key not in replaced:
                out.extend(block(key, vals)); replaced.add(key); notes.append("inserted " + key)
    return "\n".join(out) + "\n", notes


def _rewrite_pyproject(text, sources, tests):
    """Line-anchored rewrite inside [tool.mutmut] only. Refuses (ConfigProblem) any shape it
    cannot anchor on a single line: a multi-line array or an inline table for a key it must
    touch, or a table header it cannot find. Never a general TOML writer (Q4)."""
    lines = text.splitlines()
    out, notes = [], []
    in_table = False
    replaced = set()
    def one_line(key, values):
        return key + " = [" + ", ".join(json.dumps(v) for v in values) + "]"
    i = 0
    while i < len(lines):
        ln = lines[i]; stripped = ln.strip()
        if stripped.startswith("[") and stripped.endswith("]") and not stripped.startswith("[["):
            if in_table:
                for key, vals in (("only_mutate", sources), ("pytest_add_cli_args_test_selection", tests)):
                    if key not in replaced:
                        out.append(one_line(key, vals)); replaced.add(key); notes.append("inserted " + key)
            in_table = stripped == "[tool.mutmut]"
            out.append(ln); i += 1; continue
        if in_table and "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=", 1)[0].strip()
            rhs = stripped.split("=", 1)[1].strip()
            if key in ("only_mutate", "pytest_add_cli_args_test_selection", "tests_dir"):
                complete = (rhs.startswith("[") and rhs.rstrip().endswith("]") and "#" not in rhs) or rhs.startswith('"')
                if not complete or rhs.startswith("{"):
                    raise ConfigProblem("cannot anchor `{}` in pyproject.toml [tool.mutmut]: its value is not a "
                                        "single-line array (multi-line, inline-table or comment-carrying). "
                                        "{}".format(key, _MIGRATION_HINT))
                if key == "tests_dir":
                    notes.append("neutralised legacy tests_dir (mutmut appends it to the selection)"); i += 1; continue
                vals = sources if key == "only_mutate" else tests
                out.append(one_line(key, vals)); replaced.add(key); notes.append("replaced " + key); i += 1; continue
            if key == "paths_to_mutate":
                notes.append("left deprecated paths_to_mutate as the source root (only_mutate narrows)")
        out.append(ln); i += 1
    if in_table:
        for key, vals in (("only_mutate", sources), ("pytest_add_cli_args_test_selection", tests)):
            if key not in replaced:
                out.append(one_line(key, vals)); replaced.add(key); notes.append("inserted " + key)
    if not any(l.strip() == "[tool.mutmut]" for l in lines):
        raise ConfigProblem("pyproject.toml has no [tool.mutmut] table header to anchor on. " + _MIGRATION_HINT)
    return "\n".join(out) + "\n", notes


def narrow_config(copy_dir, cfg, scope, real_dir=None, python=None, reader=None):
    """Rewrite the mutmut config IN THE COPY (`copy_dir`) so mutmut mutates only `scope.sources`
    and its stats pass runs only `scope.tests`; then READ BACK through mutmut and assert both
    took and legacy tests_dir no longer widens the selection. The real file (in `real_dir`, or
    inferred as the copy's own pre-rewrite content) is never written; its sha256 is recorded."""
    path = os.path.join(copy_dir, cfg.config_file)
    if not os.path.isfile(path):
        raise ConfigProblem("{} is missing in the copy at {} — the copy does not mirror the repo".format(cfg.config_file, copy_dir))
    before_sha = _sha256_file(path)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if cfg.config_file == "setup.cfg":
        new_text, notes = _rewrite_setup_cfg(text, scope.sources, scope.tests)
    else:
        new_text, notes = _rewrite_pyproject(text, scope.sources, scope.tests)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new_text)
    after = (reader or effective_mutmut_config)(copy_dir, python=python)
    if after.only_mutate != list(scope.sources) or after.selection != list(scope.tests) or after.legacy_tests_dir:
        raise ConfigProblem("read-back through mutmut does not match the narrowed scope: only_mutate={} "
                            "selection={} legacy_tests_dir={} (wanted {} / {} / []). The rewrite did not "
                            "take; refusing to run over an unscoped tree. {}".format(
                                after.only_mutate, after.selection, after.legacy_tests_dir,
                                scope.sources, scope.tests, _MIGRATION_HINT))
    if after.do_not_mutate != cfg.do_not_mutate or after.pytest_add_cli_args != cfg.pytest_add_cli_args:
        raise ConfigProblem("the rewrite disturbed keys it must preserve (do_not_mutate / pytest_add_cli_args)")
    real_sha = _sha256_file(os.path.join(real_dir, cfg.config_file)) if real_dir else before_sha
    if real_dir and real_sha != before_sha:
        raise ConfigProblem("the copy's config did not match the real one before rewriting — refusing")
    notes.append("read back through mutmut: OK")
    return NarrowReport(cfg.config_file, notes, real_sha, _sha256_file(path))


def forbidden_add_args(add_args):
    """`pytest_add_cli_args` is replayed into the baseline; a non-executing arg there collapses it."""
    for part in add_args or []:
        if part in _NON_EXECUTING:
            return ("refusing `{}` inside mutmut's pytest_add_cli_args: it collects without executing, so "
                    "the baseline would prove nothing and the measured time would make any scope look "
                    "affordable".format(part))
    return None


def baseline_argv(cfg, scope, python=None):
    """The wrapper's baseline = python -m pytest + mutmut's pytest_add_cli_args + the mapped
    selectors: the SAME selection and the SAME non-selection arguments mutmut will use (Q2)."""
    return [python or sys.executable, "-m", "pytest"] + list(cfg.pytest_add_cli_args) + list(scope.tests)


def baseline_share(seconds, max_minutes):
    return float(seconds) / float(max_minutes * 60)


def baseline_dominates(seconds, max_minutes):
    """SS4b: a baseline over a fifth of the budget is the GATE's misconfiguration (selection too
    wide), not the module's size — named as such, before the projection decides affordability."""
    if baseline_share(seconds, max_minutes) > 0.2:
        return ("BASELINE DOMINATES: {:.0f}s of a {}-minute budget goes to the baseline — the GATE is "
                "misconfigured (the scope's test selection is too wide), not the module; narrow the "
                "mapping's tests, do not blame the module and do not defer the measurement".format(
                    seconds, max_minutes))
    return None


def suite_args_migration(value):
    """Q2 (v1.52.0): --suite-args is DEPRECATED outright; this release it only emits this."""
    if not (value or "").strip():
        return None
    return ("--suite-args is deprecated and no longer used ({!r} ignored). Test SELECTION comes from "
            "the scope mapping (.tdd-playbook/mutation-scopes.json, `tests` per scope) and non-selection "
            "pytest options come from mutmut's own `pytest_add_cli_args` (which the baseline replays), "
            "so the wrapper and mutmut cannot run different pytest configurations. The flag is removed "
            "in the next release.".format(value))


_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


def repo_identity(root):
    """Canonical repository identity — root, common git dir, state dir, HEAD — from
    host_contract.resolve_repository, the one owner of that answer (never gate_runner.REPO,
    which is derived from a file location and wrong in a vendored .claude/bin/)."""
    import host_contract
    try:
        return host_contract.resolve_repository(root)
    except Exception as exc:
        raise WorktreeProblem("not a Git checkout ({}): {}".format(root, exc))


def check_clean(root):
    """Q5, LITERAL: any dirty tracked file or any non-ignored untracked file refuses the run.
    Returns None when clean, else the refusal text naming the files."""
    import with_snapshot
    dirty = with_snapshot.dirty_tracked(root)
    untr = with_snapshot.untracked(root)
    if not dirty and not untr:
        return None
    lines = ["the tree is not clean — a mutation run measures a COMMITTED phase boundary; commit the "
             "kill test, then re-measure (a new test that is not committed is absent from the HEAD "
             "checkout and the survivor would report SURVIVED with a clean exit):"]
    lines += ["  - modified (tracked): " + p for p in dirty]
    lines += ["  - untracked (not ignored): " + p for p in untr]
    return "\n".join(lines)


class WorktreeProblem(Exception):
    """The disposable worktree cannot be created or the repository is not usable."""


class CleanupFailed(Exception):
    def __init__(self, path, detail):
        super().__init__("cleanup failed for {}: {}".format(path, detail))
        self.path = path; self.detail = detail


class LockHeld(Exception):
    """Another mutation run holds the repository lock."""


def retained_line(path):
    return "RETAINED: {} — remove with: git worktree remove --force {}".format(path, path)


MARKER_NAME = ".tdd-playbook-mutation-run.json"
LOCK_NAME = ".tdd-playbook-mutation-run.lock"
RETAINED_NAME = ".tdd-playbook-retained.json"
WORKTREES_DIR = "mutation-worktrees"
RUNS_DIR = "mutation-runs"
REPO_LOCK = "mutation.lock"


def _git_run(root, *args, runner=None):
    argv = ["git", "-C", root] + list(args)
    if runner is not None:
        return runner(argv)
    return subprocess.run(argv, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)


def _try_flock(path):
    """(fh or None): a non-blocking exclusive flock on `path`; the FACT of liveness."""
    import fcntl
    fh = open(path, "a+")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return None
    return fh


class Worktree:
    """One disposable, detached worktree per invocation under <common>/tdd-playbook/mutation-worktrees/<run_id>."""
    def __init__(self, ident, run_id, path):
        self.ident = ident; self.run_id = run_id; self.path = path
        self.lock_path = os.path.join(path, LOCK_NAME)
        self._lock_fh = None

    @classmethod
    def create(cls, ident, run_id, scope_name):
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", run_id):
            raise WorktreeProblem("run id must be a single safe path component")
        base = os.path.join(ident["state_dir"], WORKTREES_DIR)
        os.makedirs(base, mode=0o700, exist_ok=True)
        path = os.path.join(base, run_id)
        if os.path.exists(path):
            raise WorktreeProblem("worktree path already exists: {} — a leftover from a crashed run is "
                                  "never reused; inspect it, then `git worktree remove --force {}` "
                                  "(or run with --reap-stale if its lock is free)".format(path, path))
        if not ident.get("head"):
            raise WorktreeProblem("repository has no HEAD commit to check out")
        proc = _git_run(ident["root"], "worktree", "add", "--detach", path, ident["head"])
        if proc.returncode != 0 or not os.path.isdir(path):
            raise WorktreeProblem("git worktree add failed for {}: {}".format(path, (proc.stdout + proc.stderr).strip()[-300:]))
        wt = cls(ident, run_id, path)
        with open(os.path.join(path, MARKER_NAME), "w") as fh:
            json.dump({"run_id": run_id, "scope": scope_name, "head": ident["head"],
                       "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "pid": os.getpid()},
                      fh, indent=1, sort_keys=True)
        wt._lock_fh = _try_flock(wt.lock_path)
        if wt._lock_fh is None:
            raise WorktreeProblem("could not take the per-run lock at {}".format(wt.lock_path))
        return wt

    def release_lock(self):
        if self._lock_fh is not None:
            import fcntl
            try:
                fcntl.flock(self._lock_fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._lock_fh.close(); self._lock_fh = None

    def remove(self, runner=None, force=False):
        """Remove EXACTLY this worktree (never a global prune). Raises CleanupFailed with the
        retained path when git cannot, so the operator inspects rather than loses it."""
        self.release_lock()
        proc = _git_run(self.ident["root"], "worktree", "remove", "--force", self.path, runner=runner)
        if proc.returncode != 0:
            raise CleanupFailed(self.path, (proc.stdout + proc.stderr).strip()[-300:] or "git worktree remove failed")
        if os.path.exists(self.path):
            if force:
                shutil.rmtree(self.path, ignore_errors=True)
            if os.path.exists(self.path):
                raise CleanupFailed(self.path, "directory still present after git worktree remove")


def mark_retained(path, reason):
    """A forensic path: listed separately, never auto-reaped (Q6)."""
    with open(os.path.join(path, RETAINED_NAME), "w") as fh:
        json.dump({"reason": reason, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, fh, indent=1)


class _LockHandle:
    def __init__(self, path):
        self.path = path


@contextlib.contextmanager
def repo_lock(ident, scope_name, run_id):
    """One mutation run per repository (D2b): non-blocking flock on <state>/mutation.lock,
    acquired BEFORE listing or reaping stale worktrees so setup cannot race cleanup (Q6).
    While held, <state>/mutation-runs/in-progress.json names the holder for the refusal."""
    state = ident["state_dir"]
    os.makedirs(state, mode=0o700, exist_ok=True)
    lock_path = os.path.join(state, REPO_LOCK)
    fh = _try_flock(lock_path)
    stub = os.path.join(state, RUNS_DIR, "in-progress.json")
    if fh is None:
        holder = ""
        try:
            with open(stub) as sfh:
                info = json.load(sfh)
            holder = " (scope {!r}, run {}, started {}, pid {})".format(
                info.get("scope"), info.get("run_id"), info.get("started"), info.get("pid"))
        except (OSError, ValueError):
            pass
        raise LockHeld("another mutation run holds {}{} — one run per repository at a time; wait for it "
                       "or, if it is dead, remove the lock file and run again".format(lock_path, holder))
    os.makedirs(os.path.dirname(stub), mode=0o700, exist_ok=True)
    try:
        import host_contract
        host_contract._atomic_json(stub, {"scope": scope_name, "run_id": run_id, "pid": os.getpid(),
                                          "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        yield _LockHandle(lock_path)
    finally:
        try:
            os.unlink(stub)
        except OSError:
            pass
        import fcntl
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()


class _WT:
    def __init__(self, run_id, path, marker):
        self.run_id = run_id; self.path = path; self.marker = marker


class StaleReport:
    def __init__(self):
        self.stale = []; self.live = []; self.foreign = []; self.retained = []


def list_stale(ident):
    """Classify every entry under mutation-worktrees/: ours + lock free = STALE; ours + lock held
    = LIVE; retained marker = RETAINED (never reaped); no marker = FOREIGN (named, left alone).
    Call under repo_lock."""
    report = StaleReport()
    base = os.path.join(ident["state_dir"], WORKTREES_DIR)
    if not os.path.isdir(base):
        return report
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name)
        if not os.path.isdir(path) or os.path.islink(path):
            continue
        marker_path = os.path.join(path, MARKER_NAME)
        if not os.path.isfile(marker_path):
            report.foreign.append(path); continue
        try:
            with open(marker_path) as fh:
                marker = json.load(fh)
        except (OSError, ValueError):
            marker = {}
        entry = _WT(marker.get("run_id", name), path, marker)
        if os.path.isfile(os.path.join(path, RETAINED_NAME)):
            report.retained.append(entry); continue
        fh = _try_flock(os.path.join(path, LOCK_NAME))
        if fh is None:
            report.live.append(entry)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN); fh.close()
            report.stale.append(entry)
    return report


def stale_lines(report):
    lines = []
    for w in report.stale:
        lines.append("stale worktree (ours, lock free): {} — {}".format(
            w.path, retained_line(w.path).split(" — ", 1)[1]) + "  [--reap-stale removes it]")
    for w in report.live:
        lines.append("live worktree (lock held by a running pass): {} — left alone".format(w.path))
    for w in report.retained:
        lines.append("RETAINED forensic worktree: {} — never auto-removed; inspect, then "
                     "git worktree remove --force {}".format(w.path, w.path))
    for p in report.foreign:
        lines.append("foreign directory (no marker of ours): {} — left alone".format(p))
    return "\n".join(lines)


def reap_stale(ident, report):
    """Remove exactly the STALE set (ours, marker-bearing, lock free). Never retained, live or foreign."""
    removed = []
    for w in report.stale:
        proc = _git_run(ident["root"], "worktree", "remove", "--force", w.path)
        if os.path.exists(w.path):
            shutil.rmtree(w.path, ignore_errors=True)
        if not os.path.exists(w.path):
            removed.append(w.path)
    return removed


class AccountingProblem(Exception):
    """The per-mutant accounting cannot be trusted: unknown status, duplicate name, or a
    disagreement between mutmut's two views of the same run (Q7: fail closed)."""


class RecordProblem(Exception):
    """The run record could not be written — a record is a deliverable, not a nicety."""


DECIDED = ("killed", "survived")
UNSCORED = ("no tests", "skipped", "suspicious", "timeout", "segfault", "caught by type check")
UNFINISHED = ("check was interrupted by user", "not checked")
# CI export field per status, for the statuses the export EMITS (it omits not_checked and
# caught_by_type_check — the known residual, never compared)
_EXPORT_FIELD = {"killed": "killed", "survived": "survived", "no tests": "no_tests", "skipped": "skipped",
                 "suspicious": "suspicious", "timeout": "timeout", "segfault": "segfault",
                 "check was interrupted by user": "check_was_interrupted_by_user"}
_RESULT_LINE = re.compile(r"^\s*(\S.*?):\s*(.+?)\s*$")


class Buckets:
    def __init__(self, counts):
        self.counts = dict(counts)
        self.killed = counts.get("killed", 0); self.survived = counts.get("survived", 0)
        self.decided = self.killed + self.survived
        self.unscored = {k: v for k, v in counts.items() if k in UNSCORED and v}
        self.unscored_total = sum(self.unscored.values())
        self.interrupted = counts.get("check was interrupted by user", 0)
        self.not_checked = counts.get("not checked", 0)
        self.unfinished = self.interrupted + self.not_checked
        self.rows = sum(counts.values())
        self.total = self.rows
        self.survivors = []

    def as_dict(self):
        return {"killed": self.killed, "survived": self.survived, "decided": self.decided,
                "unscored": self.unscored, "unscored_total": self.unscored_total,
                "interrupted": self.interrupted, "not_checked": self.not_checked,
                "unfinished": self.unfinished, "rows": self.rows, "total": self.total,
                "survivors": list(self.survivors)}


def classify_results(text):
    """Parse `mutmut results --all=true` — one line per mutant, `<name>: <status>` — into the
    three buckets. Duplicate names are refused BEFORE anything is counted; an unknown status is
    refused rather than bucketed (mutmut's status map is a defaultdict, so a new word means the
    contract moved)."""
    counts = {}
    seen = set()
    survivors = []
    for raw in (text or "").splitlines():
        if not raw.strip():
            continue
        mo = _RESULT_LINE.match(raw)
        if not mo or raw.strip().endswith(":"):
            continue
        name, status = mo.group(1).strip(), mo.group(2).strip()
        if status not in DECIDED + UNSCORED + UNFINISHED:
            raise AccountingProblem("unknown mutant status {!r} for {!r} — mutmut's status vocabulary has "
                                    "changed; refusing to bucket it".format(status, name))
        if name in seen:
            raise AccountingProblem("duplicate mutant name {!r} in results — one duplicated row can conceal "
                                    "one missing row; refusing to count".format(name))
        seen.add(name)
        counts[status] = counts.get(status, 0) + 1
        if status == "survived":
            survivors.append(name)
    b = Buckets(counts)
    b.survivors = survivors
    return b


def reconcile(buckets, export):
    """None when the CI export agrees with the per-mutant rows; else the refusal text (Q7):
    missing/malformed export, a `total` that differs from the row count, or any EMITTED field
    that differs. The export's omitted statuses are the known residual and are not compared."""
    if not isinstance(export, dict):
        return ("CI export (mutants/mutmut-cicd-stats.json) is missing or unreadable — the denominator "
                "cannot be checked; {} rows seen, total UNVERIFIED — refusing".format(buckets.rows))
    if not isinstance(export.get("total"), int):
        return "CI export is malformed (no integer `total`) — {} rows seen, total UNVERIFIED — refusing".format(buckets.rows)
    if export["total"] != buckets.rows:
        return ("mutant accounting DISAGREES: results list {} mutants, the CI export's total is {} — "
                "refusing rather than picking one".format(buckets.rows, export["total"]))
    for status, field in _EXPORT_FIELD.items():
        if field in export and isinstance(export[field], int) and export[field] != buckets.counts.get(status, 0):
            return ("mutant accounting DISAGREES on {!r}: results say {}, the CI export says {} (total {}) — "
                    "refusing".format(status, buckets.counts.get(status, 0), export[field], export["total"]))
    return None


def certify_problem(buckets):
    """A COMPLETE run may certify only when every mutant was scored (SS4a's
    `killed + survived < generated` rule, mechanical)."""
    if buckets.unfinished:
        return "{} mutant(s) unfinished — not a complete run; cannot certify".format(buckets.unfinished)
    if buckets.unscored_total:
        return ("{} mutant(s) terminal but UNSCORED ({}) — killed + survived < generated; refusing to "
                "certify (segfault/timeout/no-tests are not kills)".format(
                    buckets.unscored_total, ", ".join("{} {}".format(v, k) for k, v in sorted(buckets.unscored.items()))))
    return None


def _rate(b):
    return (100.0 * b.killed / b.decided) if b.decided else 0.0


def partial_line(b):
    return ("PARTIAL — kill rate {}/{} = {:.0f}% over {} decided, {} unscored, {} unfinished at cutoff "
            "({} interrupted mid-check, {} not yet checked) — NON-AUTHORIZING".format(
                b.killed, b.decided, _rate(b), b.decided, b.unscored_total, b.unfinished, b.interrupted, b.not_checked))


def score_line(b):
    return ("Mutation: {}/{} killed = {:.0f}% (raw over decided) · {} survived · {} unscored · {} unfinished · "
            "{} total".format(b.killed, b.decided, _rate(b), b.survived, b.unscored_total, b.unfinished, b.total))


def account(worktree_dir, python=None):
    """(buckets, export, problem) read from the worktree after the pass (complete OR cut off):
    `mutmut results --all=true` is the one per-mutant source; `mutmut export-cicd-stats` is the
    denominator cross-check. Never raises on a disagreement — returns it, so the record is still
    written; the CALLER refuses."""
    py = python or sys.executable
    res = subprocess.run([py, "-m", "mutmut", "results", "--all=true"], cwd=worktree_dir,
                         capture_output=True, text=True, timeout=600, stdin=subprocess.DEVNULL)
    if res.returncode != 0:
        return None, None, "mutmut results failed ({}): {}".format(res.returncode, (res.stdout + res.stderr)[-300:])
    try:
        buckets = classify_results(res.stdout)
    except AccountingProblem as exc:
        return None, None, str(exc)
    subprocess.run([py, "-m", "mutmut", "export-cicd-stats"], cwd=worktree_dir,
                   capture_output=True, text=True, timeout=600, stdin=subprocess.DEVNULL)
    export = None
    try:
        with open(os.path.join(worktree_dir, "mutants", "mutmut-cicd-stats.json")) as fh:
            export = json.load(fh)
    except (OSError, ValueError):
        export = None
    return buckets, export, reconcile(buckets, export)


def write_record(ident, run_id, payload):
    """<state>/mutation-runs/<run_id>/index.json — 0600, atomic, retention shared with gate runs
    via gate_runner.prune_dir (keep 20, own lock in this directory)."""
    import host_contract
    runs = os.path.join(ident["state_dir"], RUNS_DIR)
    rec_dir = os.path.join(runs, run_id)
    try:
        os.makedirs(rec_dir, mode=0o700, exist_ok=True)
        record = dict(payload)
        record.setdefault("run_id", run_id)
        record["written_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        path = os.path.join(rec_dir, "index.json")
        host_contract._atomic_json(path, record)
        os.utime(rec_dir, None)
    except OSError as exc:
        raise RecordProblem("could not write the run record under {}: {}".format(runs, exc))
    try:
        import gate_runner
        gate_runner.prune_dir(runs, keep=20, lock_name=".prune.lock", protect=rec_dir)
    except Exception as exc:          # retention must never lose the record just written
        print("mutation_run: record retention skipped ({})".format(exc), file=sys.stderr)
    return path


def latest_record(ident):
    runs = os.path.join(ident["state_dir"], RUNS_DIR)
    if not os.path.isdir(runs):
        return None
    best = None
    for name in os.listdir(runs):
        p = os.path.join(runs, name, "index.json")
        if os.path.isfile(p):
            key = (os.stat(p).st_mtime_ns, name)
            if best is None or key > best[0]:
                best = (key, p)
    if best is None:
        return None
    try:
        with open(best[1]) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def mutmut_argv(max_children=None):
    """The REAL mutmut 3.x contract, verified against the installed binary: `python -m mutmut run`,
    with scope and runner coming from config. Accepted flags are --all/--max-children/--rootdir/
    --show-killed/--tb; anything else is a 2.x memory."""
    # v1.52.2: THROUGH the interpreter, never a bare PATH lookup. The origin repo's first real
    # scoped run (2026-09-09) launched Homebrew's `mutmut` from PATH while the config probe, the
    # collection, the baseline and the accounting all ran under the repo's .venv python — 290
    # mutants generated (the narrowing worked), every one of them unfinished.
    argv = [sys.executable, "-m", "mutmut", "run"]
    if max_children:
        argv += ["--max-children", str(max_children)]
    return argv


def main(argv=None, run=None, config_reader=None):
    parser = argparse.ArgumentParser(
        prog="mutation_run.py",
        description=("Run a SCOPED mutation pass (SS4b): both halves narrowed per run — the mutants to the "
                     "scope's sources and the baseline to the scope's tests — inside a disposable "
                     "detached worktree, with the preflight ON the execution path. --scope names an entry "
                     "in the repo-owned .tdd-playbook/mutation-scopes.json (the mutation roster). "
                     "pytest + mutmut ONLY; other stacks are refused, never guessed."))
    parser.add_argument("--scope", required=True, help="scope name from .tdd-playbook/mutation-scopes.json")
    parser.add_argument("--suite-args", default="",
                        help="DEPRECATED (v1.52.0): selection comes from the scope mapping, options from "
                             "mutmut's pytest_add_cli_args; any value is refused with the migration note")
    parser.add_argument("--max-minutes", type=int, default=None)
    parser.add_argument("--baseline-timeout", type=int, default=None,
                        help="bound for the CHEAP baseline (default: a fifth of --max-minutes)")
    parser.add_argument("--expected-mutants", type=int, default=None,
                        help="enables the projection; without it the hard bound still applies")
    parser.add_argument("--factor", type=float, default=1.0)
    parser.add_argument("--max-children", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="validate everything (mapping, config, worktree, baseline) and stop")
    parser.add_argument("--reap-stale", action="store_true",
                        help="remove OUR marker-bearing worktrees whose per-run lock is free (default: list only)")
    args = parser.parse_args(argv)

    problem = suite_args_migration(args.suite_args)
    if problem:
        print("mutation_run: REFUSED — " + problem, file=sys.stderr)
        return 1
    if args.max_minutes is None:
        print("mutation_run: --max-minutes is REQUIRED. An unbounded pass is how a run times "
              "out at 1800s having measured nothing.", file=sys.stderr)
        return 1

    root = os.getcwd()
    try:
        ident = repo_identity(root)
    except WorktreeProblem as exc:
        print("mutation_run: REFUSED — " + str(exc), file=sys.stderr)
        return 1
    try:
        cfg = (config_reader or effective_mutmut_config)(root)
    except ConfigProblem as exc:
        print("mutation_run: REFUSED — " + str(exc), file=sys.stderr)
        return 1
    problem = forbidden_add_args(cfg.pytest_add_cli_args)
    if problem:
        print("mutation_run: REFUSED — " + problem, file=sys.stderr)
        return 1
    try:
        scope = resolve_scope(ident["root"], args.scope, cfg)
    except ScopeError as exc:
        print("mutation_run: REFUSED — " + str(exc), file=sys.stderr)
        return 1
    print("mutation_run: scope {}: {} source(s) {} → {} selector(s) {} · cost: {!r}".format(
        scope.name, scope.source_count, scope.sources, scope.test_count, scope.tests, scope.cost))
    unclean = check_clean(ident["root"])
    if unclean:
        print("mutation_run: REFUSED — " + unclean, file=sys.stderr)
        return 1

    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + scope.name[:24] + "-" + str(os.getpid())
    try:
        with repo_lock(ident, scope.name, run_id):
            report = list_stale(ident)
            listing = stale_lines(report)
            if listing:
                print("mutation_run: " + listing.replace("\n", "\nmutation_run: "))
            if args.reap_stale:
                for path in reap_stale(ident, report):
                    print("mutation_run: reaped stale worktree " + path)
            try:
                wt = Worktree.create(ident, run_id, scope.name)
            except WorktreeProblem as exc:
                print("mutation_run: REFUSED — " + str(exc), file=sys.stderr)
                return 1
            print("mutation_run: disposable worktree {} (detached at {})".format(wt.path, ident["head"][:12]))
            rc = 1
            payload = {"scope": scope.name, "sources": scope.sources, "tests": scope.tests,
                       "cost": scope.cost, "source_count": scope.source_count, "test_count": scope.test_count,
                       "mapping_sha256": scope.mapping_sha256, "head": ident["head"], "worktree": wt.path,
                       "budget_minutes": args.max_minutes, "pytest_add_cli_args": cfg.pytest_add_cli_args,
                       "config_file": cfg.config_file, "exit_reason": "refused-before-run"}
            try:
                rc = _run_in_worktree(args, ident, cfg, scope, wt, payload, run=run, config_reader=config_reader)
            finally:
                try:
                    write_record(ident, run_id, payload)
                    print("mutation_run: record written ({})".format(os.path.join(RUNS_DIR, run_id, "index.json")))
                except RecordProblem as exc:
                    print("mutation_run: " + str(exc), file=sys.stderr)
                    rc = 1
                try:
                    wt.remove()
                    print("mutation_run: worktree removed")
                except CleanupFailed as exc:
                    mark_retained(exc.path, exc.detail)
                    print("mutation_run: cleanup FAILED ({}); the worktree is retained for inspection".format(exc.detail), file=sys.stderr)
                    print(retained_line(exc.path), file=sys.stderr)
                    rc = 1
            return rc
    except LockHeld as exc:
        print("mutation_run: REFUSED — " + str(exc), file=sys.stderr)
        return 1


def _run_in_worktree(args, ident, cfg, scope, wt, payload, run=None, config_reader=None):
    """Both halves, inside the worktree: narrow the copy's config (read back), count the mapped
    selection, run the baseline with pytest_add_cli_args replayed, project, then mutmut."""
    try:
        rep = narrow_config(wt.path, cfg, scope, real_dir=ident["root"], reader=config_reader)
    except ConfigProblem as exc:
        print("mutation_run: REFUSED — " + str(exc), file=sys.stderr)
        return 1
    print("mutation_run: worktree config ({}): only_mutate={!r} selection={!r} pytest_add_cli_args={!r} · {} · "
          "real config untouched (sha256 {})".format(rep.config_file, scope.sources, scope.tests,
                                                     cfg.pytest_add_cli_args, "; ".join(rep.notes), rep.real_sha256[:12]))
    payload["config_notes"] = rep.notes; payload["real_config_sha256"] = rep.real_sha256
    if run is None:
        n, problem = collect_selection(wt.path, scope.tests, cfg.pytest_add_cli_args)
        if problem:
            print("mutation_run: REFUSED — " + problem, file=sys.stderr)
            return 1
        print("mutation_run: {} test(s) collected by the mapped selection".format(n))

    bound = args.baseline_timeout or max(60, (args.max_minutes * 60) // 5)
    ok, why, seconds, collected = baseline(baseline_argv(cfg, scope), run=run, timeout=bound, cwd=wt.path)
    if not ok:
        print("mutation_run: REFUSED — " + why, file=sys.stderr)
        return 1
    print("mutation_run: baseline GREEN — {} collected, {:.1f}s measured (share of budget {:.0%})".format(
        collected, seconds, baseline_share(seconds, args.max_minutes)))
    payload["baseline_s"] = round(seconds, 3); payload["baseline_share"] = round(baseline_share(seconds, args.max_minutes), 4)
    payload["baseline_collected"] = collected
    dominates = baseline_dominates(seconds, args.max_minutes)
    if dominates:
        print("mutation_run: " + dominates)

    if args.expected_mutants is not None:
        proj = projection_problem(args.expected_mutants, seconds, args.max_minutes, args.factor)
        if proj:
            print("mutation_run: REFUSED — " + proj, file=sys.stderr)
            return 1
    else:
        print("mutation_run: projection SKIPPED (no --expected-mutants) — unmeasured, not "
              "assumed affordable; the {}-minute hard bound still applies".format(args.max_minutes))
    if args.dry_run:
        print("mutation_run: --dry-run — everything validated, mutmut not invoked")
        payload["exit_reason"] = "dry-run"
        return 0

    mut = mutmut_argv(args.max_children)
    print("mutation_run: invoking " + " ".join(mut) + " in the worktree (only_mutate={!r})".format(scope.sources))
    try:
        proc = run_bounded(mut, args.max_minutes * 60, run=run, cwd=wt.path)
    except subprocess.TimeoutExpired:      # only the injected hook can still raise this
        print("mutation_run: mutation pass exceeded {} minutes — UNMEASURED".format(args.max_minutes), file=sys.stderr)
        return 1
    except OSError as exc:
        print("mutation_run: mutmut could not be run ({}) — refusing rather than reporting a "
              "score nothing produced".format(exc), file=sys.stderr)
        return 1
    sys.stdout.write(proc.stdout or "")
    timed_out = bool(getattr(proc, "timed_out", False))
    payload["mutmut_exit"] = proc.returncode; payload["elapsed_s"] = round(getattr(proc, "elapsed_s", 0.0), 1)
    if run is not None:                       # injected hook: no real tool to account against
        payload["exit_reason"] = "timeout" if timed_out else "complete"
        payload["buckets"] = None
        return 1 if timed_out else proc.returncode
    buckets, export, problem = account(wt.path)
    payload["buckets"] = buckets.as_dict() if buckets else None
    payload["export"] = export
    if problem:
        payload["exit_reason"] = "accounting-refused"
        print("mutation_run: REFUSED — " + problem, file=sys.stderr)
        return 1
    if timed_out:
        payload["exit_reason"] = "timeout"
        print("mutation_run: mutation pass hit the {}-minute deadline (SIGINT at deadline-30s, SIGKILL at the "
              "deadline; {:.0f}s)".format(args.max_minutes, proc.elapsed_s), file=sys.stderr)
        print("mutation_run: " + partial_line(buckets))
        for name in buckets.survivors:
            print("mutation_run:   survived: " + name)
        return 1
    payload["exit_reason"] = "complete"
    print("mutation_run: " + score_line(buckets))
    for name in buckets.survivors:
        print("mutation_run:   survived: " + name)
    cert = certify_problem(buckets)
    if cert:
        payload["exit_reason"] = "complete-uncertified"
        print("mutation_run: REFUSED to certify — " + cert, file=sys.stderr)
        return 1
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
