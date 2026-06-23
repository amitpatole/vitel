# vitel

**Vitals / interoception for AI agents** — graded observability that turns telemetry (metrics, SLOs,
error budgets) into a `pass` / `warn` / `fail` verdict, with every finding grounded in a `Metric`
(name, window, observed vs threshold, burn-rate).

vitel is a *sense organ* built on the shared [`agentsensory`](https://github.com/amitpatole/agentsensory)
contract — sibling to **AgentVision** (eyes), **Audel** (ears) and **Verel** (brain). Drop it into
CI/CD to **gate a release on error-budget burn**, or run it as a Verel sense so the brain won't mark a
deploy "done" until post-rollout vitals confirm health.

## What it does

| Function | Behavior |
|---|---|
| `check(source, *, slo=None)` | deterministic threshold / SLO / burn-rate evaluation, no LLM — **main path** |
| `analyze(source, *, slo=None, backend=None)` | adds anomaly / LLM critique on top of `check` |
| `watch(source, *, window, interval)` | poll / stream over time; trend, degradation, liveness |
| `render(source)` | normalized series + rates / percentiles / burn-rate (the trustworthy signal) |

## Install

```bash
pip install vitel                      # light base: JSON/CSV series + thresholds
pip install "vitel[prometheus]"        # PromQL / Prometheus
pip install "vitel[otel]"              # OpenTelemetry (OTLP)
pip install "vitel[cloud]"             # Datadog / CloudWatch
pip install "vitel[psutil]"            # process self-vitals
pip install "vitel[all]"               # everything
```

## License

MIT © Amit Patole
