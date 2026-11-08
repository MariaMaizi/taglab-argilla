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

## Live deployment checked on 2026-11-08

Docker Desktop's WSL 2 Linux engine started after the required Windows restart. All five Compose services ran; PostgreSQL, Elasticsearch and Redis health checks passed, the Argilla web page returned HTTP 200, and the browser login succeeded. Eighteen previously unannotated pilot inputs were bulk-uploaded and visibly present in the annotation page. They contained neither existing references nor model suggestions, and excluded holdout records. The first pull returned zero submitted proposals, as expected before a new annotation. The existing five local references and six experiment records were preserved.

The opt-in `live_smoke.py` uses the real server and a separate synthetic QA workspace. Four records verify valid submitted-response decoding, draft exclusion, exact-quote rejection and remote-input integrity rejection. The single valid proposal is staged twice without updating references, then explicitly adjudicated only in an isolated fixture database; a second adjudication is rejected. Its responses are authored by `taglab-qa-bot` and are explicitly automated fixtures. No real quality score or human-label count is inferred from them.

The initial Elasticsearch start failed because an ARM-specific `-XX:UseSVE=0` option was unsupported by this image's x86-64 JVM. The option was removed, then service startup was verified. Initial Docker registry downloads also timed out until Docker was configured to use the machine's existing local HTTP proxy; no registry mirror or unverified image source was substituted.

The fork SDK reports `2.8.0.dev0`; these dataset upload and synthetic submitted-response round trips passed against the official `v2.8.0` server image. This verifies the exercised paths, not all SDK/server combinations. Dependency deprecation warnings from upstream Pydantic configuration remain visible.

## What remains unverified

A new, independent human response submitted through the real browser UI, pulled into the local proposal queue and explicitly adjudicated. The browser task is ready, but that human step has not yet occurred. Broad multi-user operations, production deployment and larger model-quality evaluation are also outside this acceptance run.

## Reproduction

From examples/taglab, install requirements-lock.txt into Python 3.11, then run:

```powershell
python -m pytest tests workbench -q
python taglab_argilla.py validate path/to/local/bundle.json
```

For the companion UI, run `python workbench/app.py`. A new checkout has no corpus: collect permitted public RSS metadata with `python workbench/scripts/collect_podcasts.py`, then start the app. No model call occurs during import or offline validation. A model API key must be entered in the local UI to run model experiments.

A user response is a claimed human submission, not proof of truth or independence. A bundle hash is an integrity/version check, not a cryptographic signature. Semantic support still requires review.

## Fork workflow notification fix

The inherited SDK build matrix failed on Python 3.13 while installing pyzmq 26.2.0 (`Use build.targets instead of cmake.targets for scikit-build-core >= 0.10`). It did not reach application tests. The separately maintained TagLab extension workflow passed in GitHub Actions.

Upstream release, documentation, cloud and legacy workflows now have job-level `github.repository == 'argilla-io/argilla'` guards. The TagLab workflow remains active, and a policy test checks those guards. This does not erase old failures or suppress all GitHub notifications; it prevents this fork from running upstream-only infrastructure jobs. The project does not claim full Python 3.13 compatibility.
