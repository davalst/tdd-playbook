#!/usr/bin/env python3
"""Planted-input calibration for bin/dataflow_sweeps.py — the §6c Tier-1 reference sweeps.

Every mechanical claim the tool makes is proven able to go RED here, each plant with a
paired clean control (v1.17 pair quota). The contract under test:
  render-pairing   Tier 1, blocking. Literal str.format/.format_map call sites (same-file
                   decidable, incl. module-level string constants) + config-mapped
                   template↔supplier pairs. BOTH directions, reported distinctly:
                   placeholder-with-no-supplier (broken render) and
                   supplied-key-with-no-placeholder (silently dropped value — the T5 escape).
  ghost-gates      Tier 2, ADVISORY by default (findings printed, exit 0); --strict flips
                   blocking. Undeclared getattr/.get gate reads vs a declared-fields source.
  exemption-prose  Tier 1. Default-claims ("always-on") checked against the artifact of
                   record; missing artifact/capability fails CLOSED.
  Common           summary `checked N · violations N · exempted N · unresolvable N`;
                   exemptions use the house debt shape {what, target, owner, expires} —
                   EXPIRED REDs the sweep (`--as-of` provable, string-pinned); an exemption
                   naming a `user_facing` registry capability FAILS (§6a companion rule,
                   keyed on the fact, not a proxy); exit 0 clean / 1 violation / 2 usage
                   ONLY / 3 vacuous-refusal ("refusing a vacuous pass").
Self-contained, no pytest. Run: python3 tests/test_dataflow_sweeps.py
"""
import contextlib
import io
import json
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "bin", "dataflow_sweeps.py")

_results = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _results["pass"] += 1
        print("  ok   - {}".format(name))
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def load_tool():
    import importlib.util
    spec = importlib.util.spec_from_file_location("dataflow_sweeps", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = None


def run(argv):
    """Run the tool in-process; return (rc, combined stdout+stderr text).

    An unhandled exception maps to rc -1 (recorded as a failing check, never a crashed
    suite) — a tool that RAISES on bad config instead of returning usage-2 is itself
    the script-adversary F6 defect, and the suite must survive to report it."""
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            rc = MOD.main(argv)
    except SystemExit as e:  # argparse usage errors
        rc = e.code if isinstance(e.code, int) else 2
    except Exception as e:  # noqa: BLE001 — the defect under test, surfaced not fatal
        out.write("UNHANDLED {}: {}\n".format(type(e).__name__, e))
        rc = -1
    return rc, out.getvalue()


def write(base, rel, text):
    path = os.path.join(base, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)
    return path


def cfg(base, body):
    return write(base, "sweeps.json", json.dumps(body))


SUMMARY_RX = re.compile(
    r"dataflow_sweeps (render-pairing|ghost-gates|exemption-prose): "
    r"checked \d+ · violations \d+ · exempted \d+ · unresolvable \d+")


# ------------------------------------------------------------------ render-pairing
def test_render_pairing():
    with tempfile.TemporaryDirectory() as td:
        # PLANT: supplied key with no placeholder (T5 — silently dropped value)
        write(td, "src/surplus.py", 'MSG = "hello {name}"\nX = MSG.format(name="a", layer="b")\n')
        # PLANT: placeholder with no supplier (broken render)
        write(td, "src/missing.py", 'Y = "hi {name} {age}".format(name="a")\n')
        # CONTROL: exact pairing, incl. attribute/index roots and escaped braces
        write(td, "src/clean.py",
              'Z = "{{lit}} {a.b} {c[0]} {k}".format(a=1, c=[1], k=2)\n')
        c = cfg(td, {"render_pairing": {"scan": ["src"]}})
        rc, out = run(["render-pairing", "--config", c])
        check("render: violations found -> exit 1", rc == 1, (rc, out))
        check("render: surplus key reported as its own direction",
              "no placeholder" in out and "layer" in out, out)
        check("render: missing supplier reported as its own direction",
              "no supplier" in out and "age" in out, out)
        check("render: clean file not flagged", "clean.py" not in out, out)
        check("render: summary line pinned", SUMMARY_RX.search(out) is not None, out)

    with tempfile.TemporaryDirectory() as td:
        # CONTROL: a fully clean scan passes
        write(td, "src/clean.py", 'Z = "{k}".format(k=2)\n')
        c = cfg(td, {"render_pairing": {"scan": ["src"]}})
        rc, out = run(["render-pairing", "--config", c])
        check("render: paired clean control -> exit 0", rc == 0, (rc, out))

    with tempfile.TemporaryDirectory() as td:
        # positional surplus is a violation; f-strings and % are out of scope (stated)
        write(td, "src/pos.py", 'A = "{}".format(1, 2)\n')
        write(td, "src/fstr.py", 'B = f"{undefined_is_fine}"\nC = "%s" % (1,)\n')
        c = cfg(td, {"render_pairing": {"scan": ["src"]}})
        rc, out = run(["render-pairing", "--config", c])
        check("render: positional surplus -> violation", rc == 1, (rc, out))
        check("render: f-string/percent sites not treated as violations",
              "fstr.py" not in out, out)

    with tempfile.TemporaryDirectory() as td:
        # **kwargs is UNRESOLVABLE — counted, never a silent pass, never a violation
        write(td, "src/dyn.py", 'D = "{x}".format(**{"x": 1})\n')
        c = cfg(td, {"render_pairing": {"scan": ["src"]}})
        rc, out = run(["render-pairing", "--config", c])
        check("render: **kwargs counted unresolvable, not a violation",
              rc == 0 and "unresolvable 1" in out, (rc, out))

    with tempfile.TemporaryDirectory() as td:
        # cross-file template pair: template placeholder set vs supplier's supplied keys
        write(td, "tpl.txt", "Dear {name}, balance {balance}.")
        write(td, "sup.py", 'body = open("tpl.txt").read().format(name=n)\n')
        c = cfg(td, {"render_pairing": {
            "scan": [], "template_pairs": [{"template": "tpl.txt", "supplier": "sup.py"}]}})
        rc, out = run(["render-pairing", "--config", c])
        check("render: template pair missing supplier key -> violation",
              rc == 1 and "balance" in out, (rc, out))
        # CONTROL: fully supplied pair passes
        write(td, "sup2.py", 'body = T.format(name=n, balance=b)\n')
        c2 = cfg(td, {"render_pairing": {
            "scan": [], "template_pairs": [{"template": "tpl.txt", "supplier": "sup2.py"}]}})
        rc2, out2 = run(["render-pairing", "--config", c2])
        check("render: template pair control -> exit 0", rc2 == 0, (rc2, out2))

    with tempfile.TemporaryDirectory() as td:
        # mutation-runner M7 kill: the CROSS-FILE surplus direction (the T5 escape on the
        # seam downstream repos configure) — supplier supplies a key no placeholder takes
        write(td, "tpl.txt", "Dear {name}.")
        write(td, "sup.py", 'body = T.format(name=n, balance=b)\n')
        c = cfg(td, {"render_pairing": {
            "scan": [], "template_pairs": [{"template": "tpl.txt", "supplier": "sup.py"}]}})
        rc, out = run(["render-pairing", "--config", c])
        check("render: template pair SURPLUS supplied key -> T5 violation",
              rc == 1 and "balance" in out and "no placeholder" in out, (rc, out))


def test_duplicate_exemption_targets():
    """mutation-runner M9 kill + hardening: the expired-exemption teeth must never be
    silenceable by appending a fresh duplicate entry for the same target."""
    with tempfile.TemporaryDirectory() as td:
        write(td, "src/surplus.py", 'X = "hi {a}".format(a=1, ghost=2)\n')
        c = cfg(td, {"render_pairing": {"scan": ["src"], "exemptions": [
            {"what": "stale", "target": "src/surplus.py::ghost", "owner": "david",
             "expires": "2026-01-01"},
            {"what": "fresh duplicate", "target": "src/surplus.py::ghost",
             "owner": "david", "expires": "2027-01-01"}]}})
        rc, out = run(["render-pairing", "--config", c, "--as-of", "2026-08-03"])
        check("exemption: a clean duplicate cannot suppress its EXPIRED twin",
              rc == 1 and "EXPIRED" in out, (rc, out))
        check("exemption: duplicate targets are themselves rejected (fail closed)",
              "duplicate" in out, out)


# ------------------------------------------------------------------ exit codes + vacuity
def test_exit_codes_and_vacuity():
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "empty"))
        c = cfg(td, {"render_pairing": {"scan": ["empty"]}})
        rc, out = run(["render-pairing", "--config", c])
        check("vacuity: zero call sites -> exit 3, distinct from usage",
              rc == 3, (rc, out))
        check("vacuity: refusal string present", "refusing a vacuous pass" in out, out)

    rc, out = run(["no-such-subcommand"])
    check("usage: bad subcommand -> exit 2 (usage, never proof)", rc == 2, (rc, out))

    with tempfile.TemporaryDirectory() as td:
        write(td, "src/x.py", 'A = "{k}".format(k=1)\n')
        c = cfg(td, {"render_pairing": {"scan": ["src"]}})
        rc, out = run(["render-pairing", "--config", c, "--as-of", "not-a-date"])
        check("usage: garbage --as-of -> exit 2, distinct from vacuity's 3",
              rc == 2, (rc, out))
    rc, out = run(["render-pairing", "--config", "/nonexistent/sweeps.json"])
    check("usage: missing config -> exit 2", rc == 2, (rc, out))


# ------------------------------------------------------------------ exemptions
def test_exemptions():
    def base(td, exemptions, registry=None):
        write(td, "src/surplus.py", 'X = "hi {a}".format(a=1, ghost=2)\n')
        body = {"render_pairing": {"scan": ["src"], "exemptions": exemptions}}
        if registry:
            body["registry"] = "capabilities.json"
            write(td, "capabilities.json", json.dumps(registry))
        return cfg(td, body)

    ex = {"what": "dynamic layer key, reader ships 2026-09",
          "target": "src/surplus.py::ghost", "owner": "david", "expires": "2026-09-15"}

    with tempfile.TemporaryDirectory() as td:
        c = base(td, [ex])
        rc, out = run(["render-pairing", "--config", c, "--as-of", "2026-09-15"])
        check("exemption: live exemption suppresses -> exit 0, counted",
              rc == 0 and "exempted 1" in out, (rc, out))
        rc, out = run(["render-pairing", "--config", c, "--as-of", "2026-09-16"])
        check("exemption: EXPIRED at expiry+1 -> exit 1", rc == 1, (rc, out))
        check("exemption: expiry violation NAMES the exemption (never a bare exit code)",
              "EXPIRED" in out and "src/surplus.py::ghost" in out, out)

    with tempfile.TemporaryDirectory() as td:
        # §6a companion rule: an exemption naming a user_facing capability FAILS
        reg = {"version": 1, "capabilities": [
            {"id": "user-thing", "summary": "s", "surfaces": ["local"],
             "activation": {"default": "on"}, "wired_by": ["w"], "exercised_by": ["e"],
             "user_facing": True}]}
        c = base(td, [dict(ex, capability="user-thing")], registry=reg)
        rc, out = run(["render-pairing", "--config", c, "--as-of", "2026-09-01"])
        check("companion: user-facing exemption -> FAIL even before expiry",
              rc == 1 and "user_facing" in out, (rc, out))
        # CONTROL: same exemption on an internal capability stays legal
        reg2 = {"version": 1, "capabilities": [
            {"id": "internal-thing", "summary": "s", "surfaces": ["local"],
             "activation": {"default": "on"}, "wired_by": ["w"], "exercised_by": ["e"],
             "user_facing": False}]}
        c2 = base(td, [dict(ex, capability="internal-thing")], registry=reg2)
        rc2, out2 = run(["render-pairing", "--config", c2, "--as-of", "2026-09-01"])
        check("companion: internal exemption control -> exit 0", rc2 == 0, (rc2, out2))
        # fail CLOSED: exemption naming a capability absent from the registry
        c3 = base(td, [dict(ex, capability="no-such-cap")], registry=reg2)
        rc3, out3 = run(["render-pairing", "--config", c3, "--as-of", "2026-09-01"])
        check("companion: unknown capability fails closed", rc3 == 1, (rc3, out3))

    with tempfile.TemporaryDirectory() as td:
        # malformed exemption (missing owner) is a violation, not a silent skip
        bad = {"what": "w", "target": "src/surplus.py::ghost", "expires": "2026-09-15"}
        c = base(td, [bad])
        rc, out = run(["render-pairing", "--config", c, "--as-of", "2026-09-01"])
        check("exemption: missing debt field -> violation (house shape enforced)",
              rc == 1 and "owner" in out, (rc, out))


# ------------------------------------------------------------------ ghost-gates
def test_ghost_gates():
    with tempfile.TemporaryDirectory() as td:
        # PLANT: undeclared default-True gate (invisible AND live -> higher severity)
        write(td, "src/ghost.py", 'v = getattr(cfg, "x_enabled", True)\n'
                                  'w = opts.get("y_mode", "fast")\n')
        # declared-fields source declares neither
        write(td, "src/declared.py", "class Config:\n    z_enabled = False\n")
        c = cfg(td, {"ghost_gates": {"scan": ["src"],
                                     "gate_patterns": ["*_enabled", "*_mode"],
                                     "declared_fields": {"kind": "module",
                                                         "path": "src/declared.py"}}})
        rc, out = run(["ghost-gates", "--config", c])
        check("ghost: ADVISORY by default -> findings printed, exit 0",
              rc == 0 and "x_enabled" in out and "y_mode" in out, (rc, out))
        check("ghost: tier stated in output", "Tier 2" in out, out)
        check("ghost: default-True ghost flagged at higher severity",
              "HIGH" in out and "x_enabled" in out, out)
        rc, out = run(["ghost-gates", "--config", c, "--strict"])
        check("ghost: --strict flips blocking -> exit 1", rc == 1, (rc, out))

        # CONTROL: declared twin is clean in BOTH modes
        write(td, "src/ghost.py", 'v = getattr(cfg, "z_enabled", False)\n')
        rc, out = run(["ghost-gates", "--config", c])
        rc2, out2 = run(["ghost-gates", "--config", c, "--strict"])
        check("ghost: declared twin clean in both modes",
              rc == 0 and rc2 == 0 and "violations 0" in out2, (rc, rc2, out2))

    with tempfile.TemporaryDirectory() as td:
        # dynamic attribute name -> UNRESOLVABLE count, never a silent pass
        write(td, "src/dyn.py", "v = getattr(cfg, name, True)\n")
        write(td, "src/declared.py", "class Config:\n    a_enabled = True\n")
        c = cfg(td, {"ghost_gates": {"scan": ["src"], "gate_patterns": ["*_enabled"],
                                     "declared_fields": {"kind": "module",
                                                         "path": "src/declared.py"}}})
        rc, out = run(["ghost-gates", "--config", c])
        check("ghost: dynamic name counted unresolvable",
              "unresolvable 1" in out, (rc, out))

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "empty"))
        write(td, "declared.py", "class Config:\n    a_enabled = True\n")
        c = cfg(td, {"ghost_gates": {"scan": ["empty"], "gate_patterns": ["*_enabled"],
                                     "declared_fields": {"kind": "module",
                                                         "path": "declared.py"}}})
        rc, out = run(["ghost-gates", "--config", c])
        check("ghost: zero sites -> vacuous refusal exit 3",
              rc == 3 and "refusing a vacuous pass" in out, (rc, out))


# ------------------------------------------------------------------ exemption-prose
def test_exemption_prose():
    reg = {"version": 1, "capabilities": [
        {"id": "gated-thing", "summary": "s", "surfaces": ["local"],
         "activation": {"default": "off", "switch": "flip it"},
         "wired_by": ["w"], "exercised_by": ["e"]}]}

    with tempfile.TemporaryDirectory() as td:
        # PLANT: prose claims always-on over a default-off artifact
        write(td, "capabilities.json", json.dumps(reg))
        c = cfg(td, {"exemption_prose": {"claims": [
            {"what": "ignore-list says always-on", "claim": "always-on",
             "artifact": "capabilities.json", "capability": "gated-thing"}]}})
        rc, out = run(["exemption-prose", "--config", c])
        check("prose: always-on claim over default-off -> exit 1",
              rc == 1 and "gated-thing" in out, (rc, out))
        # CONTROL: claim matching the artifact passes
        reg_on = {"version": 1, "capabilities": [
            dict(reg["capabilities"][0], activation={"default": "on"})]}
        write(td, "capabilities.json", json.dumps(reg_on))
        rc2, out2 = run(["exemption-prose", "--config", c])
        check("prose: matching claim control -> exit 0", rc2 == 0, (rc2, out2))

    with tempfile.TemporaryDirectory() as td:
        # fail CLOSED: referenced artifact missing -> RED, never a skip
        c = cfg(td, {"exemption_prose": {"claims": [
            {"what": "w", "claim": "always-on",
             "artifact": "gone.json", "capability": "x"}]}})
        rc, out = run(["exemption-prose", "--config", c])
        check("prose: missing artifact fails closed", rc == 1, (rc, out))

    with tempfile.TemporaryDirectory() as td:
        # generic named-config form: dotted key path into a JSON artifact
        write(td, "settings.json", json.dumps({"features": {"x": {"default": "off"}}}))
        c = cfg(td, {"exemption_prose": {"claims": [
            {"what": "doc claims on-by-default", "claim": "on-by-default",
             "artifact": "settings.json", "key_path": "features.x.default",
             "expected": "on"}]}})
        rc, out = run(["exemption-prose", "--config", c])
        check("prose: key-path mismatch -> exit 1", rc == 1, (rc, out))

    with tempfile.TemporaryDirectory() as td:
        c = cfg(td, {"exemption_prose": {"claims": []}})
        rc, out = run(["exemption-prose", "--config", c])
        check("prose: zero claims -> vacuous refusal exit 3",
              rc == 3 and "refusing a vacuous pass" in out, (rc, out))


# ------------------------------------------------------------------ summary contract
def test_summary_format():
    """A consumer parses the summary (the D13b rollup) — the format is pinned, and it is
    emitted on EVERY outcome class (clean, violation, advisory)."""
    with tempfile.TemporaryDirectory() as td:
        write(td, "src/clean.py", 'Z = "{k}".format(k=2)\n')
        c = cfg(td, {"render_pairing": {"scan": ["src"]}})
        rc, out = run(["render-pairing", "--config", c])
        check("summary: emitted on a clean pass", SUMMARY_RX.search(out) is not None, out)
        check("summary: checked count is real (1 site)", "checked 1" in out, out)

    with tempfile.TemporaryDirectory() as td:
        write(td, "src/ghost.py", 'v = getattr(cfg, "x_enabled", True)\n')
        write(td, "src/declared.py", "class Config:\n    z_enabled = False\n")
        c = cfg(td, {"ghost_gates": {"scan": ["src"], "gate_patterns": ["*_enabled"],
                                     "declared_fields": {"kind": "module",
                                                         "path": "src/declared.py"}}})
        rc, out = run(["ghost-gates", "--config", c])
        check("summary: advisory run still emits the parsable line",
              SUMMARY_RX.search(out) is not None and "violations 1" in out, out)


# ------------------------------------------------------------------ adversary-found modes (v1.24 fold)
def test_fail_closed_scan():
    """script-adversary F1 / arch-adversary F1 (both top recommendations): a scan whose
    files all fail to parse/open must NEVER read as green — unreadable code is a
    VIOLATION (fail closed), and vacuity is keyed on CHECKED alone (an unresolvable
    site cannot vouch for the scan)."""
    with tempfile.TemporaryDirectory() as td:
        # PLANT: the only scanned file has a SyntaxError — the strongest evidence the
        # scanner read nothing must fail the gate, not pass it
        write(td, "src/broken.py", "def broken(:\n")
        c = cfg(td, {"render_pairing": {"scan": ["src"]}})
        rc, out = run(["render-pairing", "--config", c])
        check("fail-closed: unparsable scanned file -> exit 1, violation names the file",
              rc == 1 and "broken.py" in out and "fail closed" in out, (rc, out))
        # CONTROL: the same scan with a parsable file is clean
        write(td, "src/broken.py", 'Z = "{k}".format(k=2)\n')
        rc2, out2 = run(["render-pairing", "--config", c])
        check("fail-closed: parsable control -> exit 0", rc2 == 0, (rc2, out2))

    with tempfile.TemporaryDirectory() as td:
        # dynamic-only ghost scan: checked 0 -> vacuous refusal (unresolvable never
        # converts a zero-checked scan into a pass)
        write(td, "src/dyn.py", "v = getattr(cfg, name, True)\n")
        write(td, "src/declared.py", "class Config:\n    a_enabled = True\n")
        c = cfg(td, {"ghost_gates": {"scan": ["src"], "gate_patterns": ["*_enabled"],
                                     "declared_fields": {"kind": "module",
                                                         "path": "src/declared.py"}}})
        rc, out = run(["ghost-gates", "--config", c])
        check("fail-closed: zero-checked all-unresolvable scan -> vacuous refusal 3",
              rc == 3 and "unresolvable 1" in out
              and "refusing a vacuous pass" in out, (rc, out))


def test_template_pair_earns_checked():
    """script-adversary F2: a template_pairs entry earns `checked` only by DOING work —
    a nothing-to-pair entry must not convert a vacuous config into a green one."""
    with tempfile.TemporaryDirectory() as td:
        # PLANT: placeholder-free template + inert supplier — manufactured coverage
        write(td, "tpl.txt", "This file has no placeholders.")
        write(td, "sup.py", "x = 1\n")
        c = cfg(td, {"render_pairing": {
            "scan": [], "template_pairs": [{"template": "tpl.txt", "supplier": "sup.py"}]}})
        rc, out = run(["render-pairing", "--config", c])
        check("pair: nothing-to-pair entry -> violation, not manufactured coverage",
              rc == 1 and "nothing to pair" in out, (rc, out))
        # CONTROL: a real pair still passes
        write(td, "tpl2.txt", "Dear {name}.")
        write(td, "sup2.py", 'b = T.format(name=n)\n')
        c2 = cfg(td, {"render_pairing": {
            "scan": [], "template_pairs": [{"template": "tpl2.txt", "supplier": "sup2.py"}]}})
        rc2, out2 = run(["render-pairing", "--config", c2])
        check("pair: real pair control -> exit 0", rc2 == 0, (rc2, out2))


def test_prose_vocabulary_closed():
    """script-adversary F3 / arch-adversary F6: unrecognized default-claim wording must
    be its own violation — never silently reinterpreted as 'claims OFF'."""
    reg = {"version": 1, "capabilities": [
        {"id": "cap-on", "summary": "s", "surfaces": ["local"],
         "activation": {"default": "on"}, "wired_by": ["w"], "exercised_by": ["e"]}]}
    with tempfile.TemporaryDirectory() as td:
        write(td, "capabilities.json", json.dumps(reg))
        # PLANT: paraphrase outside the vocabulary — must violate, not assert "off"
        c = cfg(td, {"exemption_prose": {"claims": [
            {"what": "paraphrased claim", "claim": "enabled by default",
             "artifact": "capabilities.json", "capability": "cap-on"}]}})
        rc, out = run(["exemption-prose", "--config", c])
        check("prose: unrecognized vocabulary -> violation naming the wording",
              rc == 1 and "not recognized" in out, (rc, out))
        # CONTROL: the OFF vocabulary works symmetrically
        reg_off = {"version": 1, "capabilities": [
            dict(reg["capabilities"][0],
                 activation={"default": "off", "switch": "s"})]}
        write(td, "capabilities.json", json.dumps(reg_off))
        c2 = cfg(td, {"exemption_prose": {"claims": [
            {"what": "off claim", "claim": "off-by-default",
             "artifact": "capabilities.json", "capability": "cap-on"}]}})
        rc2, out2 = run(["exemption-prose", "--config", c2])
        check("prose: off-by-default over default-off control -> exit 0",
              rc2 == 0, (rc2, out2))


def test_config_shape_and_containment():
    """script-adversary F5/F6: scan entries must stay inside the config's base dir, and
    malformed config SHAPES are usage (2) — never an AttributeError masquerading as a
    violation exit."""
    with tempfile.TemporaryDirectory() as td:
        outside = tempfile.mkdtemp()
        try:
            with open(os.path.join(outside, "x.py"), "w") as fh:
                fh.write('Z = "{k}".format(k=2)\n')
            c = cfg(td, {"render_pairing": {"scan": [outside]}})
            rc, out = run(["render-pairing", "--config", c])
            check("containment: absolute scan entry outside base -> exit 2 usage",
                  rc == 2, (rc, out))
            c2 = cfg(td, {"render_pairing": {"scan": ["../" + os.path.basename(outside)]}})
            rc2, out2 = run(["render-pairing", "--config", c2])
            check("containment: ../ escape -> exit 2 usage", rc2 == 2, (rc2, out2))
        finally:
            import shutil
            shutil.rmtree(outside, ignore_errors=True)
    with tempfile.TemporaryDirectory() as td:
        p = write(td, "sweeps.json", json.dumps([1, 2, 3]))
        rc, out = run(["render-pairing", "--config", p])
        check("shape: non-object config -> exit 2 usage", rc == 2, (rc, out))
        write(td, "src/x.py", 'Z = "{k}".format(k=2)\n')
        p2 = cfg(td, {"render_pairing": {"scan": ["src"],
                                         "exemptions": {"not": "a list"}}})
        rc2, out2 = run(["render-pairing", "--config", p2])
        check("shape: non-list exemptions -> exit 2 usage", rc2 == 2, (rc2, out2))


def test_all_subcommand():
    """arch-adversary F2: 'which sweeps are armed' lives in the CONFIG, not in hardcoded
    lists inside two callers — `all` derives the armed set from the sections present and
    emits one pinned summary line per sweep."""
    reg = {"version": 1, "capabilities": [
        {"id": "cap-on", "summary": "s", "surfaces": ["local"],
         "activation": {"default": "on"}, "wired_by": ["w"], "exercised_by": ["e"]}]}
    with tempfile.TemporaryDirectory() as td:
        write(td, "src/clean.py", 'Z = "{k}".format(k=2)\n')
        write(td, "capabilities.json", json.dumps(reg))
        c = cfg(td, {"render_pairing": {"scan": ["src"]},
                     "exemption_prose": {"claims": [
                         {"what": "w", "claim": "always-on",
                          "artifact": "capabilities.json", "capability": "cap-on"}]}})
        rc, out = run(["all", "--config", c])
        check("all: armed sections run, one summary line each, exit 0",
              rc == 0 and "dataflow_sweeps render-pairing: checked" in out
              and "dataflow_sweeps exemption-prose: checked" in out, (rc, out))
        # PLANT: a violation in either armed sweep fails `all`
        write(td, "src/clean.py", 'Z = "{k}".format(k=2, ghost=3)\n')
        rc2, out2 = run(["all", "--config", c])
        check("all: violation in an armed sweep -> exit 1", rc2 == 1, (rc2, out2))
    with tempfile.TemporaryDirectory() as td:
        c = cfg(td, {})
        rc, out = run(["all", "--config", c])
        check("all: zero armed sections -> vacuous refusal 3",
              rc == 3 and "refusing a vacuous pass" in out, (rc, out))
    with tempfile.TemporaryDirectory() as td:
        # ghost-gates stays advisory under `all` (Tier 2), --strict flips it
        write(td, "src/ghost.py", 'v = getattr(cfg, "x_enabled", True)\n')
        write(td, "src/declared.py", "class Config:\n    z_enabled = False\n")
        c = cfg(td, {"ghost_gates": {"scan": ["src"], "gate_patterns": ["*_enabled"],
                                     "declared_fields": {"kind": "module",
                                                         "path": "src/declared.py"}}})
        rc, out = run(["all", "--config", c])
        rc2, out2 = run(["all", "--config", c, "--strict"])
        check("all: ghost finding advisory by default, blocking under --strict",
              rc == 0 and rc2 == 1, (rc, rc2))


def test_companion_unclassified_fails_closed():
    """arch-adversary F5: an exemption naming a capability with NO user_facing
    annotation must fail CLOSED — absence of the audience fact is not 'internal'."""
    with tempfile.TemporaryDirectory() as td:
        write(td, "src/surplus.py", 'X = "hi {a}".format(a=1, ghost=2)\n')
        reg = {"version": 1, "capabilities": [
            {"id": "unclassified-thing", "summary": "s", "surfaces": ["local"],
             "activation": {"default": "on"}, "wired_by": ["w"], "exercised_by": ["e"]}]}
        write(td, "capabilities.json", json.dumps(reg))
        c = cfg(td, {"registry": "capabilities.json", "render_pairing": {
            "scan": ["src"], "exemptions": [
                {"what": "w", "target": "src/surplus.py::ghost", "owner": "d",
                 "expires": "2099-01-01", "capability": "unclassified-thing"}]}})
        rc, out = run(["render-pairing", "--config", c])
        check("companion: unclassified capability fails closed (annotate before exempting)",
              rc == 1 and "user_facing" in out, (rc, out))


def test_plant_target_handoff():
    """tripwire-auditor D12(c): the civerd-integrity.yml handoff entry is pinned
    mechanically — the engine-side plant rotation must be able to find the new checker.
    (Engine-side pickup itself is EXTERNAL-STATE, covered by the integrity-guards
    watchlist debt in capabilities.json.)"""
    repo_root = os.path.dirname(os.path.dirname(ROOT))
    with open(os.path.join(repo_root, "civerd-integrity.yml")) as fh:
        manifest = fh.read()
    check("handoff: dataflow_sweeps.py is a plant target",
          "plugins/tdd-playbook/bin/dataflow_sweeps.py" in manifest, manifest)
    check("handoff: the blessed gate is still the suite_cmd",
          'suite_cmd: "sh scripts/civerd_gate.sh"' in manifest, manifest)
    # planted-stripped twin: the pin can fail (§13)
    stripped = "plant_targets:\n  - path: plugins/tdd-playbook/bin/verify_verdict.py\n"
    check("handoff planted: manifest without the entry is detected",
          "dataflow_sweeps.py" not in stripped)


# ------------------------------------------------------------------ tool doc honesty
def test_help_states_bounds():
    """`--help` states what v1 does NOT cover — silently unhandled classes are the trap."""
    rc, out = run(["--help"])
    check("help: f-strings stated as skipped (compiler-checked)", "f-string" in out, out)
    check("help: %-style stated out of v1", "%" in out, out)
    check("help: ghost-gates tier stated", "Tier 2" in out, out)
    check("help: exits documented as 0/1/2/3", "3" in out and "vacuous" in out, out)


def main():
    global MOD
    print("dataflow_sweeps calibration (§6c Tier-1 reference tool)")
    check("bin/dataflow_sweeps.py exists", os.path.isfile(TOOL), TOOL)
    try:
        MOD = load_tool()
    except Exception as e:  # noqa: BLE001 — a missing/broken tool must read RED, not crash
        MOD = None
        check("tool loads", False, repr(e))
    suite = (test_render_pairing, test_exit_codes_and_vacuity, test_exemptions,
             test_ghost_gates, test_exemption_prose, test_summary_format,
             test_fail_closed_scan, test_template_pair_earns_checked,
             test_duplicate_exemption_targets,
             test_prose_vocabulary_closed, test_config_shape_and_containment,
             test_all_subcommand, test_companion_unclassified_fails_closed,
             test_plant_target_handoff, test_help_states_bounds)
    if MOD is not None:
        for fn in suite:
            print("\n[{}]".format(fn.__name__))
            fn()
    else:
        # name the suite's tests so the orphan guard sees them referenced even on the
        # tool-missing path: they run above whenever the tool loads
        for fn in suite:
            check("SKIPPED (tool missing): {}".format(fn.__name__), False)
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


if __name__ == "__main__":
    main()
