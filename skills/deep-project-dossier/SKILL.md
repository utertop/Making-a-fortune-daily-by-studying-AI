---
name: deep-project-dossier
description: Complete an existing deep-project dossier draft into a mature, research-grade knowledge-base document for this repository. Use when Codex needs to study a GitHub repository, official docs, examples, releases, key code structure, and surrounding primary sources, then fill a deep dossier draft under knowledge-base/ rather than write a shallow summary.
---

# Deep Project Dossier

Use this skill when the user wants a deep, reusable project knowledge base rather than a lightweight signal note.

The canonical template is [knowledge-base/templates/deep-project-dossier.md](../../knowledge-base/templates/deep-project-dossier.md). This skill assumes the draft already exists and should be upgraded into a final deep dossier with supported claims, explicit uncertainty, and a practical learning path.

## Workflow

1. Read the existing draft first.
2. Collect the primary source set.
3. Reconstruct the project from repo, docs, examples, releases, and key code structure.
4. Separate facts, inference, and open questions.
5. Fill the deep dossier so a future reader can actually understand and use the project.

Read [references/research-depth-rules.md](references/research-depth-rules.md) before drafting the final document.

Read [references/dossier-section-checklist.md](references/dossier-section-checklist.md) while writing or reviewing the final Markdown.

When source-level deepening is justified, also read [references/source-level-deepening-checklist.md](references/source-level-deepening-checklist.md).

## Scope

This skill is for projects that deserve a deep study layer, including:

- AI engineering tools
- agent frameworks and runtimes
- developer tools with docs plus real code
- infrastructure or workflow systems with multiple moving parts
- open-source projects the user may study, adopt, compare, or operationalize

This skill is not for simple trend notes, one-page summaries, or fast daily snapshots. Use `knowledge-base-writer` for that lighter workflow.

## Source Handling

- Prefer official repo README, docs, examples, release notes, changelog, and in-repo configuration first.
- Inspect key directories, entry files, and wiring points when architecture or workflow claims matter and when the repository actually exposes meaningful implementation.
- Use official blog posts, project sites, or creator announcements next.
- Use third-party posts only as secondary context, never as the sole basis for technical claims.
- If docs and code disagree, say so explicitly and favor the strongest primary evidence.
- If the repo is thin but the docs are strong, write that clearly instead of guessing missing implementation details.

## Research Expectations

- Reconstruct what problem the project solves and for whom.
- Explain the user workflow from entry point to result.
- Identify the major modules, components, or layers that make the system work.
- Describe configuration, extension points, permissions, providers, plugins, skills, agents, or runtime concepts when they exist.
- Orient the reader to the codebase with concrete directories or files when possible.
- Explain practical adoption: what a learner would do first, next, and after basic setup.
- Surface real strengths, limitations, and risk signals instead of praise-heavy summaries.
- Decide whether source code is a primary learning signal for this project. If yes, include source-level orientation. If not, keep the dossier deep through docs, workflow, architecture, and product understanding rather than forcing weak code analysis.
- When source-level deepening applies, prioritize skeleton files that explain system shape rather than reading the repo evenly.

## Output Rules

- Default to Chinese unless the user asks for English.
- Preserve product names, repo names, package names, CLI commands, and config keys in their original language.
- Distinguish clearly between:
  - source-backed facts
  - inference
  - unknowns or TODOs
- Do not invent install commands, architecture details, benchmarks, license details, internal module behavior, or adoption claims.
- If a deep section cannot be completed from available sources, leave a concise `TODO` with the missing evidence type.
- Prefer clarity over coverage; a smaller number of accurate deep insights is better than many speculative paragraphs.

## Path Rules

- Require an existing draft path under `knowledge-base/`.
- Update the target file in place.
- Keep all generated files inside `knowledge-base/`.
- Do not create a new draft path as part of this skill.
- Do not silently switch to the lightweight template.

## Depth Rules

- Move beyond `what it is` into `how it is organized, how it works, and how to use it well`.
- Treat architecture as a system explanation, not just a diagram section.
- When Mermaid helps, add it. When it would be decorative only, skip it.
- Prefer one clear architecture diagram plus one flow/module diagram over many weak diagrams.
- Use code references, directory references, and docs references to support the explanation.
- Add comparison or positioning context only when it helps the learner choose or understand.
- Source-level analysis is a conditional enhancement, not a mandatory section for every project.
- When code is sparse, closed, incidental, or not the main value signal, say that clearly and focus the dossier on the strongest available primary sources instead.
- When code is valuable, do not turn the code section into a directory dump; explain why specific files matter and what system behavior they reveal.

## Final Check

Before finishing:

1. Confirm the draft has been upgraded into a deep dossier, not just a longer summary.
2. Confirm the output still matches the local deep-project-dossier template.
3. Confirm every strong claim has a source or is clearly marked as inference.
4. Confirm the reader could understand the learning path, workflow, and architecture after reading.
5. Confirm strengths, limits, and risks are all present.
6. Confirm the document is useful for future study and real adoption decisions.
