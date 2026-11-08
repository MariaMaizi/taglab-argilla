# TagLab — podcast annotation and evaluation extension

This fork adds a small, inspectable integration to Argilla. The first use case is assigning topic and programme-format labels to podcast titles and descriptions, then reviewing where model output fails.

The upstream Apache-2.0 license and attribution are retained. Application changes live in `examples/taglab/`. Two small SDK fixes declare its requests dependency and allow explicit HTTP transport injection for offline tests; the annotation server and frontend remain unchanged.

## What is different in this fork

- **Blind annotation and model review are separate modes.** Blind tasks contain no predictions or existing human labels. Review tasks show one experiment strategy at a time, using Argilla Suggestions rather than Responses for machine labels.
- **Evidence has its own checks.** Returned quotations must occur continuously in the actual input. Reviewers also answer whether the candidate conclusion is supported: a matching quotation alone does not establish semantic support.
- **An import does not overwrite a reference.** Submitted human responses are converted to staged proposals. Author IDs, input hashes, taxonomy version and reference revision are retained. Drafts and model suggestions cannot become gold labels.
- **Development excludes the holdout set.** This bridge accepts pilot and development records only. A model-visible review is never silently promoted to an independent reference.
- **Snapshots are immutable.** A dataset name includes its bundle fingerprint. Upload refuses an existing name instead of replacing records.

## Status

Actual GitHub fork and local checkout: complete. Extension uses the real SDK from this fork. Offline SDK serialization and response round-trip tests are included; authentication is explicitly mocked in those tests.

A live Argilla server has **not** been deployed or synchronized on the development machine: Docker/WSL is unavailable. This limitation is part of the project record, not hidden behind a mock demonstration. `compose.yaml` prepares a localhost-only server using the official v2.8.0 image; it does not claim to run a custom server build.

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

Set `ARGILLA_API_URL` and `ARGILLA_API_KEY` in your own terminal, then inspect and upload the bundle:

```powershell
python taglab_argilla.py push path/to/bundle.json --confirm-upload
python taglab_argilla.py pull path/to/bundle.json --output private/proposals.json
```

`push` creates a dataset and logs records through the SDK. `pull` reads submitted responses and produces validated proposals. It never changes TagLab reference labels. Server creation, upload and pull still need live verification after deployment.

## How the companion workbench connects

The included companion workbench (`workbench/`) owns the source corpus, experiment history, human references and adjudication audit. Its `argilla_bridge.py` exports sealed JSON bundles and stages returned proposals. Both sides of the protocol are included as source in this fork; the original local corpus is not. The corpus remains local; a real remote upload is a separate, explicit action.

See [architecture and evaluation](docs/ARCHITECTURE.md), [implementation boundaries](docs/VALIDATION.md), and [upstream provenance](UPSTREAM.md).
