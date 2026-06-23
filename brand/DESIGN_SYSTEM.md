# vitel branding — Trio "Warm Paper"

vitel uses the shared **Warm Paper** design system across the eyes/ears/vitals/brain ecosystem.
Everything is identical between organs — light editorial paper, `Source Serif 4` display headings,
`Inter` body, `JetBrains Mono` code, hairline rules, no gradients/glows, and the recurring
`— amitpatole` maker's mark — **except one per-sense accent.**

## Per-sense accents

| Sense | Project | Accent | Accent-ink |
|---|---|---|---|
| Eyes | AgentVision | `#3a8a99` | `#256b78` |
| Ears | Audel | `#c4943f` | `#90641a` |
| **Vitals** | **vitel** | **`#c2453f`** | **`#93302b`** |
| Brain | Verel | `#7a72b5` | — |

vitel's **Vital Crimson** fills the warm-red slot the trio left open and reads as the
vitals/heartbeat theme. The accent appears only as: the H1 hairline tick, links/CTA, the admonition
left-rule, the social-card spine, and the footer signature — one quiet gesture per surface.

## Surfaces (all retrofit to match)

- **Docs** — `docs/stylesheets/extra.css` (canonical Warm Paper; only the two `--accent` lines differ).
- **Social card** — `social_vitel.html` → `og-vitel.png` (1280×640), referenced by the Space `og:image`.
- **HF Space** — `space/index.html` + `space/README.md` (static SDK).

## Tokens

The canonical token source is `extra.css` / `social_vitel.html` `:root`. Background `#f7f5f1`,
surface `#fffdf9`, panel `#efece4`, ink `#1b1a17`, muted `#6b6862`, faint `#918d84`, rule `#e3ded4`.
