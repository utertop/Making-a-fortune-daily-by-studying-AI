# Source-Level Deepening Checklist

Use this checklist only when source-level deepening is justified for the project.

The goal is not to read everything. The goal is to identify the smallest set of files that explains the system's real skeleton.

## 1. Start with skeletal files, not broad directory browsing

Prioritize files that explain system shape:

1. root `package.json`, workspace files, lockfiles
2. core package `package.json`
3. CLI or app entry file
4. agent, mode, runtime, or orchestration definition files
5. config loading and merge files
6. permission or policy evaluation files
7. session, state, workspace, storage, or sync files
8. server or route entry files
9. plugin or extension entry files
10. SDK export files

Do not start by dumping the entire repo tree.

## 2. Ask these questions while reading

For each key file, try to answer:

1. Why is this file important to the system?
2. What role does it play in the runtime?
3. What user-visible behavior does it explain?
4. Does it expose a boundary, a flow, a rule, or an integration point?

If a file does not answer one of those questions, it may not belong in the deep dossier.

## 3. Look for these high-value code signals

These signals usually produce the best deep-dossier upgrades:

- command registration surfaces
- built-in agent definitions
- permission evaluation logic
- config resolution and merge order
- session lifecycle and state transitions
- workspace or storage mapping
- server middleware and route wiring
- plugin hooks
- tool registries
- SDK exports
- provider abstraction surfaces

## 4. Separate fact from reconstruction

When writing from code:

- `Fact:` when the code directly defines behavior, structure, or defaults
- `Inference:` when the architecture is reconstructed from file relationships, naming, or wiring
- `TODO:` when the evidence is still incomplete

Never turn a likely interpretation into a hard claim without support.

## 5. Turn code reading into learning value

The code section should not be a file inventory. It should help the reader understand:

- what the core runtime is
- where behavior boundaries live
- how state moves
- where extensibility lives
- which files are worth reading first

Good code orientation feels like a guided tour, not a filesystem dump.

## 6. Typical output patterns to add

When source-level deepening works well, the final dossier should usually gain:

- a stronger "关键模块" section
- a more concrete "代码导览" section
- a more defensible architecture explanation
- better confidence notes
- fewer vague statements like "it seems modular"

## 7. Stop conditions

Stop going deeper when:

- the key architecture has become clear
- additional files add detail but not understanding
- you are drifting into implementation trivia
- evidence quality drops below what the dossier needs

Deep is not the same as exhaustive.
