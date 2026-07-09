# UX-Probe Engine Evaluation: page-agent vs Stagehand vs browser-use

**Date:** 2026-07-04 · **Method:** full source clones reviewed at code level (file:line citations throughout), plus ecosystem research.
**Purpose:** choose an engine for intent-only "probabilistic UX probes" in the TDD Playbook — an LLM agent given only a user goal ("sign up for the meeting") drives the real UI, while a deterministic harness records evidence and asserts outcomes (DB state, no 5xx, console budget). Blocking gate = deterministic oracles; agent result = trend line (per Playbook §7 zero-flake and §8 EVAL doctrine).

**Versions reviewed:** page-agent v1.11.0 (2026-07-03) · Stagehand core v3.6.0 · browser-use v0.13.3 (2026-07-01).

---

## Executive summary

1. **The industry has moved off Playwright as the *driver*.** Both mature engines (Stagehand v3, browser-use ≥0.12) replaced Playwright with their own raw-CDP stacks for speed and control. The original "agent-through-Playwright" architecture therefore becomes **"agent and Playwright sharing one Chromium over CDP"** — harness owns the browser (or attaches to it), agent drives it, harness passively captures network/console and asserts outcomes. The evidence chain survives, but composite: agent step-evidence + HAR/network events + console listener + DB asserts, *not* a single Playwright trace timeline (PW traces only attribute actions performed through PW's own API).
2. **All three engines self-report success via the LLM** — none can be a gate. This independently confirms the Playbook's architecture: deterministic oracles must live entirely in the harness, engine-agnostic.
3. **Recommendation: no single winner — pick per stack, under one doctrine.**
   - **Stagehand v3** for TypeScript/Node repos and wherever **deterministic replay** matters: its file-backed ActCache/AgentCache (probabilistic discovery → pinned, self-healing replay, cache files diffable in PRs) is the only real implementation of the deterministic/probabilistic hybrid, and Browserbase gates their own merges with exactly the oracle-blocks/judge-trends split the Playbook prescribes. Constraint: local operation is TS-only (the Python SDK is a thin cloud client).
   - **browser-use** for Python/pytest repos: cleanest attach-mode (`cdp_url`), built-in CDP HAR recorder, custom-action registry (a `report_ux_friction` action is ~20 lines), schema-validated structured `done` output. Constraints: zero determinism layer, telemetry + LLM judge on by default (disable both), fast API churn (pin exact versions).
   - **page-agent: do not adopt as a test engine.** SPA-only (a document navigation destroys the agent), synthetic `isTrusted:false` events (probe failures users would never experience = engine noise in the trend line), no determinism, bus-factor of one, zero E2E tests on a 1,745-line vendored DOM layer. Its niche is in-product copilots. The *pattern* it demonstrates stands; the library is the wrong tool for this job.
4. **Common hygiene regardless of engine:** pin versions; staging-only with controlled fixtures (prompt-injection surface is the page itself); LLM keys never in-page; kill telemetry/cloud-sync; budget caps per probe; planted-UX-defect calibration so the probe itself is proven live.

## Comparison matrix

| Dimension | page-agent v1.11 | Stagehand v3.6 | browser-use v0.13 |
|---|---|---|---|
| Language / runtime | TS, **in-page JS** | TS/Node (Python SDK = cloud-only client) | **Python ≥3.11** |
| Driver | Synthetic DOM events in page (`isTrusted:false`) | Own CDP layer ("understudy"), trusted `Input.dispatch*` | Own CDP (`cdp-use`), trusted `Input.dispatch*` |
| Perception | Text DOM serialization (vendored from browser-use), index-addressed live refs | Hybrid a11y-tree + DOM snapshot → XPath map | DOM+AX fusion, `backendNodeId` indexing, optional vision |
| Full-page navigation | **No — kills the run** (SPA only; prompt forbids leaving page) | Yes | Yes |
| Determinism / replay | None | **ActCache + AgentCache**: file-backed, CI-committable, self-healing; cache rewrites surface as PR diffs | `rerun_history`: fuzzy 5-level element re-matching, heuristic, not deterministic |
| Evidence emitted | Structured history incl. raw LLM req/resp; no screenshots | `onEvidence` stream: per-step screenshots, reasoning, a11y snapshots; metrics; inference logs | AgentHistory + per-step screenshots + GIF + video + **CDP HAR recorder** |
| Harness interop | Inject via `addInitScript`; `customFetch` seam tunnels LLM out of page | **Bidirectional**: `connectURL()` → PW `connectOverCDP`; accepts PW `Page` into act(); attaches via `cdpUrl` | `BrowserSession(cdp_url=...)` attaches to harness-launched Chromium; `keep_alive` |
| Network capture / mocking | None (harness-side only) | Passive only in-stack; **no interception/HAR** — PW sidecar needed | HAR with bodies built-in; no console capture (~50 lines CDP to add) |
| LLM providers | OpenAI-compatible endpoint only | Vercel AI SDK: Anthropic/OpenAI/Google/Bedrock/Ollama/…, CUA modes | First-party clients incl. Anthropic (tool-forced structured output) |
| Structured completion | `ExecutionResult {success, data, history}` | `AgentResult {success, actions, usage, messages}` + evidence events | `output_model_schema` → schema-validated `done` payload |
| Custom actions | `@experimental` hooks | AI SDK tools + MCP integrations | **Registry decorator** — ideal for `report_ux_friction` |
| Own test rigor | 53 unit tests, 40 lines on DOM layer, zero E2E | 72 unit + 63 real-browser integration specs; **agent evals gate their CI** (deterministic asserts + rubric verifier) | ~82 CI test files vs mocked LLM; CI retries everything (`nick-fields/retry`); real benchmarks off-repo/private |
| Maturity / bus factor | 1 maintainer (86% of commits), ~4 months public, monthly releases | Browserbase team, multiple releases/month, v3 <1yr old, active deprecations | ~4 employees dominate; heavy VC open-core; index contract changed within 2 months |
| Telemetry | None | None in core (verified) | **PostHog ON by default**; cloud-sync flag; disable both |
| License | MIT | MIT | MIT |
| Effort to first probe | 1–2 wks (SPA only); +2–3 wks for MPA (fork-adjacent) | ~1–2 wks incl. cache pinning + PW evidence sidecar | **2–4 days** for pytest fixture |

## Decision rationale

**Why Stagehand wins on architecture.** It is the only engine where the "probabilistic discovery, deterministic replay" pattern actually exists in code: `act()` resolves an intent to `{xpath, method, args}` once, caches it keyed on instruction+URL, replays it LLM-free on subsequent runs, and self-heals + rewrites the cache on UI drift — meaning **UI drift shows up as a cache-file diff in a PR**, which is a genuinely novel regression signal. Its evidence stream (`onEvidence`) and rubric verifier were built for exactly the probe-with-recorded-trajectory use case, and Browserbase dogfoods the pattern in their own merge gates. Risks: understudy is a young Playwright-reimplementation maintained by one vendor; no request interception (pair a passive Playwright CDP session for network evidence); TS-only locally.

**Why browser-use wins on Playbook fit.** The Playbook is pytest-centric; browser-use is Python, attach-mode is first-class, the HAR recorder feeds a "no 5xx" oracle with zero extra plumbing, `output_model_schema` gives a machine-readable probe verdict, and the action registry makes friction self-reporting trivial. Risks: no determinism at all (every run a fresh trajectory — pure trend-line duty), default-on telemetry and LLM judge to switch off, 4k-line core classes churning fast.

**Why page-agent is out (as a test engine).** Three disqualifiers for probe duty: (1) agent state lives in the page and dies on document navigation — most signup/checkout intents cross pages; (2) synthetic untrusted events mean some real components fail under the probe but not under users, polluting the metric the probe exists to produce; (3) no replay/caching and a bus factor of one. Its `customFetch` seam and clean promise-returning core are nice engineering, but they don't offset the epistemic noise problem. Revisit if probing an in-page copilot product surface, where in-page *is* the deployment target.

## Recommended probe architecture (engine-agnostic)

1. **Harness owns the browser.** Launch Chromium with a remote-debugging port (Playwright `launch` + CDP port, or bare subprocess). Attach the engine over CDP; attach your own passive listeners (network events or HAR, `Runtime.consoleAPICalled`).
2. **Probe = intent-only agent run** with steps capped, staging fixtures loaded, dangerous actions excluded (JS-eval, web-search), a `report_ux_friction` custom action registered where supported.
3. **Deterministic gate (blocking):** DB/persisted-state asserts, no-5xx from HAR/network log, console-error budget, forbidden-host check. Never reads the agent's opinion.
4. **Trend line (non-blocking):** success rate over N runs, steps-to-done, tokens/cost, friction events, loop-detector triggers; artifacts = full history + screenshots/GIF.
5. **Calibration (Playbook planted-error discipline):** periodically plant a UX defect (mislabeled submit, hidden required field) and require the probe to flag it. A probe that never fails a plant is theater.
6. **Cadence:** nightly/weekly on critical journeys, not per-commit (LLM-per-step cost + latency). With Stagehand, per-commit *cached replay* is cheap enough to run in CI, with cache-miss/self-heal events surfaced as warnings.

---

# Appendix A — page-agent (alibaba/page-agent) full code review

Version reviewed: **v1.11.0** (tag `v1.11.0`, 2026-07-03; HEAD `68245e8`).

## Verdict (short)

Page Agent is a credible, surprisingly clean candidate engine — but only for **SPA-scoped intents**. Its core (`@page-agent/core` + `@page-agent/page-controller`) is a headless-friendly, UI-free, promise-returning re-act loop (`execute(task): Promise<ExecutionResult>` with a structured `history` transcript), which is almost exactly the shape a Playwright-mediated probe wants. Element perception is a browser-use-derived text serialization with index addressing; the LLM layer is OpenAI-compatible-only but pluggable via `customFetch`, so keys can be kept out of the page. The two hard blockers are: (1) **a full page navigation destroys the agent** — the loop, task state, and history live in the page's JS context, and the only cross-page story is the Chrome extension's `MultiPageAgent`, not something you can drive headlessly from Playwright without building your own persistence layer; and (2) **all actions are synthetic, untrusted DOM events** (no real input, no keypresses, no file upload), so a subset of real UIs will behave differently under the probe than under a human. Maturity is "healthy young project with one maintainer": monthly releases, real CI, ~53 unit tests, zero E2E tests, one person authoring 86% of commits. Usable as a trend-line probe engine for SPA products with ~1–2 weeks of harness work; not currently suitable for multi-page (MPA) signup-style flows without meaningful additional engineering (~3–5 weeks) or accepting the extension-based path.

## 1. Architecture & Execution Model

**Everything runs in the target page's JavaScript context.** There is no server component in the core product; the npm library and IIFE bundle are injected into the page (README.md "Just in-page javascript. Everything happens in your web page.", confirmed by code — all DOM work uses `window`/`document` directly, e.g. `packages/page-controller/src/PageController.ts:114,130-132`).

**Monorepo layers** (root `package.json:6-15`): `packages/llms` (OpenAI-compatible LLM client), `packages/page-controller` (DOM extraction + action execution; LLM-independent per `PageController.ts:5-7`), `packages/core` (the agent loop `PageAgentCore`, no UI), `packages/page-agent` (thin wrapper adding the floating `Panel` UI, `packages/page-agent/src/PageAgent.ts:13-29`), `packages/extension` (WXT Chrome extension, multi-tab agent), `packages/mcp` (Node stdio MCP server bridging to the extension), `packages/ui`, `packages/website`.

**Main loop** — `PageAgentCore.execute()` at `packages/core/src/PageAgentCore.ts:210-375`, documented as a re-act loop at `PageAgentCore.ts:34-42`. Per step:
1. **Observe**: `this.pageController.getBrowserState()` (`PageAgentCore.ts:268`) → DOM extraction (`PageController.ts:129-165` → `updateTree()` at `:174-219`), plus system observations (URL change detection, wait-time and remaining-step warnings, `PageAgentCore.ts:538-577`).
2. **Think**: assembles a **fresh 2-message conversation each step** — system prompt + one user message containing `<instructions>`, `<agent_state>`, `<agent_history>` (compressed memory), and `<browser_state>` (`PageAgentCore.ts:273-276`, prompt assembly `:579-647`). The system prompt is a lightly edited browser-use prompt (`packages/core/src/prompts/system_prompt.md`).
3. **Act**: all tools are packed into a single "MacroTool" (`AgentOutput`) whose schema forces reflection fields (`evaluation_previous_goal`, `memory`, `next_goal`) plus one `action` chosen from a zod union of tool schemas (`PageAgentCore.ts:386-470`). The forced tool call is executed inline by the LLM client (`packages/llms/src/OpenAIClient.ts:237-249`).

Loop terminates on `done` action (`PageAgentCore.ts:317-325`), abort, error, or `maxSteps` (default 40, `PageAgentCore.ts:111`, cap check `:349-358`).

**DOM serialization** — a vendored, modified copy of browser-use's `buildDomTree.js`: `packages/page-controller/src/dom/dom_tree/index.js` (1,745 lines; acknowledgment in README). Not an a11y tree:
- Walks the real DOM (incl. shadow roots and same-origin iframes), computing visibility via `checkVisibility()` (`dom_tree/index.js:622-627`), **interactivity** via a heuristic stack — computed `cursor: pointer` styles (`index.js:719-784`), native interactive tags (`:786-849`), ARIA roles (`:871-899`), contenteditable, class/attribute heuristics (`:859-869`), DevTools-only `getEventListeners` when available (`:901-909`) — and **top-element** status via `elementFromPoint` hit-testing (`:966`, `:1025`, `:1054`).
- Interactive, visible, top elements get a sequential **`highlightIndex`**; the flat tree renders to text like `[12]<button aria-label=Submit>Submit />` via `flatTreeToString` (`packages/page-controller/src/dom/index.ts:193-463`), with attribute whitelist (`:198-227`), dedup, 20-char caps (`:372`), `*[n]` new-element markers (`:378-380`), `data-scrollable` annotations (`:390-403`). Scroll hints added at `PageController.ts:139-163`.
- **No screenshots, no vision** — text-only by design.

**Element addressing**: purely by **index into a per-step selector map holding live element references** — not XPath, not selectors (`dom/index.ts:496-508`; ref stored at `dom_tree/index.js:1648-1650`, comment "`@edit` no need for xpath" at `:1601`). Actions resolve `selectorMap.get(index).ref` (`packages/page-controller/src/actions.ts:23-42`). Indices are valid only for the snapshot the LLM saw; the map rebuilds every step (`PageController.ts:202-206`); stale-DOM races possible.

**Action space** (`packages/core/src/tools/index.ts`): `done` (:38-52), `wait` (:54-73), `ask_user` (:75-91, callback-gated, `PageAgentCore.ts:232`), `click_element_by_index` (:93-105), `input_text` (:107-120), `select_dropdown_option` (:122-136), `scroll`/`scroll_horizontally` (:141-180), opt-in `execute_javascript` (:182-198, gated by `experimentalScriptExecutionTool`, `PageAgentCore.ts:144-146`). **Absent**: navigation, keyboard (`send_keys` is a `@todo`, `tools/index.ts:200`), hover, drag, file upload, frame switching. The prompt forbids leaving the page (`system_prompt.md:88-89`). Tab tools exist **only in the extension** (`packages/extension/src/agent/tabTools.ts:24-74`).

**Action execution is synthetic**: `clickElement` scrolls into view, dispatches a spec-ordered pointer/mouse sequence + `target.click()` (`actions.ts:64-126`) — `isTrusted` will be `false`. Text input uses the native value setter + synthetic `input` event (`actions.ts:221-227`), with a contenteditable fallback that explicitly doesn't support Monaco/CodeMirror/Draft.js (`:139-213`). `<select>` set by direct `.value` assignment + `change` (`:250-251`). A `patchReact` hack marks common React roots non-interactive (`packages/page-controller/src/patches/react.ts:4-12`).

## 2. Harness-Mediation (Playwright fit)

**Yes, with real caveats.**
- Ships as npm ESM + IIFE bundle (`vite.iife.config.js:20-33`); injectable via `addInitScript`/`evaluate` (the "bookmarklet" path they already support).
- **Programmatic completion signal is good**: `await agent.execute(task)` resolves to `ExecutionResult {success, data, history}` (`packages/core/src/types.ts:281-285`); `success` is the LLM's self-report from `done` (`PageAgentCore.ts:317-321`). Step-limit exhaustion and internal errors resolve (not reject) with `success:false` (`:334, :354`).
- **Headless/UI-free**: use `PageAgentCore` + `PageController` directly with `enableMask:false` (`PageController.ts:28,96`).
- **Structured transcript**: typed event array with reflection, action name/input/output, token usage, raw LLM payloads (`types.ts:198-218`); JSON-serializable; extension ships a JSON exporter (`packages/extension/src/lib/history-export.ts:6-35`).
- **Hooks**: `onBeforeTask/onBeforeStep/onAfterStep/onAfterTask` (`types.ts:82-105`), `transformPageContent` (`:148`), `pushObservation()` (`PageAgentCore.ts:192-194`).
- **`customFetch`** on `LLMConfig` (`packages/llms/src/index.ts:107`, used at `OpenAIClient.ts:26-27,76`) lets a harness tunnel LLM calls out of the page (via `page.exposeFunction`) — solves CSP and key exposure, and doubles as a record/replay seam.

**Caveats:** CSP will typically block in-page LLM `fetch` (`OpenAIClient.ts:76-84`) — `bypassCSP` or the tunnel is mandatory. **Navigation kills the run** (URL-change handling is SPA-only, `PageAgentCore.ts:547-553`; no persistence/resume API; extension's `MultiPageAgent` + `RemotePageController` RPC is the only cross-page story, `packages/extension/src/agent/MultiPageAgent.ts:24-98`). The MCP server is extension-tethered (localhost hub bridging to a Chrome-Web-Store extension ID, `hub-bridge.js:7-8,64`), returns only `{success, data}` — not a CI story. No official Playwright/CI recipe exists anywhere in the repo.

## 3. Determinism

**None — every run is a fresh LLM conversation.** `execute()` resets history/observations/state per call (`PageAgentCore.ts:219-222`). No action caching, no replay, no seeding. `temperature` deprecated/unset by default (`packages/llms/src/index.ts:92-97`). Minor leaks: `newElementsCache` WeakMap persists across tasks in one page lifetime (`dom/index.ts:55,103-107`); `llms.txt` fetches cached per-origin (`packages/core/src/utils/index.ts:80-114`). A replay layer would be fork-level work, though `customFetch` is a clean record/replay seam for LLM responses.

## 4. Observability

- **Structured history**: per-step reflection, action `{name,input,output}`, token usage, full `rawRequest`/`rawResponse` (`types.ts:198-218`, populated `PageAgentCore.ts:307-315`); errors/retries are history events (`:120-131,333`).
- **Events**: `statuschange`, `historychange`, `activity`, `dispose` (`PageAgentCore.ts:44-59`; `types.ts:274-279`).
- **Console**: chalk-colored `console.group` per step (`PageAgentCore.ts:264-282,410-445`) — capturable via `page.on('console')`.
- **No screenshots/video/DOM snapshots persisted** — harness must own those.
- Extension adds IndexedDB task history + JSON export.

## 5. LLM Integration

- **OpenAI-compatible chat-completions only** (`OpenAIClient.ts:76`; wrapper hardcodes it, `packages/llms/src/index.ts:27-28`). Anthropic/Gemini via compatible endpoints or OpenRouter, with per-provider request patcher (`modelPatch` in `packages/llms/src/utils.ts`, reworked v1.11.0 for "GPT, Claude, Qwen, Gemini, DeepSeek").
- **Structured output via forced tool calling** (`tool_choice` at `OpenAIClient.ts:42-52`), zod-validated (`:225-235`). A 200-line `normalizeResponse`/autoFixer repairs malformed outputs — including a fallback to `wait 1s` when action is missing (`packages/core/src/utils/autoFixer.ts:21-121`, wait fallback `:94-97`). Live provider-matrix tests, env-gated (`packages/llms/src/live-models.test.ts:1-33`). Retries: 2 default with error taxonomy (`index.ts:42-52,58-81`).

## 6. Safety / Security

- **BYOK in-page by design**: Bearer key sent from the browser (`OpenAIClient.ts:80`); demo IIFE reads `apiKey` from the script URL query (`packages/page-agent/src/demo.ts:34`). Docs honest about it (`docs/terms-and-privacy.md` §1; testing API "technical evaluation only" §2). `customFetch` avoids in-page keys.
- **Prompt injection: no defenses.** Page text flows verbatim into the prompt (`PageAgentCore.ts:635-644`); `experimentalLlmsTxt` fetches and injects `origin/llms.txt` (`utils/index.ts:83-115`) — a literal injection channel if enabled. `execute_javascript` is raw eval (`PageController.ts:383-398`) with a docs warning (`types.ts:118-124`). Element exclusion via `interactiveBlacklist`/`data-page-agent-not-interactive` (`PageController.ts:186-189`). No domain restrictions.
- **Human takeover is vestigial**: `user_takeover` event type exists and renders in the Panel (`types.ts:229-233`, `packages/ui/src/panel/Panel.ts:648-649`) but nothing emits it. What exists: `ask_user` (callback-gated) and clean async `stop()` (`PageAgentCore.ts:200-204`).
- Full-viewport `SimulatorMask` blocks human input during runs (`packages/page-controller/src/mask/SimulatorMask.ts:43-71`) — disable in harness. Prompt-level guardrails only (`system_prompt.md:72,79,93`).

## 7. Maturity

- **Cadence**: v1.8.0 (2026-04-15) → v1.11.0 (2026-07-03), roughly monthly minors, honest Keep-a-Changelog.
- **Bus factor 1**: Simon 171 of 198 commits in the clone window; next is dependabot (11).
- **Tests**: 6 files, ~1,127 lines, ~53 cases. `llms` well-tested; `core` has a solid 365-line mocked loop test (`packages/core/src/PageAgentCore.test.ts:33-66`); **the 1,745-line vendored DOM file has a 40-line test**; **zero browser/E2E tests** (happy-dom env).
- **CI**: commitlint, lint, prettier, typecheck, vitest, build (`.github/workflows/ci.yml`, `scripts/ci.js:33-56`); husky, dependabot, release workflow.
- **TODOs**: 21 in non-test source; several load-bearing (`actions.ts:85`, `:345-363`; `tools/index.ts:200-202`).
- **Docs**: good (site, developer guide, SECURITY.md, terms, AGENTS.md). "Technical evaluation only" applies to the free demo LLM API, not the library.

## 8. Testing-Fit Verdict

**Build for SPAs (~80% of plumbing present):** inject a custom UI-free IIFE of core (`demo.ts:25-55` shows what to strip); `customFetch` over `page.exposeFunction` (~1–2 days) for Node-side LLM calls; `page.evaluate(() => window.__agent.execute(intent))` → `ExecutionResult`; wire `onAfterStep` to Playwright screenshots.

**Risk register:** MPA navigation is a blocker for many signup-style intents (options: SPA-only scope; a Node-side outer loop re-injecting and re-seeding history after navigation, ~2–3 wks fork-adjacent; or the extension under Playwright persistent context — heavy, Chrome-only). Synthetic events (`isTrusted:false`, no keyboard/file upload, `<select>` by value assignment) fail some real components for reasons users wouldn't experience — the biggest epistemic risk. Perception noise (cursor-heuristic + `elementFromPoint`) guarded by 40 lines of tests. `success` self-reported. Single maintainer, `@experimental` APIs — pin or vendor.

**Effort:** SPA-only harness ~1–2 wks, low-moderate risk. MPA continuity +2–3 wks, moderate-high risk.

---

# Appendix B — Stagehand (browserbase/stagehand) full code review

## Verdict (top-line)

**Conditional adopt — strong fit, with two eyes open.** This repo is the TypeScript original (monorepo, core = `@browserbasehq/stagehand` v3.6.0, MIT). **v3 removed Playwright as the driving engine**, replaced by an in-house CDP layer, **"understudy"** (`packages/core/lib/v3/understudy/`, ~10k+ lines) — Playwright is now an optional peer dependency used only for interop. Crucially, the interop is bidirectional and clean: Stagehand exposes its raw CDP websocket (`connectURL()`), so a deterministic Playwright harness can `connectOverCDP` to the *same* browser and own tracing/network/console evidence while Stagehand's agent drives it; conversely you can pass a Playwright `Page` directly into `act()/extract()/observe()`. Fully LOCAL/headless with zero Browserbase dependency (gotcha: in `env:"BROWSERBASE"` mode, inference silently routes through Browserbase's hosted API by default). The probabilistic-discovery/deterministic-replay story is real and file-backed (`ActCache`/`AgentCache`, JSON in a configurable `cacheDir`, committable to CI), though replay re-resolves selectors live and self-heals via LLM on failure — *pinned*, not *hermetic*. Main risks: v3 is young, the custom CDP layer is a large novel surface maintained by a small vendor team, understudy has **no request interception/mocking**, and `success` is LLM-asserted.

## 1. Architecture & Execution Model

### Driver stack: "understudy," a Playwright reimplementation over raw CDP
- Orchestrator `V3` class (`packages/core/lib/v3/v3.ts:154`), bootstraps Chrome/Browserbase + CDP WebSocket + `V3Context` (`v3.ts:149`).
- LOCAL launch via **chrome-launcher**, not Playwright (`packages/core/lib/v3/launch/local.ts:1`, `--headless=new` at `local.ts:29,41`); dials CDP directly (`v3.ts:1004`).
- Understudy (`packages/core/lib/v3/understudy/`) reimplements the Playwright surface over `devtools-protocol`: `page.ts:67-79` (top session + OOPIF child sessions + FrameRegistry), `frame.ts`, `locator.ts`, `deepLocator.ts` (closed-shadow-root piercing), `networkManager.ts`, `lifecycleWatcher.ts`, `consoleMessage.ts`, `screenshotUtils.ts`. Clicks via `Input.dispatchMouseEvent` (`understudy/locator.ts:364,385-419`).
- Root `CHANGELOG.md` v3.0.0: "Removes internal Playwright dependency"; `playwright-core`/`puppeteer-core`/`patchright-core` are optional peerDependencies.

### Perception: hybrid a11y-tree + DOM snapshot
- All primitives use `captureHybridSnapshot` (`understudy/a11y/snapshot/capture.ts:58`): per CDP session, `DOM.getDocument` (`snapshot/domTree.ts:147`) + `Accessibility.getFullAXTree` (`snapshot/a11yTree.ts:32`), merged per-frame (incl. OOPIFs, shadow DOM) → text outline (`combinedTree`) + `EncodedId → XPath` map (algorithm at `capture.ts:40-56`).
- `observe()` feeds `combinedTree` to the LLM, maps IDs back to `xpath=` selectors (`handlers/observeHandler.ts:103-156,210`). `extract()` same snapshot; schema-less extract returns `combinedTree` as `pageText` (`handlers/extractHandler.ts:135-144`); optional `screenshot:true` (`:163-184`).

### Acting: act() = one inference → one deterministic CDP action
`ActHandler.act` (`handlers/actHandler.ts:137`): DOM/network-quiet wait (`:147`), snapshot (`:152`), one inference proposing `{elementId, method, arguments}` (`:164`), executed via `performUnderstudyMethod` (`actHandler.ts:306`; `METHOD_HANDLER_MAP` at `handlers/handlerUtils/actHandlerUtils.ts:35,83,124`; selectors via `deepLocator.ts`). `twoStep` flows re-snapshot, **diff the trees**, ask a follow-up (`actHandler.ts:198-252`).

### Playwright interop — works both directions
- **PW → Stagehand's browser**: `stagehand.connectURL()` (`v3.ts:1547-1552`); docs show `chromium.connectOverCDP` + mixing `pwPage.goto()` with `stagehand.act("…", {page: pwPage})` (`packages/docs/v3/integrations/playwright.mdx:40-63`).
- **PW Page into Stagehand**: `act/extract/observe` accept `AnyPage`; normalized via CDP session + `Page.getFrameTree` matching (`v3.ts:1702-1732,1770-1802`). Puppeteer/Patchright equally supported.
- **Stagehand → your browser**: `localBrowserLaunchOptions.cdpUrl` attaches to a running browser (`v3.ts:945-969`).
- **Caveat**: you never get a PW `Page` *from* Stagehand — interop = shared browser over CDP, two clients side by side.

### agent() modes
- `agent()` (`v3.ts:1948`), three modes:
  - **DOM (default)** — `V3AgentHandler`, Vercel AI SDK `generateText`/`streamText` tool loop (`handlers/v3AgentHandler.ts:458-471`), `maxSteps=20` default (`:162`); tools: `act`, `extract`, `ariaTree`, `fillForm`, `goto`, `scroll`, `keys`, `navback`, `screenshot`, `wait`, `think`, optional `search` (`agent/tools/index.ts`).
  - **Hybrid** — coordinate tools swapped in via `filterTools` (`agent/tools/index.ts:77-103`); gated to `HYBRID_CAPABLE_MODEL_PATTERNS = ["gemini-3","claude","gpt-5.4","gpt-5.5"]` (`types/private/agent.ts:12-17`).
  - **CUA** — `V3CuaAgentHandler`, provider-native computer-use loops (`agent/AnthropicCUAClient.ts:511-523,866-960`; providers at `agent/AgentProvider.ts:17-37`).
- Custom tools via `options.tools` (AI SDK) + MCP `options.integrations` (`lib/v3/mcp/connection.ts:24-78`, merged `v3AgentHandler.ts:195`) — DOM/hybrid only.

## 2. Determinism & Caching
- **Storage**: `CacheStorage.create(opts.cacheDir, …)` (`v3.ts:394`; `cache/CacheStorage.ts:21-45`) — JSON files, content-addressed `<sha256>.json`; off unless `cacheDir` set.
- **ActCache** (`cache/ActCache.ts`): key = SHA-256 of `{instruction, normalized URL, sorted variable keys}` (`:188-199`); value = resolved actions `{selector(xpath), method, arguments, description}`, `version:1` (`:148-160`). Replay waits for selector attach (best-effort, `cache/utils.ts:39-53`), executes deterministically (`:214-236`). Wiring: try replay before inference, store after success (`v3.ts:1293-1319,1346-1353`).
- **Self-healing**: on action failure, re-snapshot + re-infer + retry (`handlers/actHandler.ts:334-405`, `selfHeal` default true, `v3.ts:852`); cache rewritten with healed actions (`ActCache.ts:264-275,327-360`).
- **AgentCache** (`cache/AgentCache.ts`): whole runs as typed replay steps (`:627-683`); key includes instruction/startUrl/options/config (`:519-534`); replayed acts run stored actions with self-heal (`:685-725`); replay returns cached final `AgentResult` with usage zeroed + `metadata.cacheHit:true` (`:597-609`); replay failure falls back to live run (`:614-624` → `v3.ts:2096-2128`).
- **CI pinning**: commit `cacheDir` JSON. Sharp edges: (a) instruction/URL drift = silent miss = full LLM run (no strict-replay-only mode — build a wrapper asserting `cacheHit`); (b) replayed agent results echo the recorded final message — verify steps execute, not that the outcome recurred; oracle must be external. Variables substitute at replay; only keys enter the cache key (`ActCache.ts:52-60`). Browserbase `serverCache` exists (`v3.ts:1058`) — ignorable for LOCAL.

## 3. Harness-Mediation & Evidence Chain
- **Local/headless CI: yes** (`env:"LOCAL"`, chrome-launcher `--headless=new`, no Browserbase key). Their CI runs an e2e matrix with `STAGEHAND_BROWSER_TARGET: local` (`.github/workflows/ci.yml:397-424,597-645`).
- **Hosted-inference gotcha**: `env:"BROWSERBASE"` creates a `StagehandAPIClient` unless `disableAPI:true` (`types/public/options.ts:63`, `v3.ts:1053-1059`) — act/extract/agent execute on Browserbase servers (`v3.ts:2113-2126`). LOCAL never constructs it.
- **Network**: understudy `NetworkManager` is **passive-only** (`Network.requestWillBeSent/loadingFinished/loadingFailed` for idle heuristics, `understudy/networkManager.ts:135-143,194`). **No `route()`/`Fetch.enable`, no mocking, no HAR.** Response objects exist for navigations (`understudy/response.ts`; tested `tests/integration/page-goto-response.spec.ts:22-33`). ⇒ attach your PW context over CDP to the same browser for network evidence; CDP `Network` events broadcast to all sessions, passive capture coexists fine (active `route()` from a second client riskier — test).
- **Console**: `page.on("console", …)` (`understudy/page.ts:634`) or your PW session.
- **Tracing/video: absent from understudy.** PW traces only record actions performed through PW — Stagehand-driven actions won't appear as trace actions; you'll still get network/console/screenshots. Compensate with Stagehand's evidence stream.
- **Browserbase cloud adds (optional)**: session replay dashboard, live debug URL (`v3.ts:1124-1135`), proxies, captcha (`v3.ts:198-204`), stealth (`v3.ts:210-217`), hosted inference/cache, `search` tool (`agent/tools/index.ts:161-202`).

## 4. Observability
- **Logs**: `LogLine {category, message, level 0-2, auxiliary}` (`types/public/logs.ts:16-28`), Pino (`lib/logger.ts:35-54`), injectable logger (`:243-249`), per-instance AsyncLocalStorage routing (`lib/v3/logger.ts:35-104`).
- **History**: `stagehand.history` (frozen, `v3.ts:695-710`) records act/extract/observe with params/result/timestamp + `cacheHit` (`v3.ts:1307-1317`). **Agent runs not in history** — use `AgentResult`.
- **Agent traces**: `AgentResult {success, message, actions, completed, usage{input/output/reasoning/cached, inference_time_ms}, messages}` (`types/public/agent.ts:92-117`); per-step `reasoning`, tool, `pageUrl`, timing (`agent.ts:79-90`; populated `v3AgentHandler.ts:312,337-348`). Streaming + `onStepFinish`/`prepareStep` (`v3AgentHandler.ts:465-471`). **`onEvidence` events**: typed `screenshot` (PNG Buffer, role probe/agent), `step_finished` (action/args/reasoning/output), `step_observed` (url + ariaTree), `final_answer` (`types/public/agentEvidenceEvents.ts:29-95`; post-step probe screenshot+a11y each step, `v3AgentHandler.ts:363-373`). A ready-made evidence feed.
- **Cost**: `StagehandMetrics` per-primitive tokens/time (`types/public/metrics.ts:1-27`, `v3.ts:712-759`).
- **Inference dumps**: `logInferenceToFile` → `./inference_summary/` (`lib/inferenceLogUtils.ts:7-62`). Internal FlowLogger gated by env (`flowlogger/EventStore.ts:13-15`). **No phone-home** (grep-verified).

## 5. LLM Integration
- **Vercel AI SDK abstraction**: `LLMProvider.getClient()` routes `provider/model` strings (`llm/LLMProvider.ts:216-234`); providers: openai, anthropic, google, bedrock, vertex, azure, xai, groq, cerebras, togetherai, mistral, deepseek, perplexity, ollama, gateway (`:37-70`). Default `openai/gpt-4.1-mini` (`v3.ts:101`). Custom `LLMClient` injectable (`v3.ts:359-360`) + AI SDK middleware (`v3.ts:352`).
- **Structured output**: Zod v3/v4 (`zodCompat.ts:33-49`) → `generateObject` (`llm/aisdk.ts:250-258`); legacy fallbacks (Anthropic synthetic tool-calling `AnthropicClient.ts:146-166`; Groq/Cerebras regex-scrape — off default path).
- **CUA**: OpenAI, Anthropic (native `computer_20251124`, `AnthropicCUAClient.ts:462-523`), Google, Microsoft fara-7b (`agent/AgentProvider.ts:17-37`). Prefer DOM agent for replay: CUA steps are coordinates/screenshots, mostly don't replay from cache.

## 6. Their Own Evals/Tests
- **Two-tier eval framework** (`packages/evals/`, Braintrust runner `framework/runner.ts`): "core" tier = deterministic browser tasks scored by `node:assert` (`framework/assertions.ts`; e.g. `core/tasks/actions/click.ts:31-35` asserts `aria-expanded`), "bench" tier = act/extract/observe/agent × model matrix incl. WebVoyager, OnlineMind2Web, WebTailBench, GAIA (`packages/evals/datasets/`). Defaults: 3 trials, local (`evals.config.json:1-22`).
- **Agent judging**: LLM judge with two backends (`packages/core/lib/v3Evaluator.ts:23-37`): legacy screenshot YES/NO (`v3LegacyEvaluator.ts:22-129`) and a **rubric verifier** (`lib/v3/verifier/rubricVerifier.ts`, 2,145 lines): auto-generated rubric, trajectory evidence scoring, deterministic aggregation Σearned/Σmax (`:600-607`), failure taxonomy, disk-cached rubrics (`framework/rubricCache.ts:91-105`). Trajectories via `onEvidence` (`framework/verifierAdapter.ts:44-84`). Where ground truth is checkable they use deterministic oracles even in benches (`extract_github_stars.ts:27-31`).
- **Unit depth**: 72 vitest unit files (mocked LLM), 63 real-browser integration specs (OOPIF, downloads, console, responses), incl. `agent-cache-self-heal.spec.ts` and `act-cache-url-normalize.test.ts`.
- **CI**: lint/build/unit/e2e (local + Browserbase matrices) + a **"regression" eval category with trials=3, failing on missing Braintrust score** (`.github/workflows/ci.yml:218-241,707-822`). They gate merges on agent evals.

## 7. Maturity
- Core 3.6.0, MIT. Monorepo: core, evals, cli, server-v3 (source-visible, `"private": true`), docs.
- **Cadence**: 14 releases in 3.x, multiple/month; last commit 2026-07-03. Very active.
- **Contributors**: vendor-concentrated (~2-3 Browserbase engineers dominate recent window; ~7-8 recurring in CHANGELOG).
- **Breaking history**: v3.0.0 = engine swap (PW → understudy; `ObserveResult`→`Action`; model config consolidation) with real migration guide (`packages/docs/v3/migrations/v2.mdx`); active deprecations (`cua:true` → `mode:"cua"`, `v3.ts:1961-1971`).
- **Python SDK is NOT the TS engine**: Stainless-generated API client where AI logic runs on Browserbase's hosted API (`stainless.yml`; `packages/docs/v3/migrations/python.mdx`). **Local-only ⇒ TypeScript/Node required.**
- **Open-core risk**: LOCAL genuinely self-sufficient; cloud-gated extras visible but avoidable.

## 8. Testing-Fit Verdict
1. Harness owns the browser (`chromium.connectOverCDP(stagehand.connectURL())` is the simple direction); attach network/console listeners + PW tracing before the probe.
2. Probe = `stagehand.agent({mode:"dom", maxSteps:N}).execute({instruction, onEvidence})`; persist evidence stream + `AgentResult.actions/usage`; `success` = telemetry, never gate.
3. Deterministic gate = harness asserts (DB, no-5xx from PW network log, console budget) — exactly how Browserbase's own core eval tier works (`framework/assertions.ts`).
4. Cost/flake control: committed `cacheDir`; first green run records action JSON; CI replays near-zero-token with self-heal; alert on `cacheHit !== true`; heals surface as PR diffs.
5. Optional: reuse the rubric verifier as a secondary graded signal.

**Missing/you build**: request interception/HAR (PW sidecar); strict-replay-fail-on-miss wrapper; agent runs in `history`; PW trace timeline for agent steps (fill with evidence screenshots); Python not viable locally.

**Effort**: ~1–2 engineer-weeks; long tail = flake tuning (network-idle heuristics, `domSettleTimeoutMs`) + cache-drift policy.

**Risks, ranked**: (1) understudy = young vendor-maintained CDP reimplementation; (2) API churn; (3) vendor concentration/cloud gravity (MIT + local core mitigate); (4) replay is self-healing, not hermetic — a feature for drift tolerance, a bug if you expected byte-identical runs.

---

# Appendix C — browser-use (browser-use/browser-use) full code review

Version reviewed: v0.13.3 (shallow clone, history grafted at 2026-02-12).

## Verdict

**Conditionally recommended — attach-mode only, agent as probe, never as gate.** browser-use is now a pure-CDP stack (its own `cdp-use` client; `pyproject.toml:52` lists `cdp-use==1.4.5`, `playwright` appears nowhere in dependencies). Good: `BrowserSession(cdp_url=...)` attaches cleanly to externally launched Chromium (`browser_use/browser/session.py:206,266`), CDP-based HAR recorder (`browser_use/browser/watchdogs/har_recording_watchdog.py:144`), rich JSON-serializable `AgentHistoryList` with per-step reasoning/actions/screenshots (`browser_use/agent/views.py:488,595`), first-class Anthropic support with tool-forced structured output (`browser_use/llm/anthropic/chat.py:349-376`), clean custom-action registry (`browser_use/tools/service.py:2088`), typed structured `done` output (`tools/service.py:1998-2031`). Bad: you lose Playwright's trace timeline unless PW owns the browser and browser-use attaches over CDP (isolation by discipline, not API); agent-optimized not test-optimized (LLM judge on by default, telemetry on by default, 4,100-line Agent class); `rerun_history` is best-effort fuzzy matching, not deterministic; heavily VC-funded open-core vendor bending toward its cloud.

## 1. Architecture & execution model

**Loop**: `Agent.run()` (`browser_use/agent/service.py:2492`) → `_execute_step` → `step()` (`service.py:1027`): (1) **Perceive** — `get_browser_state_summary(include_screenshot=True)` (`service.py:1088-1091`; `session.py:1563`); screenshot captured **every step regardless of `use_vision`** ("so that cloud sync is useful", `service.py:1089`). (2) **Decide** — `_get_next_action` (`service.py:1167`), structured `AgentOutput` (thinking/evaluation/memory/next_goal/actions, `agent/views.py:388-400`). (3) **Act** — `multi_act` (`service.py:2719`) sequential with stale-DOM guards (`terminates_sequence` + URL/focus comparison aborting the queue, `service.py:2801-2817`). Heuristic scaffolding: budget warnings, replan/exploration nudges, action-loop detector hashing recent actions + page fingerprints (`service.py:1145-1151`; `agent/views.py:157-249`) — useful friction signals, but hidden prompt injections shape step behavior.

**Perception**: `DomService._get_all_trees` (`browser_use/dom/service.py:385`) collects over raw CDP: `DOMSnapshot.captureSnapshot`, `DOM.getDocument`, full AX tree for all frames (`dom/service.py:339`), plus a JS `getEventListeners` pass with >10k-element bail-out (`dom/service.py:443-484`) → `EnhancedDOMTreeNode` tree → `DOMTreeSerializer` (`browser_use/dom/serializer/serializer.py:41`): interactivity, visibility/paint-order, bounding-box containment, shadow DOM, compound controls (`serializer.py:617-727`). **Indexing = CDP `backendNodeId`** (changed recently; `serializer.py:712-713`), rendered `*[<backend_node_id>]<tag ...>` (`serializer.py:925-927`; `*` = new since last step, `:719-723`). `backendNodeId` is stable within a page lifetime, **not across loads/runs**. Vision highlighting drawn in Python on screenshots (`browser_use/browser/python_highlights.py:1-3,409`), not by page mutation.

**Action**: tools dispatch on a `bubus` event bus (e.g. `ClickElementEvent`, `tools/service.py:727`) handled by `DefaultActionWatchdog` performing real input via `Input.dispatchMouseEvent`/`dispatchKeyEvent` (`browser/watchdogs/default_action_watchdog.py:906,920,940,1082`). Only Playwright remnants: copied launch-flag comments (`browser/profile.py:38-67`) and CI using `uvx playwright install chromium` as a browser installer (`.github/workflows/test.yaml:49`).

**Attach/coexist**: `BrowserSession(cdp_url=...)` over WebSocket (`session.py:206,266,1760,1820`), reconnect logic (`:2083-2118`), `keep_alive` (`profile.py:629`, `session.py:1260-1261`). Without `cdp_url`, launches Chromium as subprocess (`browser/watchdogs/local_browser_watchdog.py:122-123`). Harness pattern: PW launches Chromium with `--remote-debugging-port`, browser-use attaches. CDP multi-session is legal; risks: both drivers see each other's tabs; PW auto-waiting vs agent input mid-trace.

## 2. Action space & extensibility
- Built-ins (`tools/service.py:442+`): search (just DuckDuckGo/Google/Bing URL nav, `:463-487`), navigate, go_back, wait, click (index or coordinate), input, upload_file, tab switch/close, extract (LLM), search_page, find_elements, scroll, send_keys, find_text, screenshot, save_as_pdf, dropdown ops, file-system read/write, `evaluate` (arbitrary JS — exclude for probes; `registry.exclude_action`, `tools/registry/service.py:41`).
- **Custom actions**: `@tools.registry.action('desc', param_model=..., allowed_domains=[...])` (`tools/service.py:2088-2093`; impl `registry/service.py:290-303`); Pydantic params; framework objects injected by name (`:56-72`); auto-added to the LLM action schema (`registry/service.py:507`; `agent/views.py:419-431`). A `report_ux_friction` action is ~20 lines.
- **Structured completion**: `output_model_schema=MyModel` (`agent/service.py:166,362-363`) swaps `done` to `StructuredOutputAction[MyModel]` (`tools/service.py:1998-2031`); retrieve via `history.structured_output` (`agent/views.py:918`).

## 3. Determinism & replay
**No determinism, only replay-with-heuristics.** `rerun_history()`/`load_and_rerun()` (`agent/service.py:3092,3861`) replays saved history LLM-free for most actions; element re-binding = 5-level cascading fuzzy match: exact `element_hash` → `stable_hash` → XPath → AX-name → unique attribute (`service.py:3518-3534`). Laced with flakiness workarounds: exponential backoff per step (`:3204-3257`), skip-redundant-retry (`:3187-3199`), dropdown re-open heuristics (`:3218-3241`), `wait_for_elements` polling (`:3101,3406-3431`), `extract` re-executed with live LLM (`:3444-3467`), and an **AI-generated rerun summary judging its own success** (`RerunSummaryAction`, `agent/views.py:352-359`; `service.py:3263-3266`). No action/decision caching. Use `rerun_history` as a cheap smoke lane at most — investigate, don't block.

## 4. Observability & evidence
- **Per-step** (`AgentHistory`, `agent/views.py:488-495`): full model_output, all ActionResults (errors, extracted_content, attachments — `views.py:307`), `BrowserStateHistory` (url/title/tabs/interacted elements with xpath/hashes/ax_name/screenshot path — `browser/views.py:114-131`), timing (`views.py:362-373`). Screenshots to disk per step (`browser_use/screenshots/service.py:16-37`; `agent/service.py:735,1746-1752`).
- **Save/load** with redaction hooks (`agent/views.py:627,695,550`); mining accessors `urls()/errors()/model_thoughts()/action_history()/extracted_content()/screenshot_paths()` (`views.py:707-887`).
- **GIF** (`browser_use/agent/gif.py:35`); **video** via `record_video_dir` (`browser/video_recorder.py:32`; `profile.py:376,712`).
- **Network**: real CDP HAR recorder with bodies — `record_har_path` (`profile.py:375`; watchdog `har_recording_watchdog.py:144,210,283,381,427,489`). "No 5xx" oracle = HAR parsing.
- **Console: gap** — no `Runtime.consoleAPICalled`/`Log.entryAdded` capture; raw `cdp_client` exposed (`session.py:1307`; `get_or_create_cdp_session`, `:1448`) so the harness adds its own (~50 lines). `actor` module = small PW-style Page API over same plumbing (`browser_use/actor/page.py`).
- **Cost**: `TokenCost` per-model pricing + usage on history (`browser_use/tokens/service.py:49,221,264,423`; `calculate_cost=True`).
- **Phone-home**: PostHog telemetry **on by default** (`browser_use/config.py:58-59`; `telemetry/service.py:39-46`); cloud-sync defaults to the telemetry flag (`config.py:62-63`), transmits only when authenticated (`sync/service.py:41-52`) but step events would include screenshots and goals (`agent/cloud_events.py:117-130`). Set `ANONYMIZED_TELEMETRY=false`, `BROWSER_USE_CLOUD_SYNC=false`.

## 5. LLM integration
- **Providers**: first-party Anthropic, OpenAI, Google, Bedrock, Azure, Groq, Cerebras, DeepSeek, Mistral, Ollama, OpenRouter, Vercel, OCI, LiteLLM + hosted `ChatBrowserUse` (`browser_use/llm/*`; `anthropic==0.76.0` pinned, `pyproject.toml:44`). Abstraction = `BaseChatModel.ainvoke(messages, output_format)` Protocol (`llm/base.py:18-44`).
- **Structured output**: Anthropic client forces a single schema-named tool, `tool_choice={'type':'tool'}`, Pydantic-validated (`llm/anthropic/chat.py:349-376,283-291`); parse-failure retries (`agent/service.py:1176`); `llm_timeout`/`step_timeout`.
- **Vision optional**: `use_vision=True|False|'auto'` — with False, screenshots never attached to messages; DOM/AX text only (`agent/message_manager/service.py:427-475`); screenshots still saved for evidence.
- **Caution**: `use_judge=True` **by default** — an extra LLM judge over the trace at end of every run (`agent/service.py:184,254-255`; `agent/judge.py`; `history.judgement()`, `views.py:744`). Disable or quarantine from gates.

## 6. Tests & CI
- ~82 files under `tests/ci` (navigation, tabs, cross-origin iframes, screenshots, DOM serialization, dropdowns/autocomplete/radios, watchdogs, replay features, multi-action guards, LLM retries) against local `pytest-httpserver` with mocked LLMs (`tests/ci/conftest.py:14,176-185`) — good template for your fixtures.
- CI: one matrix job per test file, 4–8 min timeouts, **every test wrapped in `nick-fields/retry` with `retry_on: error`** (`test.yaml:84,175-181,247-251`) — they fight flakiness with retries, not elimination.
- Agent quality measured off-repo: `eval-on-pr.yml` posts SHA to a private eval platform (`secrets.EVAL_PLATFORM_URL`, `InteractionTasks_v8`); not locally reproducible.

## 7. Maturity
- **Cadence**: 0.12.7 (2026-05-18) → 0.13.3 (2026-07-01); 234 commits since 2026-05-01; no in-repo CHANGELOG; docs off-repo. Breaking-change history real: LangChain removed, Playwright→CDP, **index contract changed (sequential→backendNodeId) within this two-month window**, `Controller`→`Tools` rename. Pin exact versions.
- **Contributors** (shallow-window): Saurav Panda 114, Laith Weinberger 54+35, Magnus Müller 42+12, Gregor Žunič 23 — ~4 employees dominate.
- **Open-core gravity**: cloud browser (`browser/cloud/`), cloud sync (`sync/`), hosted LLM (`llm/browser_use/chat.py:31-42`), `browser-use-sdk` + `browser-harness` pinned deps (`pyproject.toml:57-58`), private eval platform, `CLOUD.md`. OSS core functional standalone today.
- **Hygiene**: MIT; Python ≥3.11 (`pyproject.toml:6`); 38 TODO/FIXMEs (low for size); candid hacks (`dom/views.py:981`); `agent/service.py` 4,143 lines, `browser/session.py` 4,046 lines; heavy dependency footprint (all LLM SDKs unconditional, posthog, reportlab…).

## 8. Testing-fit: pytest probe blueprint, gaps, effort, risk
1. **Harness owns the browser** (PW `launch_persistent_context(args=['--remote-debugging-port=0'])` for traces, or bare subprocess if HAR+screenshots+video suffice). `BrowserSession(cdp_url=..., keep_alive=True)`. Own CDP session for console.
2. **Hermetic agent**: `Agent(task=intent, llm=ChatAnthropic(...), browser_session=..., output_model_schema=ProbeResult, use_judge=False, calculate_cost=True, generate_gif=...)`; `record_har_path`; telemetry/sync env-off; `exclude_action('evaluate')`, `exclude_action('search')`; register `report_ux_friction`.
3. **Deterministic oracles after run()** — DB fixtures; HAR 5xx/4xx + forbidden hosts; console errors from own listener; final URL from `history.urls()[-1]`.
4. **Trend mining**: `history.save_to_file()` + screenshots + GIF as CI artifacts; extract structured_output, `total_duration_seconds()`, `number_of_steps()`, usage/cost, errors, loop-detector nudges, friction events into a per-commit metrics table.
5. Optional `rerun_history` smoke lane — report, don't gate.

**Gaps**: no PW trace of agent actions (substitute HAR + screenshots + video + history, or PW-owns-browser with page-level-only trace); no console capture (build it); no deterministic mode (by design); no local reproduction of their benchmarks; version-churn risk (pin + own regression suite before bumps).

**Effort**: 2–4 days for a first probe fixture; ~0.5 day per version bump. **Risk**: low for the probe lane; moderate maintenance; near-zero release-integrity risk *provided* deterministic oracles stay wholly outside browser-use.
