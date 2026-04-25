# Dossier Section Checklist

Use this checklist while completing a deep-project dossier.

Do not be constrained by the template's example counts. The template provides a minimum workable structure, not a maximum. Expand sections when the project complexity justifies it.

## Metadata

- Fill source, source type, project type, signal score, status, confidence, and tags when known.
- Keep `Depth level` aligned with the deep dossier workflow.

## Executive Summary

- `TL;DR`: what it is, who it is for, why it matters now.
- Problem definition: what pain point or workflow gap it addresses.
- Why now: what makes this project worth learning in the current AI landscape.
- Learning path: how a reader should approach it in stages.

## Project Understanding

- Project positioning
- Target user or team
- Core concepts and terms
- User workflow
- Feature / capability map

The reader should understand both the product idea and the mental model required to use it.

## Architecture

- Architecture overview
- Layer breakdown
- Module or subsystem descriptions
- Mermaid only when it clarifies system structure
- Module interactions and boundaries

Explain the logic of the architecture, not just the names of layers.

## Code and Repo Orientation

- Important paths and what they mean
- Important files and why they matter
- Key runtime or orchestration entry points
- Configuration and extension points
- If source code is not a strong or necessary signal for this project, explicitly say so and keep this section lighter instead of fabricating depth.
- If source code is a strong signal, prefer a curated "why this file matters" tour over a broad file listing.

Prefer a curated code tour over a full tree dump.

## Runtime Shapes

When applicable, cover:

- CLI / TUI
- Web
- IDE
- Desktop

If a mode does not exist, say so plainly or leave a TODO.

## Practical Adoption

- Source-backed quick start
- Realistic setup path
- Hands-on workflow examples
- Practical tips, gotchas, and validation checkpoints

## Evaluation

- strengths
- weaknesses
- risks
- adoption difficulty
- docs quality
- code quality
- activity
- community health
- learning value

## Comparison

- compare only when useful
- focus on meaningful differences, not forced tables

## Learning Guidance

- what to study first
- what to study after basics
- what to test hands-on

## Open Questions

- record unresolved questions honestly
- use TODO where the evidence is missing

## Links

- repo
- docs
- release notes or changelog
- examples
- related official blog or announcement

## Confidence Notes

- mention which sections are source-backed
- mention which sections rely on inference
- mention what evidence was missing
- mention whether source-level analysis was applicable, partial, or intentionally limited
- mention which core files most strongly supported the source-level conclusions

## Final Pass

Before finishing, ask:

1. Could a future reader build a real mental model from this document?
2. Could they tell how the project is organized?
3. Could they decide whether it is worth deeper adoption?
4. Are unknowns explicit instead of hidden?
