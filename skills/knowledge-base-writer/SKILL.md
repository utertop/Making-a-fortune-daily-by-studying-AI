---
name: knowledge-base-writer
description: Fill and upgrade an existing knowledge-base draft into a final structured markdown note for this repository. Use when Codex needs to read a GitHub repository, documentation site, blog post, paper, product page, or mixed source bundle and complete a draft file under knowledge-base/ rather than create a new draft from scratch.
---

# Knowledge Base Writer

Use this skill to turn source material into a final note that matches this repository's knowledge-base style.

The canonical template is [knowledge-base/templates/project-note.md](../../knowledge-base/templates/project-note.md). This skill assumes the draft already exists and should be completed, upgraded, and normalized into a final knowledge-base document.

## Workflow

1. Collect the source set.
2. Prefer primary sources over commentary.
3. Preserve the existing output path under `knowledge-base/`.
4. Fill the draft sections with supported claims only.
5. Leave explicit gaps when the source set is incomplete.

Read [references/source-priority.md](references/source-priority.md) when the source mix is messy or when repo, docs, blog, and paper links disagree.

Read [references/section-checklist.md](references/section-checklist.md) when writing or reviewing the final Markdown note.

## Source Handling

- Prefer official repo README, docs, examples, releases, and changelogs first.
- Use the project site, official blog, or author post next.
- Use papers or preprints when they are the actual origin of the idea.
- Use secondary articles only to add context, never as the sole basis for technical claims.
- If the user provides a GitHub repo plus a draft, inspect the draft first, then fill it with evidence from the repo and docs.
- Do not replace a good draft with a brand-new document unless the user explicitly asks for a rewrite.

## Output Rules

- Default to Chinese unless the user asks for English.
- Preserve product names, repo names, package names, and CLI commands in their original language.
- Keep unsupported claims out of the note.
- Mark inference explicitly with wording such as `Inference:` or `Likely based on ...`.
- Do not invent install commands, architecture details, benchmarks, license details, or adoption claims.
- If a section cannot be completed from sources, leave a short `TODO` rather than fabricating content.

## Path Rules

- Require an existing draft path under `knowledge-base/`.
- If the user gives a target Markdown path, update that file.
- If the task already has a generated draft, keep the existing path.
- Do not create a new draft path as part of this skill.
- Keep all generated files inside `knowledge-base/`.

## Section Rules

- `TL;DR`: explain what it is, who it is for, and why it matters now.
- `Why It Matters`: explain the shift, trend, or workflow advantage behind the signal.
- `Quick Start`: include only source-backed commands or clearly label them as unverified.
- `Core Concepts`: explain the concepts a learner must understand before using it.
- `Architecture`: add Mermaid only when the system has enough moving parts to benefit from a diagram.
- `Evaluation Notes`: be explicit about docs quality, code quality, activity, license, and risks.
- `Hands-on Notes`: record actual setup results if tested; otherwise leave concise TODOs.
- `Links`: include the primary sources used.

## Good Defaults

- For a GitHub repo note, focus on README, docs, examples, release notes, and recent activity.
- For a docs/article note, focus on the feature, workflow, constraints, and practical adoption path.
- For a paper note, focus on the idea, the engineering relevance, and whether there is real code or usable documentation.
- For a hot AI signal, explain why people care now, not just what it is.

## Final Check

Before finishing:

1. Confirm the draft has been upgraded into a final usable note, not just lightly edited.
2. Confirm the note still matches the local project-note structure.
3. Confirm every strong claim has a source.
4. Confirm all links are captured in `Links`.
5. Confirm risks and limitations are not omitted.
6. Confirm the note is useful for future you, not just a shallow summary.
