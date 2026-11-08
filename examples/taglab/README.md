# TagLab — podcast annotation and evaluation extension

This fork adds a small, inspectable integration to Argilla. The first use case is assigning topic and programme-format labels to podcast titles and descriptions, then reviewing where model output fails.

The upstream Apache-2.0 license and attribution are retained. Application changes live in `examples/taglab/`. Two small SDK fixes declare its requests dependency and allow explicit HTTP transport injection for offline tests; the annotation server and frontend remain unchanged.

中文原理与实际案例见 [原理与实现](docs/原理与实现.md)。

## What is different in this fork

- **Blind annotation and model review are separate modes.** Blind tasks contain no predictions or existing human labels. Review tasks show one experiment strategy at a time, using Argilla Suggestions rather than Responses for machine labels.
- **Evidence has its own checks.** Returned quotations must occur continuously in the actual input. Reviewers also answer whether the candidate conclusion is supported: a matching quotation alone does not establish semantic support.
- **An import does not overwrite a reference.** Submitted human responses are converted to staged proposals. Author IDs, input hashes, taxonomy version and reference revision are retained. Drafts and model suggestions cannot become gold labels.
- **Development excludes the holdout set.** This bridge accepts pilot and development records only. A model-visible review is never silently promoted to an independent reference.
- **Snapshots are immutable.** A dataset name includes its bundle fingerprint. Upload refuses an existing name instead of replacing records.

## Status

Actual GitHub fork and local checkout: complete. Extension uses the real SDK from this fork. Offline SDK serialization and response round-trip tests are included; authentication is explicitly mocked in those tests.

On 2026-11-08 the localhost server was deployed with Docker Desktop's WSL 2 engine using the official v2.8.0 image. All five Compose services started, the web login was checked, and 18 previously unannotated pilot records were uploaded without model suggestions or reference labels. The existing five local references were preserved. No custom server build is claimed.

An opt-in live check exercised four synthetic records in a separate QA workspace: one valid submitted answer was returned, one draft was ignored, and an invalid quotation and a changed source input were rejected. Staging and adjudication were checked against an isolated fixture database. These automated fixture responses are not human reference labels or model-quality measurements.

Two real user blind annotations have since been submitted through the browser, pulled, validated, staged and explicitly accepted after assisted evidence review. The existing five references remained unchanged, bringing the local total to seven. This is one person's labelling followed by assistant review, not an independent dual-human agreement study. A new offline rule run used four pilot references across 20 inputs while preserving all six earlier experiment snapshots; no model requests were made in that check. The extension/workbench suite now has 32 passing tests.

## Run the extension tests

From this directory (`examples/taglab`), with Python 3.11:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-lock.txt
.venv\Scripts\python -m pytest tests workbench -q
```

`requirements-lock.txt` pins the tested SDK environment and installs the SDK from `../../argilla` in this fork. Synthetic fixtures are used in tests; no podcast corpus, personal review data or model API keys are committed.

## Validate a local bundle

```powershell
python taglab_argilla.py validate path/to/bundle.json
```

This constructs real Argilla Settings, Questions, Records and Suggestions with mocked authentication. The command explicitly reports `server_sync: false`.

## Connect a server

After Docker Desktop and its Linux engine work, run:

```powershell
python prepare_runtime.py
```

The command checks Docker, then creates random local-only credentials in `private/runtime.env`. Keep that file private. Next:

```powershell
docker compose --env-file private/runtime.env -f compose.yaml up -d
```

Open `http://127.0.0.1:6900`. Model-provider credentials and Argilla-server credentials are different. The Argilla key authenticates dataset operations; it is not a Qwen key.

Sign in with the local username and password created in `private/runtime.env`. No Docker Hub account is needed for the local web login. On the deployment machine Docker program files, project files and WSL container data are stored on its D drive; these personal paths are not required by the extension.

Set `ARGILLA_API_URL` and `ARGILLA_API_KEY` in your own terminal, then inspect and upload the bundle:

```powershell
python taglab_argilla.py push path/to/bundle.json --confirm-upload
python taglab_argilla.py pull path/to/bundle.json --output private/proposals.json
```

`push` creates a dataset and logs records through the SDK. `pull` reads submitted responses and produces validated proposals. It never changes TagLab reference labels. The companion bridge stages those proposals before a separate explicit adjudication. Replaying a previously accepted, identical proposal is a no-op, allowing later answers from the same immutable export to sync. Batch provenance and stale unaccepted revisions are still checked, and a changed answer is a distinct proposal that requires review.

## Opt-in live integration check

After starting the server, run `python live_smoke.py --confirm-local-qa`. It reads local credentials, creates clearly named synthetic QA records and an automated fixture author in the separate `taglab-qa` workspace, and saves a private report. It creates no real references and makes no model calls. QA fixtures are retained for inspection. This is an SDK/API integration check; it does not submit an answer through the browser UI.

## How the companion workbench connects

The included companion workbench (`workbench/`) owns the source corpus, experiment history, human references and adjudication audit. Its `argilla_bridge.py` exports sealed JSON bundles and stages returned proposals. Both sides of the protocol are included as source in this fork; the original local corpus is not. The corpus remains local; a real remote upload is a separate, explicit action.

See [architecture and evaluation](docs/ARCHITECTURE.md), [implementation boundaries](docs/VALIDATION.md), and [upstream provenance](UPSTREAM.md).
