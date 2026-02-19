# Tower Upgrade Advisor
## Game context, mechanics, and what this calculator is trying to do

This document exists so any model, agent, or teammate can understand:
- What the game loop is
- What the currencies and upgrades mean at a conceptual level
- What "best next upgrade" means for this project
- What is in scope and out of scope
- What must be treated as unknown until extracted from data

This is intentionally written as a stable, long-lived reference. If anything conflicts with extracted data or the game itself, the extracted data and observed in-game behavior win.

---

## 1) The game in plain terms

"The Tower" is an incremental tower defense style game where progression is built from repeated runs.

### The core loop
1. You start a run.
2. Enemies come in waves.
3. You earn resources from the run based on performance.
4. During the run you can buy temporary upgrades using a run currency.
5. After the run you spend a persistent currency on permanent upgrades.
6. Permanent upgrades make the next run stronger, which yields more resources, which funds more permanent upgrades.

This is a compounding loop.

### Two upgrade worlds
- In-run upgrades: bought with run currency, reset each run.
- Permanent upgrades: bought with persistent currency, carry over between runs.

This project starts with permanent upgrades only.

---

## 2) Currency and progression concepts

This section is conceptual. Exact formulas, values, and tables must come from extracted data.

### Persistent currency
- Typically called coins in community tools.
- Earned from runs.
- Spent on permanent upgrades.
- Permanent upgrades have levels.
- Each level has a cost and an effect.

### Run currency
- Often called cash in tools.
- Earned during a run.
- Spent on in-run upgrades.
- Resets each run.

### Why this matters for a calculator
A permanent upgrade is only "good" if it improves future runs enough to justify its coin cost.

The calculator must quantify that in a deterministic way using extracted values.

---

## 3) What "Workshop" means in this project

Community tools often refer to permanent upgrades as "Workshop" upgrades. The reference tool we are rebuilding is explicitly a workshop calculator.

Reference tool inspiration:
https://tower-workshop-calculator.netlify.app/

In this project:
- "Workshop upgrade" means a permanent upgrade purchased with coins.
- Each upgrade has:
  - A current level
  - A next level
  - A coin cost for the next level
  - A delta effect gained from buying the next level
  - A maximum level

If the game has other permanent systems such as labs, cards, modules, perks, or similar, they are not part of V1 unless the reference tool includes them in the same dataset we are extracting.

---

## 4) The actual goal of this project

### V1 goal
Given a player profile containing current workshop levels, compute and recommend:

- The single best next permanent upgrade to buy right now.

Also show:
- The top N alternatives
- The exact numbers used for scoring
- Why the recommendation won

### V1 scope
Included:
- Permanent upgrades only
- Single-step recommendation (next purchase)
- Multiple saved profiles or builds
- Local-first UI on macOS

Not included in V1:
- In-run cash recommendations
- Multi-step planning across many purchases
- Full run simulation
- Mobile-first UI
- Publishing or hosting

---

## 5) Why the existing online tool is not enough

The reference tool is useful but has issues:
- Laggy or slow performance
- Crashes
- Hard to trust if it silently fails
- Hard to extend

This project is a rebuild focused on:
- Speed
- Stability
- Explicit validation
- Transparent logic
- Local ownership of the dataset

---

## 6) What "best" means here

"Best" is not a vibe. It must be a measurable objective.

### What we can safely do in V1
We can score "best next upgrade" using only the extracted workshop data if we define a scoring method that is:
- Deterministic
- Explainable
- Transparent about assumptions
- Comparably scaled across upgrades

### Important warning about comparability
Many upgrades affect different dimensions that are not directly comparable without a model of the run:
- Offense
- Defense
- Economy
- Utility

If we do not have a full simulation, any single combined score is inherently assumption-heavy.

Therefore V1 must either:
- Provide category-based recommendations (best economy, best offense, best defense), plus an optional weighted blended recommendation
- Or replicate the reference tool’s ranking logic if it can be discovered and validated

No hidden weights. If weights exist, they must be visible and adjustable.

---

## 7) The scoring problem in one sentence

We are choosing among many candidate next purchases.

Each candidate has:
- Coin cost to buy
- Delta effect it adds
- A category or type
- Constraints (max level, prerequisites, etc)

We need a scoring function that maps a candidate to a number so candidates can be ranked.

### Scoring interface requirement
The scoring engine must be swappable.

Minimum deliverables:
- A scoring protocol or interface
- One default scoring implementation
- Clear output explanation showing how the score was computed

---

## 8) Data is the real project

If the extracted upgrade tables are wrong, the calculator is wrong.

This project must prioritize:
1. Data extraction correctness
2. Data normalization correctness
3. Validation and tests
4. Then UI

### Primary data source
The reference site:
https://tower-workshop-calculator.netlify.app/

The extraction plan must prioritize:
1. Find JSON endpoints or embedded JSON payloads
2. If needed, intercept network responses using browser automation
3. Only scrape the DOM as last resort

### Do not do this
- Do not manually transcribe numbers into code
- Do not allow any model to invent or "fill missing" values
- Do not accept partial extraction without explicitly documented gaps

---

## 9) Normalized dataset requirements

We need a normalized file that drives everything.

Suggested normalized row structure:
- upgrade_id: stable string key
- upgrade_name: display name
- category: offense, defense, economy, utility, or whatever the reference tool uses
- level: integer
- max_level: integer
- coin_cost: integer or decimal
- effect_value: numeric value representing the effect at this level or the delta for this level
- effect_unit: string such as percent, flat, multiplier
- notes: optional
- source: where this row came from

It is acceptable for the dataset to store both:
- absolute effect at each level
- delta effect between levels

But the schema must be explicit.

---

## 10) Data integrity and validation rules

These must run automatically and fail fast.

Minimum validation checks:
- No duplicate (upgrade_id, level)
- Levels are continuous from 0 or 1 up to max_level
- All numeric fields parse cleanly to numbers
- No human-formatted suffix strings leak into numeric fields, for example 1.2M, 3.4B
  - If the source uses these formats, parsing must convert them deterministically into raw numbers
- Cost and effect arrays align
- Upgrade ordering is preserved exactly as the reference tool displays, unless intentionally changed and documented

Optional sanity checks:
- Costs are generally non-decreasing with level when applicable
- Effects are generally non-decreasing when applicable

Note: Do not enforce monotonic rules globally if some upgrades intentionally break that pattern. If unknown, log the anomaly instead of hard failing, or gate it behind an allowlist.

---

## 11) Player profile requirements

A player profile is the user’s current workshop state.

Profile must store:
- profile_name
- last_updated_timestamp
- current_levels:
  - mapping from upgrade_id to current_level
- optional tags:
  - farm build
  - push build
  - balanced build

Profile storage requirements:
- Atomic writes to avoid corruption
- Human-readable JSON
- Easy export and import

---

## 12) UI requirements, minimal but usable daily

The UI must be built for speed and low friction.

Minimum UI:
- Profile selector
- A list of upgrades in the same order as the game or the reference tool
- A way to input current level per upgrade quickly
- Button: Recommend next upgrade
- Output:
  - Best next upgrade
  - Top alternatives
  - For each: coin cost, delta, score, category
  - Clear explanation of scoring

Avoid:
- spreadsheets
- command line only flows
- complex dashboards in V1

---

## 13) Engineering constraints and preferences

Environment:
- macOS
- VS Code
- Git repo
- Minimal setup friction

Human constraints:
- User does not want to manually edit code line by line
- Agents should create and modify files directly
- The repo must contain canonical context docs so the project does not rely on chat history

Subscription constraints:
- No new paid subscriptions beyond what is already available

---

## 14) Model behavior rules for this repo

If you are a model or agent working on this project, follow these rules.

### Data rules
- Never invent numbers, costs, effects, or max levels
- If data is missing, mark it as missing and fail validation unless the project explicitly supports partial data mode
- Always preserve provenance. Store how you derived a value.

### Logic rules
- Deterministic computations only
- No ML-based ranking in V1
- Scoring must be explainable, not a black box

### Documentation rules
- Any new assumption goes into docs/assumptions.md
- Any new decision goes into docs/decisions.md with rationale
- Any schema change updates docs/data_schema.md

### Testing rules
- Add tests for parsing, normalization, and scoring edge cases
- Add at least one golden test case where a small known dataset produces a stable ranking

---

## 15) Definition of done for V1

V1 is done when:
- We can extract the dataset from the reference tool reproducibly
- Validation passes with strong guarantees
- The UI loads profiles and accepts level input
- The app produces a ranked recommendation deterministically
- The app explains its score using real numbers from the dataset
- A user can run it daily without lag or crashes

---

## 16) Future roadmap, intentionally not implemented in V1

Potential V2 expansions:
- In-run cash upgrade recommendations
- Multi-step path planning, for example best next 10 purchases
- Patch-versioned datasets
- Calibration using observed run results
- A lightweight simulation mode, clearly marked as approximate

These must not contaminate V1’s trust.

---

## 17) Open unknowns that must be resolved by extraction

These are not to be guessed:
- The full list of workshop upgrades and their ordering
- Per-level coin cost tables
- Per-level effect tables
- Whether effects are absolute or delta in the reference tool
- Whether the reference tool encodes additional logic such as category weights or special cases

---

## 18) Project posture

This project optimizes for:
- Trust
- Stability
- Speed of daily use
- Extensibility without rewrites

It explicitly does not optimize for:
- Fancy UI
- Premature simulation
- Perfect optimization across all possible game states

Build the solid core first.

End of document.
