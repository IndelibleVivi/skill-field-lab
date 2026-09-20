# Current state

Checked: **2026-09-20**. Source version: **0.2.1**; active schema: **v2**.
This page owns dated status. Start with the [documentation map](README.md) for
reading paths or the [Product spec](PRODUCT_SPEC_V0.2.md) for accepted behavior.

## Source and release

- [v0.2.1](https://github.com/IndelibleVivi/skill-field-lab/releases/tag/v0.2.1)
  was published on 2026-09-20 from release commit `b5dfa07`. Its changes are
  recorded in the [changelog](../CHANGELOG.md).
- The working source retains that runtime and now curates the bilingual reader
  entry, SVG overviews, architecture, documentation map and historical reading
  path. This documentation revision does not replace the tagged archive or publish a new
  release.
- Product/workspace/evidence contracts and schema v2 remain unchanged by this
  curation. [Architecture](ARCHITECTURE.md) explains their relationships.

## Evidence by layer

| Layer | What is established | Limit |
| --- | --- | --- |
| V0.2.1 release source | [Bundle report](../BUNDLE_REPORT.md) and [test report](../TEST_REPORT.txt): 83 deterministic tests, package compilation, both bundled example validations/selftests and controller validation | Fake adapters; zero real target invocations or LLM graders |
| Documentation curation | Local Markdown targets and bilingual diagram topology checked; all six Mermaid diagrams rendered and visually inspected; both README SVGs checked at 1000px and 640px, including grayscale; the unchanged runtime passed the 83-test bundle check again | Ordinary-work verification, not a measured reader-comprehension or Curator-benefit result |
| Published release | The linked v0.2.1 release and publication date were read back on 2026-09-20 | Publication does not establish installation or use |
| Installation and cross-subject integration | The bundle report retains dated v0.2.0 transactional-install, doctor and disposable external-lab evidence | Historical acceptance, not a v0.2.1 installation claim |
| Live target behavior | One 2026-08-30 ROT canary and a separate digest-bound review; later imported observations are distinguished in the [case study](../case-studies/repository-operational-truth-audit.md) | Supports only its pinned claim; no v0.2.1 live rerun or comparative-benefit claim |
| Controller discovery and owner acceptance | No new evidence established by this documentation revision | Installed bytes, source checks and publication do not establish either |

## Supported surface and current limits

Python 3.10+, standard library only. The sole implemented live adapter is
`codex-exec`; live execution is POSIX-only. Subjects are explicit `local-path`,
`local-git-ref`, lab-owned `snapshot`, or `control` sources. Normal commands
accept v2 only; v1 has a separate [offline migration](MIGRATION_V1_TO_V2.md).

V0.2.1 checks actual subject delivery against the saved plan before each
attempt. That does not prove host Skill selection or semantic application:
host selection remains unknown, trace references mean command-path mentions,
and application needs semantic review. Selftest exercises only declared
workspace/command oracles, not result, trace or human-review assertions.
See the [Evidence model](EVIDENCE_MODEL.md) for interpretation.

There is no remote auto-clone, marketplace resolver, automatic LLM judge,
global score, background service or automatic publication. `hermetic` is
reserved. A workspace overlay does not establish exclusive causation.

## Next evidence boundary

No new live trial is required to complete this documentation change. Stronger
claims about v0.2.1 installation, fresh-host selection, live behavior or
comparative benefit remain separate evidence questions. Use existing work
first; authorize any new synthetic execution through its own saved plan and
explicit invocation cap. Release publication alone closes none of those gaps.
