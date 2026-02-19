# Tower Upgrade Advisor - Project Brief

## Goal
Build a trustworthy local tool that recommends the SINGLE best NEXT permanent upgrade (coin-based) in the game "The Tower" (idle tower defense) after each run.

## Scope V1
- Permanent upgrades only (coin upgrades from the Workshop)
- No in-run cash upgrades
- Daily use on macOS
- Local-first UI (fast, stable)
- Multiple saved profiles/builds
- Upgrades listed in the same order/grouping as in-game and the reference tool
- Show transparent math: coin cost, delta effect/value, score, ranking

## Non-Goals V1
- Mobile UX
- Publishing/hosting (optional later)
- Multi-step budget plans
- Full game simulation
- In-run cash upgrades

## Reference Tool
- https://tower-workshop-calculator.netlify.app/
- JS SPA (Create React App on Netlify)
- No public GitHub repository found
- We replicate functionality with better reliability and validation
- We do NOT copy UI design

## Data Source Reality
- Reference site requires JavaScript execution (cannot scrape with simple HTTP)
- Fandom wiki blocks programmatic access (403)
- Extraction priority: browser automation > JS bundle reverse-engineering > assisted manual import
- All data must pass automated integrity checks

## Trust Requirements
- Every recommendation must be reproducible from stored data + deterministic code
- Recommendation logic must be explicit and swappable
- Start simple: marginal benefit per coin
- Interface ready for future improvements
- Tests (unit + data validation) required; failing tests block changes

## Team Roles
1. **Architect** - repo layout, stack decision, integration plan
2. **Data Engineer** - extraction strategy, normalization schema, validation rules
3. **Algorithm Engineer** - scoring interface, explainable ROI logic, extensibility
4. **UI Engineer** - minimal local UI, upgrade ordering/grouping, profile handling
5. **Reliability Engineer** - tests, CI recommendations, failure modes, guardrails
