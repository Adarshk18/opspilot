# 0001: Why OpsPilot

## Context
On-call engineers face alert fatigue, scattered tools, and documentation gaps.

## Decision
Build an AI on-call agent that diagnoses incidents in a target app, searches runbooks,
and runs fixes only with human approval.

## Alternatives considered
- Terminal-Bench agent: top-10 scores need paid frontier models.
- Live-website browser agent: unreliable and low success rates even for frontier systems.

## Consequences
We must build a realistic target app to break, and safety (sandboxing, approvals) is a core feature.