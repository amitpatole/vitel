# vitel — Vitals for AI Agents

> **Problem:** AI agents ship code and call it *done* without ever feeling whether the running
> system is healthy — latency, errors, saturation, error budget.
> **Result:** vitel gives them **interoception** — turn telemetry into a `pass` / `warn` / `fail`
> verdict, so the agent **won't claim done while vitals are failing.**

```bash
pip install vitel
vitel demo                       # no API key required
```

`vitel demo` grades a synthetic degrading service, prints a **FAIL** report (error budget burning —
deterministic, no LLM key), then grades the fixed version and prints **PASS**.

## What it does

| Capability | What you get |
|---|---|
| **Grade & report** | A machine verdict (`pass`/`warn`/`fail`) + issues **grounded in a `Metric`** (name, window, observed vs threshold, burn-rate) — deterministic, no key needed. |
| **[Match an SLO](quickstart.md)** | Grade telemetry against an `SLO` / error budget — `must: error_rate < 1%`, `must: error_budget_remaining > 20%`, `should: p99(latency_ms) < 300ms`. |
| **Analyze & critique** | `analyze` adds anomaly detection and an optional LLM critique (local Ollama) — egress only here; `check` stays offline. |
| **Watch over time** | `watch` grades behavior over a window — slow latency regression, resource leak, error spike, flatline/liveness. |
| **Vitals → brain handoff** | A distilled `{perceived, next_action, todo}` signal any agent/brain acts on. |

## Where to go next

<div class="grid cards" markdown>

- :material-rocket-launch: **[Quickstart](quickstart.md)** — install, first grade, the demo.
- :material-shield-check: **[Integration](integration.md)** — CI deploy-gate + Verel registration.
- :material-api: **[API](api.md)** — `check` · `analyze` · `watch` · `render` · `perceive`.

</div>

## Deterministic by construction

`check` never touches the network — thresholds, SLO conformance and error-budget burn-rate are
computed entirely from the series you give it. Egress happens **only** on `analyze` (and only to a
backend you name), and on the metric backends you opt into. The base install is light (JSON/CSV +
thresholds, no heavy deps) — sources live behind extras: `[prometheus]`, `[otel]`, `[cloud]`,
`[psutil]`.

## Eyes, ears, brain & vitals

vitel is the **vitals / interoception** sense. It pairs with
**[AgentVision](https://github.com/amitpatole/agent-vision)** (eyes — confirms it *renders*),
**[Audel](https://github.com/amitpatole/audel)** (ears — confirms it *sounds right*), and
**[Verel](https://github.com/amitpatole/verel)** (the brain — *nothing is "done" until a grader
returns a verdict*). All four speak the shared
**[agentsensory](https://github.com/amitpatole/agentsensory)** contract — one `Verdict`, one
`Report`, one `Handoff`. **vitel confirms the running system is actually healthy.**
