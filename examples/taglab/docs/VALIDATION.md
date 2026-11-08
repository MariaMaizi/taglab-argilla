# Fork changes and validation boundaries

## Source changes

- `argilla/pyproject.toml`: declare `requests`, imported by the SDK's field module but absent from its dependency list in the checked-out base.
- `argilla/src/argilla/_api/_http/_client.py`: accept an explicitly supplied HTTP transport without passing `transport` twice. Normal transport construction and authentication headers remain covered by tests.
- `examples/taglab/taglab_argilla.py`: task schema, immutable bundles, blind/review modes, machine Suggestions, human proposal decoding and status-preserving export.
- `examples/taglab/workbench/`: standalone companion UI/backend and bridge. The public tree excludes all local corpus, human responses, experiment dumps and keys.
- `examples/taglab/compose.yaml`: localhost server configuration using the official release image. No server/frontend fork modifications are claimed.

The generic upstream `Record.to_dict()` representation omits Response status. The application export iterates actual SDK Response objects to preserve submitted/draft/discarded state; it does not assume a missing status means submitted.

## What is tested

Real fork SDK object construction, serialization, custom/default transport behavior, human-response round trip, multiple authors, draft exclusion, blind-mode leakage, holdout exclusion, original text checks, quote integrity, staged import, rollback, reference revision conflict and explicit adjudication. Fixtures are synthetic and isolated in temporary databases.

Offline authentication uses `httpx.MockTransport`, explicitly labelled in CLI output and docs. This is a contract test, not a live Argilla service.

The companion workbench's existing model API was tested separately with real Qwen requests. Those results do not prove Argilla-server integration. No raw corpus or private model output is included in this repository.

## What remains unverified

A real `docker compose up`, first login, server-side dataset validation/indexing, bulk upload and real UI-submitted response pull. Docker and a Linux engine are missing on the current Windows machine. Deployment files were parsed and inspected; container execution cannot be reported as passed.

The SDK source reports `2.8.0.dev0`, whereas the optional official server image is `v2.8.0`. Exact live compatibility must be checked at deployment. Dependency deprecation warnings from upstream Pydantic configuration remain visible and are not suppressed as a false clean bill of health.

## Reproduction

From examples/taglab, install requirements-lock.txt into Python 3.11, then run:

```powershell
python -m pytest tests workbench -q
python taglab_argilla.py validate path/to/local/bundle.json
```

For the companion UI, run `python workbench/app.py`. A new checkout has no corpus: collect permitted public RSS metadata with `python workbench/scripts/collect_podcasts.py`, then start the app. No model call occurs during import or offline validation. A model API key must be entered in the local UI to run model experiments.

A user response is a claimed human submission, not proof of truth or independence. A bundle hash is an integrity/version check, not a cryptographic signature. Semantic support still requires review.
