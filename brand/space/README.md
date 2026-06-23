---
title: vitel
emoji: ❤️
colorFrom: red
colorTo: gray
sdk: static
pinned: false
license: mit
short_description: Vitals for AI Agents — graded observability (pass/warn/fail)
---

# vitel — Vitals for AI Agents

Graded observability coding agents consume to feel whether the running system is healthy — turn
telemetry into a `pass`/`warn`/`fail` verdict grounded in a `Metric`, and **refuse to claim *done*
while vitals are failing.**

This Space is a static landing page. Use vitel from Python or the CLI:

```bash
pip install vitel
vitel demo          # budget-burn FAIL → fixed → PASS, no API key required
```

- **Docs:** https://amitpatole.github.io/vitel/
- **Source:** https://github.com/amitpatole/vitel
- **PyPI:** https://pypi.org/project/vitel/

Part of the eyes/ears/vitals/brain ecosystem with
[AgentVision](https://huggingface.co/spaces/amitpatole/AgentVision) (eyes),
[Audel](https://huggingface.co/spaces/amitpatole/audel) (ears) and
[Verel](https://huggingface.co/spaces/amitpatole/verel) (brain), sharing one contract,
[agentsensory](https://pypi.org/project/agentsensory/).
