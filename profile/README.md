# AURA Lab — how we file work

GitHub is a flat list. This is the legend. A new repo walks **top to bottom** and stops at the first match.

```
AURA
├── research    what we find out
├── teaching    what we teach
├── products    software with users outside one mission
├── people      who is / was in the lab
├── identity    how outsiders recognize AURA
└── ops         how the lab runs itself
```

## Walk-in test

1. **people** — the repo *is* a person.
2. **research** or **teaching** — it *is* that mission’s content, or software whose **only** users are that mission.
3. **products** — released software, more than one mission **or** users outside the lab.
4. **identity** — its job is making AURA recognizable.
5. **ops** — it automates how the lab works **and failed every test above**.

Ops is a **negative** test, not “anything Claude-shaped.”

## Naming

Path with `/` becomes `-` on GitHub.

| Path | Repo |
|---|---|
| `research/<slug>` | `research-<slug>` |
| `teaching/<course>/<year>` | `teaching-<course>-<year>` |
| `teaching/<course>/<year>/<netid>` | `teaching-<course>-<year>-<netid>` |
| `teaching/coll100/codelab` | `teaching-coll100-codelab` |
| `project/<name>/…` | `project-<name>-…` |
| `student/aura\|grad\|undergrad/<name>` | `student-aura\|grad\|undergrad-<name>` |
| `design/kit` | `design-kit` |
| `design/kit/logos` | `design-kit-logos` |
| `design/slides` | `design-slides` |
| `web/<site>` | `web-<site>` |
| `ops/<tool>` | `ops-<tool>` |
| `ops/skills` | `skills` |

Do **not** put a venue in a research name (a reject makes the name a lie).  
Do **not** put a year on a platform (codelab.sh is not “2026”).  
Kit owns tokens; slides consume them; logos are marks only.

## Skills

**Default:** [`skills`](https://github.com/aura-lab-wm/skills), under a domain folder (`research/`, `workday/`, `macos/`, …).

**Exception:** if the skill *is* the product, it lives in that product. `skills/elsewhere/` keeps the pointer.

Today: lecture skill → [`design-slides`](https://github.com/aura-lab-wm/design-slides).

## Ops (same shape as the other rooms)

```
ops/skills           skills
ops/reimbursement    ops-reimbursement
ops/telemetrify      ops-telemetrify
ops/toast            ops-toast
ops/key-agent        ops-key-agent
ops/phd-defence      ops-phd-defence
```

A hook that exists only to enforce `design-kit` is **identity**, not ops. Put it in `design-kit` (or `design-kit-hook`) and point from `skills/elsewhere/`.

## Adding a repo

1. Run the walk-in test. Do not skip to ops.
2. Name it from the table.
3. One GitHub **topic** = the room (`research`, `teaching`, `products`, `people`, `identity`, `ops`).
4. If it is a skill, follow Skills above.

## Live map

| Room | Repos |
|---|---|
| research | `swebench-dominance` *(rename to `research-swebench-dominance`)* |
| teaching | `teaching-coll100-codelab`, `teaching-coll100-2026`, `teaching-genai4se-2026` + netid copies |
| products | `project-rocco-code`, `project-rocco-web`, `project-rocco-student-kit`, `project-auracron` |
| people | `student-aura-*` |
| identity | `web-auralab`, `design-kit`, `design-kit-logos`, `design-slides` |
| ops | `skills`, `ops-reimbursement`, `ops-telemetrify`, `ops-toast`, `ops-key-agent`, `ops-phd-defence` |
