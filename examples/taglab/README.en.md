[简体中文](README.md) | **English**

# TagLab Guide

TagLab supports public-text annotation, paired model experiments and error review. Its first use case labels podcast titles and descriptions by topic and programme format, with quoted evidence for each decision. The application extension is maintained in this directory.

## Start here

- Follow the [three-minute demo](docs/DEMO.en.md) for the workflow.
- Read [principles](docs/PRINCIPLES.en.md) and [architecture](docs/ARCHITECTURE.en.md) for decision and version design.
- See [validation](docs/VALIDATION.en.md) and [pilot notes](docs/PILOT-20261108.en.md) for exercised paths and remaining limits.

## From a decision to a reference

Blind tasks show input and guidelines. Model-review tasks show one experiment strategy's candidate. Machine labels use Argilla Suggestions; submitted user answers use Responses.

Returned answers pass input, quotation, taxonomy and revision checks before becoming staged proposals. References change only after explicit adjudication. Model-visible feedback cannot enter the blind-reference adjudication path. Disputed interpretations can remain available for later review without becoming independent references.

Export bundles and dataset names include content fingerprints. Replaying an identical accepted proposal is a no-op, so later answers from the same batch can still synchronize without duplicate writes.

## Install and test

Run from this directory with Python 3.11:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-lock.txt
.venv\Scripts\python -m pytest tests workbench -q
```

The dependency file installs this fork's SDK. Forty tests use synthetic fixtures and isolated databases. Mocked HTTP authentication in offline tests is explicitly identified; it does not prove server connectivity.

## Start the companion workbench

A fresh checkout has no private corpus, references or run history. Collect permitted public RSS metadata, then start:

```powershell
.venv\Scripts\python workbench\scripts\collect_podcasts.py
.venv\Scripts\python workbench\app.py
```

The default address is `http://127.0.0.1:8877/`. Human annotations, offline rules and model experiments retain separate provenance. Model experiments require your own provider configuration in the local page. Credentials live only in service memory and must be re-entered after a service restart.

## Start the annotation server

With Docker Desktop's Linux engine ready:

```powershell
.venv\Scripts\python prepare_runtime.py
docker compose --env-file private/runtime.env -f compose.yaml up -d
```

The script checks the engine and creates random local credentials in `private/runtime.env`, refusing to overwrite an existing file. Open `http://127.0.0.1:6900/` and sign in with that local username and password. Argilla credentials and model-provider keys are separate configurations.

The deployment uses the official `argilla/argilla-server:v2.8.0` image and exposes the web port only on localhost. The upstream server and web frontend have not been modified. The validation notes record deployment issues and their resolution.

## Export, upload and return

The workbench exports pilot or development data; the development bridge excludes holdout records. Inspect a bundle and validate local SDK construction:

```powershell
.venv\Scripts\python taglab_argilla.py validate path/to/bundle.json
```

This reports `server_sync: false`. For live synchronization, configure `ARGILLA_API_URL` and `ARGILLA_API_KEY` in the current terminal, then run:

```powershell
.venv\Scripts\python taglab_argilla.py push path/to/bundle.json --confirm-upload
.venv\Scripts\python taglab_argilla.py pull path/to/bundle.json --output private/proposals.json
```

`push` creates the dataset and uploads through the SDK. `pull` saves validated proposals and rejection reasons without updating references. The workbench bridge's `stage` command imports proposals; `accept` is a separate explicit adjudication.

Human quotes may have boundary whitespace removed only when the result is an exact continuous input substring, with both values retained in the audit. Interior changes, punctuation differences and ellipsis joins remain invalid. Model-output validation is unchanged.

## Exercise a real server

```powershell
.venv\Scripts\python live_smoke.py --confirm-local-qa
```

This reads local credentials, creates synthetic records and automated fixture responses in a separate `taglab-qa` workspace, and saves a private report. It checks submitted responses, draft exclusion, invalid quotations and changed inputs without writing real references or calling a model. QA data remains available for inspection.

## Re-evaluate a reference revision

In a populated companion workbench:

```powershell
python reference_audit.py EXPERIMENT_ID
```

The tool reuses saved outputs and writes a separate analysis while preserving the experiment. Changed inputs or taxonomy block reuse; disputed references are excluded. Post-output reference changes are sensitivity analysis, not model improvement.

## Verified scope and limits

Local deployment, web submission, response return, explicit adjudication, repeat synchronization and model review have been exercised. A ten-record, twenty-request paired model run produced eighteen mechanically valid outputs, with additional semantic-support issues found in review.

The seven local references and eight runs validate the workflow on limited sources and categories. One person's labels followed by assistant evidence review are not independent dual-human agreement, and disputed feedback is not an independent reference. The pilot notes preserve detailed observations and reference revisions.

The upstream Apache-2.0 license and attribution are retained; see [provenance](UPSTREAM.en.md) for the base commit and SDK/server versions. Private text, human responses, full model dumps and credentials are not included in this repository.
