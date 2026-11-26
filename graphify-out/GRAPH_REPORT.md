# Graph Report - hackathon-2026  (2026-11-26)

## Corpus Check
- 3 files · ~459 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: (none) 2)

## Summary
- 14 nodes · 11 edges · 3 communities (2 shown, 1 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a02ef0b1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- hackathon-2026
- AGENTS.md

## God Nodes (most connected - your core abstractions)
1. `hackathon-2026` - 3 edges
2. `Project status (update when something important lands)` - 1 edges
3. `Stack` - 1 edges
4. `Git workflow (several people push to this repo at once)` - 1 edges
5. `Code` - 1 edges
6. `Secrets` - 1 edges
7. `Keep usage low` - 1 edges
8. `graphify (code knowledge graph in `graphify-out/`)` - 1 edges
9. `Setup` - 1 edges
10. `Graphify (code knowledge graph, saves AI tokens)` - 1 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Communities (3 total, 1 thin omitted)

### Community 1 - "hackathon-2026"
Cohesion: 0.50
Nodes (3): Graphify (code knowledge graph, saves AI tokens), hackathon-2026, Setup

### Community 2 - "AGENTS.md"
Cohesion: 0.22
Nodes (7): Code, Git workflow (several people push to this repo at once), graphify (code knowledge graph in `graphify-out/`), Keep usage low, Project status (update when something important lands), Secrets, Stack

## Knowledge Gaps
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Not enough signal to generate questions. This usually means the corpus has no AMBIGUOUS edges, no bridge nodes, no INFERRED relationships, and all communities are tightly cohesive. Add more files or run with --mode deep to extract richer edges._