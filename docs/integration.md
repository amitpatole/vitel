# Integrating vitel: CI deploy-gate & Verel registration

vitel turns telemetry into a `pass` / `warn` / `fail` verdict. Two integrations make that verdict
*block* bad releases.

## 1. CI deploy-gate — block a release on error-budget burn

`vitel check` exits non-zero on `fail`, so it gates a pipeline with no glue code.

**Exit codes:** `0` = pass (and warn), `1` = fail, `2` = usage/source error. Add `--warn-as-fail`
to also block on `warn` (a stricter gate).

```yaml
# .github/workflows/deploy.yml (excerpt) — see examples/ci/deploy-gate.yml
- name: Deploy
  run: ./deploy.sh

- name: Post-deploy vitals gate
  run: |
    pip install "vitel[prometheus]"
    # pull post-rollout vitals and fail the deploy if the budget is burning
    vitel check "$PROM_QUERY" \
      --backend prometheus \
      --expect "availability 99.9%" \
      --expect "must: error_budget_remaining > 20%" \
      --expect "should: p99(latency_ms) < 300ms" \
      --window 600
  env:
    VITEL_PROMETHEUS_URL: ${{ secrets.PROMETHEUS_URL }}
```

If post-deploy vitals violate a `must:` threshold (or burn the error budget), the step exits `1` and
the job fails — the rollout is gated. For a file/exported-metrics source, point `vitel check` at a
JSON/CSV file or a `/metrics` URL (`--backend scrape`) instead.

## 2. Register vitel as a Verel sense

Verel withholds "done" until its required senses return a passing verdict. vitel plugs into Verel's
verdict bus as the **vitals** sense.

### The afferent signal

vitel implements `agentsensory.Sense` (`vitel.Vitals`) and every grade distills to a `Handoff`:

```python
import asyncio
from vitel import perceive
from vitel.slo import SLO

slo = SLO.from_inputs(expect=["availability 99.9%", "must: error_budget_remaining > 20%"])
handoff = asyncio.run(perceive(POST_DEPLOY_METRICS, slo=slo))

handoff.perceived      # Verdict.FAIL when the budget is blown
handoff.next_action    # NextAction.REVISE  (never DONE on a failing verdict)
handoff.todo           # actionable items the brain should resolve
```

Because a failing verdict yields `next_action = REVISE` (and a passing one `DONE`), Verel's gate
**cannot close a deploy task** while vitals are failing.

### Trust tier

- `check` / `watch` are **deterministic, grounded graders** → they may **block** (precise gate).
- `analyze`'s LLM critique is **advisory** → Verel clamps it to `≤ warn` (informs, never blocks),
  matching Verel's "precise gates, advisory informs" reducer.

### Wiring (lives in the Verel repo)

Verel mounts vitel either over MCP (`vitel-mcp`: `vitals_check` / `vitals_watch` / `vitals_status`)
or by importing `vitel.Vitals`. A ready-to-drop recipe is in
[`examples/verel/post_deploy_vitals.recipe.json`](../examples/verel/post_deploy_vitals.recipe.json):
it triggers a post-deploy `vitals_check`, treats a `fail` verdict as a blocking gate, and lists the
remediation skill. Register it in Verel's sense/recipe registry (per the Verel repo's instructions).
