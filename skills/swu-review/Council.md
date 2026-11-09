# Council Review

*Strategic deck review tool for Star Wars: Unlimited Premier decks.*

> **Note:** Council reviews are **optional strategic commentary outside** the analysis artefacts.
> `analysis.json` and `report.md` never contain council recommendations, cuts/adds, matchups or play lines.
> Those are listed in `out_of_scope[]`.

## Purpose

The council provides multi-perspective strategic review of SWU Premier decks,
supplementing the mechanical analysis produced by the analysis pipeline.

## When to Use

- Optional strategic commentary across multiple reviewers
- When you want diverse perspectives on a deck's strengths/weaknesses
- For identifying flexible slots, strategic objectives, and gameplay goals
- Not for mechanical legality or composition analysis (covered by the pipeline)

## Council Review Protocol

### 1. Capture the Plan First
Before recommending strategic insights, summarize:
- **Objective**: What is the deck trying to achieve?
- **Target Line**: What is the primary game plan?
- **Matchups**: What are the expected matchups?
- **Flexible Slots**: Which cards could be swapped based on matchup?

### 2. List Perspectives
Each council member provides their perspective:

```
## Reviewer 1: [Name/Style]
- **Objective**: ...
- **Target Line**: ...
- **Matchup Focus**: ...
- **Flexible Slots**: ...
- **Strengths**: ...
- **Weaknesses**: ...

## Reviewer 2: [Name/Style]
- **Objective**: ...
- **Target Line**: ...
- **Matchup Focus**: ...
- **Flexible Slots**: ...
- **Strengths**: ...
- **Weaknesses**: ...
```

### 3. Identify Consensus and Disagreements
```
## Agreement Points
- Point 1 accepted by all reviewers
- Point 2 accepted by all reviewers

## Points of Contention
- Reviewer 1: [view]
- Reviewer 2: [view]
- Reviewer 3: [view]

## Compromise/Resolution
- Agreed approach: ...
```

### 4. Identify Flexible Slots
For each flexible slot, explain:
- **Slot out**: Which card could be removed
- **Role lost/gained**: What changes
- **Sequence enabled/lost**: What combos interact
- **Matchup relevance**: Which matchups this affects
- **Opportunity cost**: What you give up
- **Confidence level**: High/Medium/Low

### 5. Transparent Council
- List all reviewers and their styles/backgrounds
- State explicit points of consensus
- State explicit points of disagreement
- Note any uncertainties or areas needing further research

## Council vs Analysis Pipeline

| Aspect | Council Review | Analysis Pipeline |
|--------|---------------|-------------------|
| **Output** | Strategic commentary | `analysis.json` + `report.md` |
| **Contains** | Strategy, matchups, flexible slots | Legality, composition, findings, limitations |
| **Recommendations** | Allowed (strategic) | Not allowed (out of scope) |
| **Matchups** | Allowed (discussed) | Not modeled |
| **Play Lines** | Allowed (discussed) | Not simulated |
| **Cuts/Adds** | Allowed (strategic) | Not recommended |

## Council Review Example

```markdown
# Council Review: [Deck Name]

## Reviewers
- **Alice**: Control player, experienced with SWU since 2023
- **Bob**: Aggro player, tournament-focused
- **Carol**: Balanced player, casual but competitive

## Objectives
- **Alice**: Value engine, late-game topdecks
- **Bob**: Early pressure, resource denial  
- **Carol**: Balanced gameplan, fun factor

## Consensus
- **Agreed**: Poggle the Lesser is a strong engine card
- **Agreed**: Need more Space arena tech for matchup

## Points of Contention
- **Bob**: Wants more aggro threats, wants to cut [card]
- **Alice**: Wants more control tools, wants to keep [card]
- **Carol**: Prefers balanced approach, suggests [card] as compromise

## Flexible Slots
| Slot | Options | Rationale |
|------|---------|-----------|
| **3x [Card A]** | Cut 1 for [Tech Card] | Aggro matchup tech |
| **2x [Card B]** | Keep/Replace with [Card C] | Depends on matchup |
| **1x [Card D]** | Always include | Engine consistency |

## Strategic Recommendations
- **vs Aggro**: [specific advice]
- **vs Control**: [specific advice]
- **vs Combo**: [specific advice]

## Uncertainties
- Interaction with errata post-2026
- Rotation with future sets
- Optimal resource curve for current meta
```

## Council Review Checklist

- [ ] All reviewers listed with their style/focus
- [ ] Objectives clearly stated per reviewer
- [ ] Consensus points identified
- [ ] Points of contention explicitly noted
- [ ] Flexible slots analyzed with rationale
- [ ] Strategic recommendations per matchup
- [ ] Uncertainties documented
- [ ] No mechanical recommendations in analysis artefacts
- [ ] Council noted as separate from `analysis.json`/`report.md`

## Integration with Analysis Pipeline

The council review **complements** but **does not modify** the analysis pipeline output:

```
analysis.json + report.md  ← Mechanical analysis (legality, composition, findings)
     ↑
     |
Council Review  ← Strategic commentary (outside analysis artefacts)
     ↓
Strategic deck recommendations
```

## When NOT to Use Council Review

- Single-deck analysis without need for multiple perspectives
- When only mechanical legality/composition analysis is needed
- When time is limited and only the pipeline output is required
- For tournament preparation requiring strict legality analysis

---

*This council review framework is designed to work alongside the SWU Review mechanical analysis, providing strategic human commentary while the pipeline handles the objective metrics.*