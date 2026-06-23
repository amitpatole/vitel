# vitel — KICKOFF (own repo · own workspace · build after agentsensory)

> ❤️ **Vitals / interoception** — graded observability. `pass/warn/fail` on metrics, SLOs, error budgets.
> Highest software-first ROI: mostly deterministic, strongest SRE/DevOps hook, and the robot's battery/temp
> organ later.

## Repo & contract (read first)
Separate repo / separate Claude Code workspace — this file is self-contained; you do **not** need sibling
repos checked out. Depend on the shared contract **`agentsensory`** (its own package; source of truth):
`pip install "agentsensory>=0.1,<0.2"` — or pre-release `pip install "agentsensory @ git+https://github.com/amitpatole/agentsensory@<tag>"` — or local `uv pip install -e ../agentsensory`.

Code against (don't redefine): `from agentsensory import Verdict, ReportBase, IssueBase, Conformance, Brief, Handoff, Sense`.
`Sense` = async `analyze(source, **kwargs) -> ReportBase` (the only protocol method); vitel adds
`check/watch/render`. `ReportBase.to_handoff()`, `.issue_signature()`;
`Brief.from_inputs(text=…, expect=["must: …","should: …"])`. Validate output by Pydantic round-trip
(`Report.model_validate_json(r.model_dump_json())`); subclass `ReportBase`/`IssueBase` for vitals fields.
**House style (all organs):** `src/` layout · hatchling · pydantic · `py.typed` · async · light base wheel,
heavy deps behind extras + lazy-imported · entry-point backend registry · CLI · MCP · REST · Skill ·
`vitel demo` (broken → grounded FAIL → fixed → PASS, no API key) + `vitel doctor` · `Settings` env prefix
`VITEL_` · Trusted Publishing → TestPyPI → PyPI · register with Verel (wiring lives in the Verel repo).

## Charter
The agent's sense of **internal state and the health of the system under its care**. Turns telemetry into a
verdict: *are vitals nominal, or about to fail?* Drop into CI/CD to **gate a release on error-budget burn**,
or run as a Verel sense so the brain won't mark a deploy "done" until post-rollout vitals confirm health.

## Grades / inputs
PromQL/Prometheus, OpenTelemetry (OTLP), StatsD, CloudWatch, Datadog, k8s metrics, `/metrics` endpoints,
process self-stats (psutil), or plain JSON/CSV series. **`Brief` analog = `SLO`/`BudgetSpec`:**
`must: p99_latency < 300ms`, `must: error_rate < 1%`, `must: error_budget_remaining > 20%`, `should: cpu < 70%`.

## API (implements `agentsensory.Sense`)
| Fn | Behavior |
|---|---|
| `check(source, *, slo=None) -> Report` | deterministic threshold / SLO / burn-rate eval, no LLM — **main path** |
| `analyze(source, *, slo=None, backend=None) -> Report` | adds anomaly/LLM critique + non-deterministic claims |
| `watch(source, *, window, interval) -> Report` | poll/stream over time; trend, ongoing degradation, liveness |
| `render(source) -> RenderResult` | normalized series + rates/percentiles/burn-rate (the trustworthy signal) |

## Issue kinds (grounded in `Metric`)
`slo_violation` · `error_budget_burn` · `saturation` (cpu/mem/disk/conn-pool) · `latency_regression` ·
`error_spike` · `crashloop` · `resource_leak` (monotonic growth) · `flatline`/`no_data` · `quota_exhaustion`.

## Packaging
Base = JSON/CSV series + thresholds (no heavy deps). Extras: `vitel[prometheus]`, `vitel[otel]`,
`vitel[cloud]` (datadog/cloudwatch), `vitel[psutil]`, `vitel[all]`. CLI/MCP: `vitel check|watch|analyze|demo|doctor`; MCP `vitals_check/watch/status`.

## Phases (stop at each acceptance check)
- **V0** scaffold on `agentsensory`; `SLO`/`BudgetSpec`; CSV/JSON source. **Accept:** `vitel doctor` ok; `check` fails a JSON series violating a `must:` threshold; output round-trips through Pydantic validation.
- **V1** Prometheus/PromQL + burn-rate math; `vitel demo`. **Accept:** demo trips error-budget burn → FAIL → fixed → PASS, no API key.
- **V2** OTLP + cloud backends (extras) + `psutil` self-vitals. **Accept:** same `check` grades a live `/metrics` endpoint.
- **V3** `watch` trends/degradation; `analyze` anomaly/LLM critique. **Accept:** `watch` flags a slow latency regression.
- **V4** Verel registration recipe; CI gate (block deploy on budget burn). **Accept:** Verel withholds "done" on a failing post-deploy vitals verdict.

## Paste into THIS workspace's Claude Code
> Build **`vitel`** — the vitals/interoception sense: graded observability returning `pass/warn/fail` on
> metrics, SLOs and error budgets, issues grounded in `Metric` (name, window, observed vs threshold,
> burn-rate). Implement `agentsensory.Sense` (`check/analyze/watch/render -> Report`); `check` is deterministic
> and the main path. `pip install agentsensory` and import its types — don't redefine them. Light base
> (JSON/CSV + thresholds); extras `[prometheus]`,`[otel]`,`[cloud]`,`[psutil]`, lazy-imported.
> `SLO.from_inputs(expect=["must: error_budget_remaining > 20%", ...])`. Ship `vitel demo` (synthetic
> degrading service → budget-burn FAIL → fixed → PASS, no API key) + `doctor`; CLI + MCP; tests use
> `agentsensory.testing`. Start at V0, stop at each acceptance check.
