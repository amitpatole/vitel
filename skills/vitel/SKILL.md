---
name: vitel
description: >
  Grade service vitals (metrics, SLOs, error budgets) into a pass/warn/fail verdict. Use when asked
  to check service health, gate a release/deploy on error-budget burn, evaluate an SLO, watch for a
  latency regression, or decide whether a rollout is healthy enough to call "done". Works on JSON/CSV
  series, a Prometheus/PromQL server, a /metrics endpoint, OTLP exports, Datadog/CloudWatch, or the
  process's own psutil vitals.
---

# vitel — vitals / interoception sense

vitel turns telemetry into a graded verdict whose findings are grounded in a `Metric` (name, window,
observed vs threshold, burn-rate). `check` is deterministic (no LLM); `analyze` adds anomaly + LLM
critique; `watch` looks at trends over time; `perceive` returns the brain-ready handoff.

## When to use
- "Is this service healthy / are vitals nominal?" → `vitel check`
- "Gate this deploy on the error budget." → `vitel check ... --expect "must: error_budget_remaining > 20%"` (exit 1 = block)
- "Did latency regress?" → `vitel watch`
- "Should the agent mark this deploy done?" → `vitel perceive` (next_action `done`/`revise`/`review`)

## CLI
```bash
vitel doctor                       # check install + backends + extras
vitel demo                         # synthetic budget-burn FAIL → fixed → PASS (no API key)

# Grade an SLO (exit 0 pass/warn, 1 fail, 2 error; add --warn-as-fail to block on warn too)
vitel check metrics.json --expect "must: error_rate < 1%" --expect "should: p99(latency_ms) < 300ms"

# Error budget against an availability target
vitel check metrics.json --expect "availability 99.9%" --expect "must: error_budget_remaining > 20%"

# Live sources
vitel check http://localhost:9090/metrics --backend scrape --expect "must: error_rate < 1%"
vitel check 'rate(errors[5m])' --backend prometheus --expect "availability 99.9%"  # VITEL_PROMETHEUS_URL

# Trends and the brain handoff
vitel watch series.csv --window 600 --expect "should: p99(latency_ms) < 300ms"
vitel perceive metrics.json --expect "must: error_budget_remaining > 20%"   # JSON Handoff
```

## Expectation grammar
`must:` / `should:` / `nice:` prefix + `metric  <|<=|>|>=|==  number[unit]`, optionally an aggregate:
`p99(latency_ms) < 300ms`, `error_rate < 1%` (`%`→ratio), `availability 99.9%` (sets the budget target),
derived: `error_budget_remaining > 20%`, `burn_rate < 14.4`.

## Programmatic / MCP
- Python: `from vitel import check, analyze, watch, perceive` (all async); `vitel.Vitals` implements `agentsensory.Sense`.
- MCP server `vitel-mcp`: tools `vitals_check`, `vitals_watch`, `vitals_status`, `vitals_render`, `vitals_analyze`, `perceive_handoff`, `doctor`.
- REST `vitel-serve`: loopback zero-config; off-loopback requires `VITEL_API_TOKEN`.
