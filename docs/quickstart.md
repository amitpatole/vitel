# Quickstart

## Install

```bash
pip install vitel                 # light base: JSON/CSV series + thresholds
pip install "vitel[prometheus]"   # PromQL / Prometheus + /metrics scrape (httpx)
pip install "vitel[otel]"         # OpenTelemetry (OTLP)
pip install "vitel[cloud]"        # Datadog / CloudWatch
pip install "vitel[psutil]"       # process self-vitals
pip install "vitel[all]"          # everything
```

Check the install:

```bash
vitel doctor
```

## First grade

vitel grades a source against an `SLO`. Sources can be a JSON/CSV file, inline JSON, a `/metrics`
URL, a PromQL query, an OTLP export, or `self` (psutil).

```bash
# inline JSON, two requirements
vitel check '{"metrics": {"error_rate": 0.05, "latency_ms": 520}}' \
  --expect "must: error_rate < 1%" \
  --expect "should: p99(latency_ms) < 300ms"
# → FAIL: vitals failing — 2 issues ... (exit code 1)
```

Exit codes make it a drop-in CI gate: `0` = pass (and warn), `1` = fail, `2` = error. Add
`--warn-as-fail` to block on `warn` too.

## Error budgets

Give an availability target and vitel computes burn-rate and remaining budget for you:

```bash
vitel check service.json \
  --expect "availability 99.9%" \
  --expect "must: error_budget_remaining > 20%"
```

## The expectation grammar

A requirement is `must:` / `should:` / `nice:` then `metric  OP  number[unit]`:

- `must: error_rate < 1%`        — `%` is read as a ratio (`0.01`)
- `must: p99(latency_ms) < 300ms` — aggregates: `p50/p90/p95/p99`, `max`, `min`, `mean`, `rate`, `last`
- `availability 99.9%`            — sets the error-budget target
- derived: `error_budget_remaining > 20%`, `burn_rate < 14.4`

`must` violations fail; `should` warns; `nice` never escalates the verdict.

## Live sources

```bash
# scrape a Prometheus/OpenMetrics endpoint
vitel check http://localhost:9090/metrics --backend scrape --expect "must: error_rate < 1%"

# PromQL range query (set VITEL_PROMETHEUS_URL)
VITEL_PROMETHEUS_URL=http://prom:9090 \
  vitel check 'sum(rate(errors[5m]))/sum(rate(requests[5m]))' --backend prometheus \
  --expect "availability 99.9%"

# the process's own vitals
vitel check self --backend psutil --expect "must: mem < 0.9"
```

## Watch for regressions

```bash
vitel watch series.csv --window 600 --expect "should: p99(latency_ms) < 300ms"
# flags a slow latency regression, resource leak, error spike, or flatline
```

## In Python

```python
import asyncio
from vitel import check, perceive
from vitel.slo import SLO

slo = SLO.from_inputs(expect=["availability 99.9%", "must: error_budget_remaining > 20%"])
report = asyncio.run(check("service.json", slo=slo))
print(report.verdict, report.summary)

# the brain-ready handoff (Verel won't mark done unless next_action == done)
handoff = asyncio.run(perceive("service.json", slo=slo))
print(handoff.perceived, handoff.next_action)
```
