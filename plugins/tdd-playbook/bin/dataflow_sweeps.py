#!/usr/bin/env python3
"""dataflow_sweeps — the §6c Tier-1 reference sweeps (nodes are necessary; edges are the truth).

Origin: the Cheliped excavation (2026-08-03) — 12/12 post-safeguard escapes were EDGE
failures the node-level wiring net cannot see: flows produced with no live consumer, values
accepted with no reader, fixes verified at the supply end (T5: a "wired" prompt layer whose
key `str.format` silently dropped). These sweeps make the decidable slice of that class
mechanical. Config-driven so repos tailor the pairing map rather than fork the scanner.

Subcommands
  render-pairing   Tier 1, BLOCKING. AST-scans literal `str.format(...)`/`format_map` call
                   sites (same-file decidable, incl. module-level string constants) plus
                   config-mapped template-file<->supplier-module pairs. Checks BOTH
                   directions, reported distinctly:
                     - a placeholder with no supplier  -> broken render (missing value)
                     - a supplied key with no placeholder -> silently dropped value (T5)
  ghost-gates      Tier 2 — ADVISORY BY DEFAULT (findings printed, exit 0); `--strict`
                   flips it blocking. Its gate-name globs are a scoping proxy (an
                   undeclared `use_cache` gate escapes `*_enabled`), tolerable only under
                   FP/FN-budget governance — promotion to blocking is a pilot-data
                   decision, never a default. Finds `getattr(obj, "NAME", default)` /
                   `.get("NAME", default)` reads whose NAME matches the configured gate
                   patterns but is declared NOWHERE (the declared-fields source). An
                   undeclared default-True gate is flagged HIGH: invisible AND live.
  exemption-prose  Tier 1. Prose default-claims ("always-on", "on-by-default") checked
                   against the artifact of record (capabilities.json activation.default,
                   or a dotted key path into a named JSON config). A missing artifact or
                   capability fails CLOSED — never a skip.

Stated bounds (silently unhandled classes are the trap):
  - f-strings are SKIPPED — the compiler checks their names at parse time.
  - %-style formatting is OUT of v1 (use render-pairing on .format sites only).
  - dynamic receivers/**kwargs/computed names are counted UNRESOLVABLE in the summary —
    a count, never a silent pass; cover them with a named dated exemption if intentional.

Exemptions reuse the house debt shape `{what, target, owner, expires}` (the registry's
R-DEBT contract via the shared `_debt` module — one debt shape, not a fourth): an EXPIRED
exemption REDs the sweep (`--as-of` makes the trigger provable), and an exemption naming a
`user_facing` registry capability FAILS outright (§6a's companion rule, keyed on the
audience fact, not a proxy).

Every run prints the pinned machine-readable summary (the D13b rollup parses it):
  dataflow_sweeps <subcommand>: checked N · violations N · exempted N · unresolvable N

Exit codes: 0 clean · 1 violation · 2 usage ONLY · 3 vacuous-refusal ("refusing a vacuous
pass" — a scan of nothing is a REAL blocking verdict a mechanical consumer must be able to
distinguish from a fat-fingered flag; exit 2 is usage, never proof).

Config (JSON; all paths relative to the config file's directory):
{
  "registry": "capabilities.json",              // optional — companion-rule ground truth
  "render_pairing": {
    "scan": ["src", "bin/tool.py"],             // .py files/dirs for same-file call sites
    "template_pairs": [{"template": "prompts/x.tmpl", "supplier": "src/render.py"}],
    "exemptions": [{"what": "...", "target": "src/x.py::key",
                    "owner": "me", "expires": "2026-09-15"}]
  },
  "ghost_gates": {
    "scan": ["src"],
    "gate_patterns": ["*_enabled", "*_mode"],
    "declared_fields": {"kind": "module", "path": "src/config.py"},   // or kind: "capabilities"
    "exemptions": [...]
  },
  "exemption_prose": {
    "claims": [{"what": "...", "claim": "always-on",
                "artifact": "capabilities.json", "capability": "x"},
               {"what": "...", "claim": "on-by-default", "artifact": "settings.json",
                "key_path": "features.x.default", "expected": "on"}]
  }
}

Stdlib-only (house invariant for everything under bin/).
"""
from __future__ import annotations

import argparse
import ast
import datetime as _dt
import fnmatch
import json
import os
import re
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _debt  # noqa: E402  (the ONE house debt-date implementation, vendored alongside)

EXIT_CLEAN, EXIT_VIOLATION, EXIT_USAGE, EXIT_VACUOUS = 0, 1, 2, 3


# the ONE summary-line contract — gate_yield.py imports this (producer owns the format;
# consumers import it, they never re-type it)
SUMMARY_LINE_RX = re.compile(
    r"dataflow_sweeps ([a-z-]+): checked (\d+) · violations (\d+) · "
    r"exempted (\d+) · unresolvable (\d+)")


class Tally:
    def __init__(self, sub):
        self.sub = sub
        self.checked = 0          # sites/pairs/claims actually VERIFIED — the only
                                  # counter that can vouch for the scan (vacuity keys
                                  # on this alone; v1.25 arch-F1)
        self.exempted = 0
        self.violations = []      # (target, message, kind) — kind: "sweep" | "exemption"
        self.unresolved = []      # per-site NAMED targets, e.g. "src/x.py::<dyn:EXPR>" —
                                  # a count is never a silent pass, and a NAME lets §6c's
                                  # "dynamic sites get a named dated exemption" be
                                  # mechanically true (v1.25 arch-F4)
        self.scanned = set()      # rel paths this run actually read — the fact "unused
                                  # exemption" is judged against (v1.25 arch-F2)

    def violate(self, target, message, kind="sweep"):
        self.violations.append((target, message, kind))

    def unresolvable_site(self, target):
        self.unresolved.append(target)

    @property
    def unresolvable(self):
        return len(self.unresolved)

    def summary(self):
        return ("dataflow_sweeps {}: checked {} · violations {} · exempted {} · "
                "unresolvable {}".format(self.sub, self.checked, len(self.violations),
                                         self.exempted, self.unresolvable))


class ConfigError(Exception):
    """Malformed config SHAPE — usage (exit 2), never a violation exit or a traceback."""


def _require(cond, msg):
    if not cond:
        raise ConfigError(msg)


def check_shapes(cfg):
    _require(isinstance(cfg, dict), "config root must be a JSON object")
    for name in ("render_pairing", "ghost_gates", "exemption_prose"):
        section = cfg.get(name)
        if section is None:
            continue
        _require(isinstance(section, dict), "section {} must be an object".format(name))
        for key in ("scan", "exemptions", "template_pairs", "claims", "gate_patterns"):
            if key in section:
                _require(isinstance(section[key], list),
                         "{}.{} must be a list".format(name, key))
        for key in ("exemptions", "template_pairs", "claims"):
            for ent in section.get(key) or []:
                _require(isinstance(ent, dict),
                         "{}.{} entries must be objects".format(name, key))


# ------------------------------------------------------------------ shared plumbing
def iter_py_files(base, scan):
    real_base = os.path.realpath(base)
    for entry in scan:
        path = os.path.join(base, entry)
        # containment: a scan entry escaping the config's base dir can prove non-vacuity
        # against the WRONG tree — refuse it as usage, never scan it
        if not (os.path.realpath(path) + os.sep).startswith(real_base + os.sep):
            raise ConfigError("scan entry {!r} resolves outside the config's base "
                              "directory".format(entry))
        if os.path.isfile(path) and path.endswith(".py"):
            yield path
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for fn in sorted(files):
                    if fn.endswith(".py"):
                        yield os.path.join(root, fn)


def rel(base, path):
    return os.path.relpath(path, base)


def apply_exemptions(tally, exemptions, base, as_of, registry_path):
    """Validate exemption entries (house debt shape) and suppress matching violations.

    Order matters: entry-level violations (malformed / expired / user-facing) are REAL
    violations and the entry never suppresses; only clean, live, internal exemptions do.
    """
    registry = None
    suppress = {}
    seen_targets = set()
    for ent in exemptions or []:
        target = (ent or {}).get("target")
        label = "exemption {}".format(target or "<no target>")
        problems = list(_debt.debt_problems(ent, as_of, label))
        if target and target in seen_targets:
            # a fresh duplicate must never silence its expired twin's teeth
            problems.append("{}: duplicate target — one exemption per target, "
                           "re-date the existing entry instead (fail closed)"
                           .format(label))
        seen_targets.add(target)
        if not target:
            problems.append("{}: missing target (which violation does this cover?)"
                            .format(label))
        cap_id = (ent or {}).get("capability")
        if cap_id:
            if registry is None:
                if not registry_path or not os.path.isfile(registry_path):
                    problems.append("{}: names capability {!r} but no registry is "
                                    "readable (fail closed)".format(label, cap_id))
                    registry = {}
                else:
                    try:
                        with open(registry_path) as fh:
                            registry = json.load(fh)
                    except ValueError:
                        problems.append("{}: registry {} unreadable (fail closed)"
                                        .format(label, registry_path))
                        registry = {}
            if isinstance(registry, dict) and registry:
                cap = next((c for c in registry.get("capabilities", [])
                            if isinstance(c, dict) and c.get("id") == cap_id), None)
                if cap is None:
                    problems.append("{}: capability {!r} not found in registry "
                                    "(fail closed)".format(label, cap_id))
                elif cap.get("user_facing") is True:
                    problems.append(
                        "{}: names a user_facing capability {!r} — §6a companion rule: "
                        "exemptions are for internals, NEVER a darkness hatch on a "
                        "user-facing flow".format(label, cap_id))
                elif not isinstance(cap.get("user_facing"), bool):
                    # absence of the audience fact is NOT "internal" — fail closed
                    problems.append(
                        "{}: capability {!r} carries no user_facing audience fact — "
                        "classify it (bool) before exempting (fail closed)"
                        .format(label, cap_id))
        if problems:
            for p in problems:
                tally.violate(target or "<exemption>", p, kind="exemption")
        elif target:
            suppress[target] = ent
    kept = []
    used = set()
    for target, message, kind in tally.violations:
        # entry-level exemption violations always survive (typed kind, not a string
        # prefix proxy); sweep violations covered by a clean live exemption are counted
        # AND PRINTED as exempted — visible, dated, expiring, never silent
        if target in suppress and kind == "sweep":
            tally.exempted += 1
            used.add(target)
            ent = suppress[target]
            print("  EXEMPTED {}: {} (owner: {}, expires: {})".format(
                target, ent.get("what"), ent.get("owner"), ent.get("expires")))
        else:
            kept.append((target, message, kind))
    tally.violations = kept
    # named unresolvable sites may carry a named dated exemption too (§6c: "dynamic
    # templates get a NAMED dated exemption") — matched ones count exempted, never checked
    still_unresolved = []
    for target in tally.unresolved:
        if target in suppress:
            tally.exempted += 1
            used.add(target)
            ent = suppress[target]
            print("  EXEMPTED {}: {} (owner: {}, expires: {})".format(
                target, ent.get("what"), ent.get("owner"), ent.get("expires")))
        else:
            still_unresolved.append(target)
            print("  UNRESOLVABLE {}".format(target))
    tally.unresolved = still_unresolved
    # stale vs unmatched (v1.25 arch-F2 — "unused" is judged against the SCANNED set,
    # never against what this run happened to flag): a live exemption whose target's
    # file WAS scanned but matched nothing is stale debt hygiene -> fail closed; a
    # target outside this run's scan is a distinct, printed, non-blocking state so a
    # narrowed scan never false-REDs someone else's debt
    for target, ent in suppress.items():
        if target in used:
            continue
        target_file = target.split("::", 1)[0]
        if target_file in tally.scanned:
            tally.violate(target,
                          "exemption matches nothing — the target's file was scanned "
                          "and produced no matching site; remove the entry or fix the "
                          "target (a stale exemption silently excuses the next "
                          "regression at that name)", kind="exemption")
        else:
            print("  EXEMPTION NOT IN SCAN {}: target's file is not in scan for this "
                  "run (covered by a different sweep/config?)".format(target))


# ------------------------------------------------------------------ render-pairing
def _template_fields(template):
    """(named_roots, auto_count, max_index) from a format template, or None if unparsable."""
    named, auto, max_idx = set(), 0, -1
    try:
        for _lit, field, _spec, _conv in string.Formatter().parse(template):
            if field is None:
                continue
            if field == "":
                auto += 1
                continue
            root = re.split(r"[.\[]", field, maxsplit=1)[0]
            if root.isdigit():
                max_idx = max(max_idx, int(root))
            else:
                named.add(root)
    except ValueError:
        return None
    return named, auto, max_idx


def _module_str_constants(tree):
    """Module-level NAME -> str constant, only for names assigned exactly once."""
    consts, seen = {}, set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in seen:
                consts.pop(name, None)
                continue
            seen.add(name)
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                consts[name] = node.value.value
    return consts


def _check_pairing(tally, target_prefix, dyn_target, template, supplied_kw, supplied_pos,
                   star_args=False, star_kwargs=False):
    """Both-directions pairing for one resolved call site. Returns True when the site
    was actually VERIFIED (the caller credits `checked` on True and ONLY on True —
    an unresolvable site can never vouch for the scan, v1.25 arch-F1)."""
    fields = _template_fields(template)
    if fields is None:
        tally.unresolvable_site(dyn_target)
        return False
    named, auto, max_idx = fields
    if star_args or star_kwargs:
        tally.unresolvable_site(dyn_target)
        return False
    needed_pos = max(auto, max_idx + 1)
    for root in sorted(named - set(supplied_kw)):
        tally.violate("{}::{}".format(target_prefix, root),
                      "placeholder '{{{}}}' has no supplier — broken render"
                      .format(root))
    for kw in sorted(set(supplied_kw) - named):
        tally.violate("{}::{}".format(target_prefix, kw),
                      "supplied key '{}' has no placeholder — silently dropped value "
                      "(the T5 escape)".format(kw))
    if supplied_pos is not None:
        if needed_pos > supplied_pos:
            tally.violate("{}::<positional>".format(target_prefix),
                          "positional placeholder(s) have no supplier: template needs {}, "
                          "call supplies {}".format(needed_pos, supplied_pos))
        elif supplied_pos > needed_pos:
            tally.violate("{}::<positional>".format(target_prefix),
                          "surplus positional argument(s): call supplies {}, template has "
                          "{} — silently dropped value".format(supplied_pos, needed_pos))
    return True


def _dyn_target(base, path, src, expr_node):
    """Per-site NAMED target for an unresolvable site: <relpath>::<dyn:SOURCE-SEGMENT>.
    Keyed on the receiver's source text — unique per template expression, stable under
    line moves — never a file-wide blanket (v1.25 arch-F4)."""
    seg = None
    try:
        seg = ast.get_source_segment(src, expr_node)
    except Exception:  # noqa: BLE001 — a naming fallback, never a crash
        seg = None
    seg = (seg or "?").strip().replace("\n", " ")
    if len(seg) > 60:
        seg = seg[:57] + "..."
    return "{}::<dyn:{}>".format(rel(base, path), seg)


def sweep_render_pairing(cfg, base, tally):
    section = cfg.get("render_pairing") or {}
    for path in iter_py_files(base, section.get("scan") or []):
        tally.scanned.add(rel(base, path))
        try:
            with open(path) as fh:
                src = fh.read()
            tree = ast.parse(src)
        except (SyntaxError, ValueError, OSError) as e:
            # fail CLOSED: a file the sweep could not read/parse is a violation, never
            # an "unresolvable" that vouches for the scan (script-adversary F1)
            tally.violate(rel(base, path),
                          "could not read/parse scanned file (fail closed): {}"
                          .format(e))
            continue
        consts = _module_str_constants(tree)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("format", "format_map")):
                continue
            recv = node.func.value
            if isinstance(recv, ast.JoinedStr):
                continue  # f-string receiver — compiler-checked, stated bound
            if isinstance(recv, ast.Constant) and isinstance(recv.value, str):
                template = recv.value
            elif isinstance(recv, ast.Name) and recv.id in consts:
                template = consts[recv.id]
            else:
                # dynamic receiver — NAMED per site; never credits `checked`
                tally.unresolvable_site(_dyn_target(base, path, src, recv))
                continue
            target_prefix = rel(base, path)
            dyn_target = _dyn_target(base, path, src, recv)
            if node.func.attr == "format_map":
                arg = node.args[0] if node.args else None
                if (isinstance(arg, ast.Dict)
                        and all(isinstance(k, ast.Constant) and isinstance(k.value, str)
                                for k in arg.keys)):
                    if _check_pairing(tally, target_prefix, dyn_target, template,
                                      [k.value for k in arg.keys], None):
                        tally.checked += 1
                else:
                    tally.unresolvable_site(dyn_target)
                continue
            star_args = any(isinstance(a, ast.Starred) for a in node.args)
            star_kwargs = any(kw.arg is None for kw in node.keywords)
            supplied_kw = [kw.arg for kw in node.keywords if kw.arg is not None]
            supplied_pos = sum(1 for a in node.args if not isinstance(a, ast.Starred))
            if _check_pairing(tally, target_prefix, dyn_target, template, supplied_kw,
                              supplied_pos, star_args, star_kwargs):
                tally.checked += 1

    for pair in section.get("template_pairs") or []:
        tpl_path = os.path.join(base, pair.get("template", ""))
        sup_path = os.path.join(base, pair.get("supplier", ""))
        tally.scanned.add(pair.get("template", ""))
        tally.scanned.add(pair.get("supplier", ""))
        pair_target = "{}<->{}".format(pair.get("template"), pair.get("supplier"))
        if not os.path.isfile(tpl_path):
            tally.violate(pair_target, "template file missing (fail closed)")
            continue
        if not os.path.isfile(sup_path):
            tally.violate(pair_target, "supplier module missing (fail closed)")
            continue
        with open(tpl_path) as fh:
            fields = _template_fields(fh.read())
        if fields is None:
            tally.violate(pair_target, "template unparsable (fail closed)")
            continue
        named = fields[0]
        try:
            with open(sup_path) as fh:
                sup_tree = ast.parse(fh.read())
        except (SyntaxError, ValueError) as e:
            tally.violate(pair_target,
                          "supplier unparsable (fail closed): {}".format(e))
            continue
        supplied = set()
        for node in ast.walk(sup_tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("format", "format_map")):
                supplied.update(kw.arg for kw in node.keywords if kw.arg is not None)
                for a in node.args:
                    if isinstance(a, ast.Dict):
                        supplied.update(k.value for k in a.keys
                                        if isinstance(k, ast.Constant)
                                        and isinstance(k.value, str))
        if not named and not supplied:
            # `checked` is earned by doing work — an inert entry manufactures coverage
            # and defeats the vacuity guard (script-adversary F2)
            tally.violate(pair_target,
                          "template pair has nothing to pair — no placeholders and no "
                          "supplied keys (fail closed; remove the entry or fix the pair)")
            continue
        tally.checked += 1
        for root in sorted(named - supplied):
            tally.violate("{}::{}".format(pair.get("template"), root),
                          "template placeholder '{{{}}}' has no supplier in {} — broken "
                          "render".format(root, pair.get("supplier")))
        for kw in sorted(supplied - named):
            tally.violate("{}::{}".format(pair.get("template"), kw),
                          "supplied key '{}' has no placeholder in {} — silently dropped "
                          "value (the T5 escape)".format(kw, pair.get("template")))
    return section


# ------------------------------------------------------------------ ghost-gates
def _declared_names(base, declared_cfg):
    kind = (declared_cfg or {}).get("kind")
    path = os.path.join(base, (declared_cfg or {}).get("path", ""))
    if not os.path.isfile(path):
        return None
    if kind == "capabilities":
        try:
            with open(path) as fh:
                reg = json.load(fh)
        except ValueError:
            return None
        return {c.get("id") for c in reg.get("capabilities", []) if isinstance(c, dict)}
    if kind == "module":
        try:
            with open(path) as fh:
                tree = ast.parse(fh.read())
        except (SyntaxError, ValueError):
            return None
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        names.add(t.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.add(node.target.id)
        return names
    return None


def sweep_ghost_gates(cfg, base, tally, strict):
    section = cfg.get("ghost_gates") or {}
    patterns = section.get("gate_patterns") or ["*_enabled", "*_mode"]
    declared = _declared_names(base, section.get("declared_fields"))
    if declared is None:
        print("dataflow_sweeps ghost-gates: declared_fields source unreadable — check "
              "the config (usage)")
        return None
    print("dataflow_sweeps ghost-gates: Tier 2 — advisory by default, --strict makes it "
          "blocking; promotion to blocking is a pilot-data decision (§6c).")
    for path in iter_py_files(base, section.get("scan") or []):
        tally.scanned.add(rel(base, path))
        try:
            with open(path) as fh:
                src = fh.read()
            tree = ast.parse(src)
        except (SyntaxError, ValueError, OSError) as e:
            tally.violate(rel(base, path),
                          "could not read/parse scanned file (fail closed): {}"
                          .format(e))
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name_arg = default_arg = None
            if (isinstance(node.func, ast.Name) and node.func.id == "getattr"
                    and len(node.args) == 3):
                name_arg, default_arg = node.args[1], node.args[2]
            elif (isinstance(node.func, ast.Attribute) and node.func.attr == "get"
                  and node.args):
                name_arg = node.args[0]
                default_arg = node.args[1] if len(node.args) > 1 else None
            else:
                continue
            if not (isinstance(name_arg, ast.Constant) and isinstance(name_arg.value, str)):
                # dynamic name — NAMED per site, counted, never a silent pass
                tally.unresolvable_site(_dyn_target(base, path, src, name_arg))
                continue
            name = name_arg.value
            if not any(fnmatch.fnmatch(name, p) for p in patterns):
                continue
            tally.checked += 1
            if name in declared:
                continue
            always_on = isinstance(default_arg, ast.Constant) and default_arg.value is True
            severity = ("HIGH: undeclared always-on gate (invisible AND live)"
                        if always_on else "undeclared gate")
            tally.violate("{}::{}".format(rel(base, path), name),
                          "{} — '{}' matches {} but is declared nowhere in the "
                          "declared-fields source".format(severity, name,
                                                          "/".join(patterns)))
    return section


# ------------------------------------------------------------------ exemption-prose
# CLOSED vocabulary — an unrecognized claim is its own violation, never silently
# reinterpreted as a polarity (script-adversary F3: "enabled by default" used to be
# read as claiming OFF)
_CLAIM_POLARITY = {
    "always-on": "on", "on-by-default": "on", "always on": "on", "on by default": "on",
    "always-off": "off", "off-by-default": "off", "always off": "off",
    "off by default": "off",
}


def sweep_exemption_prose(cfg, base, tally):
    section = cfg.get("exemption_prose") or {}
    for claim in section.get("claims") or []:
        tally.checked += 1
        what = claim.get("what", "<unnamed claim>")
        artifact = os.path.join(base, claim.get("artifact", ""))
        if not os.path.isfile(artifact):
            tally.violate(what, "artifact {!r} missing — fail closed, never a skip"
                          .format(claim.get("artifact")))
            continue
        try:
            with open(artifact) as fh:
                data = json.load(fh)
        except ValueError:
            tally.violate(what, "artifact {!r} unreadable (not JSON) — fail closed"
                          .format(claim.get("artifact")))
            continue
        if claim.get("capability"):
            cap = next((c for c in data.get("capabilities", [])
                        if isinstance(c, dict) and c.get("id") == claim["capability"]),
                       None)
            if cap is None:
                tally.violate(what, "capability {!r} not in {} — fail closed"
                              .format(claim["capability"], claim.get("artifact")))
                continue
            actual = (cap.get("activation") or {}).get("default")
            expected = _CLAIM_POLARITY.get(str(claim.get("claim", "")).strip().lower())
            if expected is None:
                tally.violate(what,
                              "claim wording {!r} not recognized — state the expected "
                              "default explicitly; nothing to check is not a pass"
                              .format(claim.get("claim")))
                continue
            if actual != expected:
                tally.violate(what,
                              "prose claims {!r} but {} activation.default is {!r} for "
                              "{!r} — the exemption prose contradicts the artifact of "
                              "record".format(claim.get("claim"), claim.get("artifact"),
                                              actual, claim["capability"]))
        elif claim.get("key_path"):
            node = data
            missing = False
            for key in str(claim["key_path"]).split("."):
                if isinstance(node, dict) and key in node:
                    node = node[key]
                else:
                    tally.violate(what, "key path {!r} not found in {} — fail closed"
                                  .format(claim["key_path"], claim.get("artifact")))
                    missing = True
                    break
            if not missing and node != claim.get("expected"):
                tally.violate(what,
                              "prose claims {!r} but {}:{} is {!r} (expected {!r})"
                              .format(claim.get("claim"), claim.get("artifact"),
                                      claim["key_path"], node, claim.get("expected")))
        else:
            tally.violate(what, "claim entry names neither a capability nor a key_path — "
                          "nothing to check is not a pass")
    return section


# ------------------------------------------------------------------ CLI
_SECTION_OF = {"render-pairing": "render_pairing", "ghost-gates": "ghost_gates",
               "exemption-prose": "exemption_prose"}


def run_one(sub, cfg, base, as_of, strict, registry_path):
    """Run one sweep. Returns its exit code (0/1/2/3); prints violations + the pinned
    summary line either way."""
    tally = Tally(sub)
    if sub == "render-pairing":
        section = sweep_render_pairing(cfg, base, tally)
    elif sub == "ghost-gates":
        section = sweep_ghost_gates(cfg, base, tally, strict)
        if section is None:
            return EXIT_USAGE
    else:
        section = sweep_exemption_prose(cfg, base, tally)

    # vacuity is keyed on CHECKED alone: an unresolvable site (or an unreadable file —
    # which is a VIOLATION) can never vouch for the scan. Violations are judged first,
    # so a fail-closed scan error exits 1, and a zero-checked clean scan refuses.
    apply_exemptions(tally, section.get("exemptions"), base, as_of, registry_path)

    for target, message, _kind in tally.violations:
        print("  VIOLATION {}: {}".format(target, message))
    print(tally.summary())

    if tally.violations:
        # Tier-2 advisory covers the sweep HEURISTIC's findings only — debt hygiene
        # (exemption-kind violations: malformed/expired/stale/user-facing entries) is
        # exact by construction and ALWAYS blocks (v1.25 arch-F3: an EXPIRED exemption
        # under ghost-gates used to exit 0)
        if sub == "ghost-gates" and not strict \
                and all(kind == "sweep" for _t, _m, kind in tally.violations):
            print("dataflow_sweeps ghost-gates: {} finding(s) — ADVISORY (Tier 2); "
                  "--strict to block".format(len(tally.violations)))
            return EXIT_CLEAN
        return EXIT_VIOLATION
    if tally.checked == 0:
        print("dataflow_sweeps {}: refusing a vacuous pass — nothing was CHECKED "
              "(0 sites/pairs/claims verified; unresolvable {}); a gate that can pass "
              "by checking nothing is not a gate".format(sub, tally.unresolvable))
        return EXIT_VACUOUS
    return EXIT_CLEAN


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="dataflow_sweeps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "§6c Tier-1 dataflow-liveness sweeps: every flow names a live consumer.\n"
            "render-pairing / exemption-prose are Tier 1 (blocking); ghost-gates is\n"
            "Tier 2 (advisory by default, --strict to block). `all` runs every sweep\n"
            "whose section is present in the config — the CONFIG is the single source\n"
            "of which sweeps a repo arms; callers never hardcode the list."),
        epilog=(
            "Stated bounds: f-strings are SKIPPED (compiler-checked at parse time);\n"
            "%-style formatting is OUT of v1; dynamic names/**kwargs are counted\n"
            "UNRESOLVABLE, never silently passed — but an UNREADABLE/UNPARSABLE scanned\n"
            "file is a VIOLATION (fail closed), and a scan that CHECKED nothing refuses.\n"
            "Exit codes: 0 clean · 1 violation · 2 usage ONLY · 3 vacuous-refusal\n"
            "('refusing a vacuous pass' — a scan of nothing is a real blocking verdict,\n"
            "distinct from a fat-fingered flag; exit 2 is usage, never proof).\n"
            "Exemption hygiene (v1.25): unresolvable sites carry per-site names\n"
            "(<relpath>::<dyn:EXPR>) an exemption may target; an exemption whose target\n"
            "was SCANNED but matched nothing is a stale-entry VIOLATION (a target\n"
            "outside this run's scan prints 'NOT IN SCAN', non-blocking); exemption-\n"
            "entry violations (malformed/expired/stale/user-facing) always block, even\n"
            "under ghost-gates' advisory tier."))
    ap.add_argument("subcommand",
                    choices=["render-pairing", "ghost-gates", "exemption-prose", "all"])
    ap.add_argument("--config", required=True, help="JSON sweep config; paths inside are "
                                                    "relative to its directory")
    ap.add_argument("--as-of", default=None,
                    help="YYYY-MM-DD injected as 'today' for exemption expiry (tests / "
                         "trigger proofs)")
    ap.add_argument("--strict", action="store_true",
                    help="ghost-gates: exit 1 on findings (Tier-2 promotion is a "
                         "pilot-data decision — see §6c)")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        raise e  # argparse already printed; --help exits 0, usage errors exit 2

    as_of = _dt.date.today()
    if args.as_of is not None:
        as_of = _debt.parse_date(args.as_of)
        if as_of is None:
            print("dataflow_sweeps: --as-of {!r} is not YYYY-MM-DD (usage; exit 2 is "
                  "usage, never proof)".format(args.as_of))
            return EXIT_USAGE
    if not os.path.isfile(args.config):
        print("dataflow_sweeps: config {!r} not found (usage)".format(args.config))
        return EXIT_USAGE
    try:
        with open(args.config) as fh:
            cfg = json.load(fh)
    except ValueError as e:
        print("dataflow_sweeps: config {!r} is not valid JSON: {} (usage)"
              .format(args.config, e))
        return EXIT_USAGE
    try:
        check_shapes(cfg)
        base = os.path.dirname(os.path.abspath(args.config))
        registry_path = (os.path.join(base, cfg["registry"])
                         if cfg.get("registry") else None)

        if args.subcommand != "all":
            return run_one(args.subcommand, cfg, base, as_of, args.strict,
                           registry_path)

        armed = [sub for sub, sect in _SECTION_OF.items() if cfg.get(sect)]
        if not armed:
            print("dataflow_sweeps all: refusing a vacuous pass — no sweep section is "
                  "present in the config; nothing armed is nothing checked")
            return EXIT_VACUOUS
        codes = {}
        for sub in sorted(armed):
            codes[sub] = run_one(sub, cfg, base, as_of, args.strict, registry_path)
        if EXIT_USAGE in codes.values():
            return EXIT_USAGE
        if EXIT_VIOLATION in codes.values():
            return EXIT_VIOLATION
        if EXIT_VACUOUS in codes.values():
            return EXIT_VACUOUS
        return EXIT_CLEAN
    except ConfigError as e:
        print("dataflow_sweeps: {} (usage; exit 2 is usage, never proof)".format(e))
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
