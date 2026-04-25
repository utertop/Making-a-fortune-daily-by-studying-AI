# Research Depth Rules

Use these rules when a normal project note would be too shallow for the user's goal.

## Target Outcome

The finished document should help a reader answer:

1. What is this project really for?
2. Which concepts must I understand first?
3. What is the end-to-end workflow for a real user?
4. How is the system organized internally?
5. Which directories or modules matter most?
6. How do I actually begin learning or using it?
7. What are the strengths, limits, and adoption risks?

If the draft cannot answer most of those questions, it is not deep enough yet.

Do not treat the template's example slots as hard limits. If the project needs more concepts, more layers, more scenarios, or more comparison rows, expand the document naturally.

## Source Priority

For deep work, prefer sources in this order:

1. Repo README and official docs
2. Examples, templates, starter projects, demo folders
3. Releases, changelog, migration notes
4. Key config files and repo structure
5. Entry points, runtime orchestration, provider or adapter wiring
6. Official blog, creator posts, launch notes
7. External commentary only as context

Important: source code is not automatically the most important layer for every project. Treat code as a primary deep source only when the repository contains meaningful implementation and that implementation is necessary to understand the project.

## Fact vs Inference

Use this split aggressively:

- `Fact:` directly backed by docs or code.
- `Inference:` reasonable conclusion based on wiring, naming, or structure.
- `TODO:` evidence is missing and should not be guessed.

Good deep dossiers are explicit about uncertainty instead of sounding confident everywhere.

## Architecture Standard

When describing architecture:

- Explain the main layers in plain language first.
- Then tie them back to directories, modules, or runtime concepts.
- Add Mermaid only when it clarifies the system.
- Avoid decorative diagrams that are not grounded in the actual project shape.

Minimum architecture questions:

1. Where does user input enter?
2. What core runtime or orchestration layer processes it?
3. Where do models, tools, providers, plugins, or agents fit?
4. Where does project context, config, or state live?
5. What outputs or side effects does the system produce?

## Codebase Orientation Standard

Do not dump a directory tree. Instead:

- identify the handful of files or folders that explain the system best
- say what each one is for
- connect them to user-facing behavior

Useful evidence types:

- `package.json`, workspace files, lockfiles
- app entry files
- runtime or orchestration modules
- config schemas
- provider, tool, plugin, or adapter directories
- examples and templates

Only do source-level deepening when it is justified. Good triggers include:

- the repo contains substantial implementation code
- docs alone do not explain the system well enough
- the project's main learning value lives in runtime design, module boundaries, or execution flow

If those triggers are absent, do not force a fake code-analysis section. Instead, state that the project is better understood through docs, workflow, product shape, method, or public research materials.

When those triggers are present, do not browse code evenly. Prefer the small set of files that explains:

- command surface
- runtime boundaries
- permission model
- config merge order
- session and state flow
- server or route organization
- plugin or SDK extension surface

## Practical Learning Standard

Every deep dossier should help the learner move from reading to doing.

Include:

- the best first-run path
- one or more realistic use cases
- what to verify during setup
- where confusion is likely to happen
- what to read next after basic setup works

## Anti-Patterns

Avoid these failure modes:

- turning the document into a rewritten README
- listing sections without explaining them
- describing architecture only as marketing language
- claiming module behavior without code or docs support
- pretending hands-on validation happened when it did not
- filling every gap with generic AI-tool prose
