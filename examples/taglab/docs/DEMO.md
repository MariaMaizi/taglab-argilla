# A short local demonstration

This demonstration uses saved results to show the annotation and evaluation workflow. A fresh checkout contains no private corpus or run history, so first collect permitted data and create your own references/runs. Model calls require separately configured provider credentials; they are not needed to replay saved results.

## 1. Show the input and its boundary — about 30 seconds

Open the companion workbench at its local address, then show a title, cleaned description, source and cleaning audit. Explain that this task labels text, not audio. Show the label definitions and the explicit unknown-format option.

## 2. Show one paired experiment — about 45 seconds

Open a saved model A/B run. Both strategies saw the same input and generation contract; B added definitions and counterexamples. Separate mechanical output validity from agreement with the available references. State the number of reference records and their category coverage before showing any score.

In the recorded small pilot, 18 of 20 outputs passed structural/quotation checks. This is a validity result, not 90% classification accuracy. Do not rerun an API call simply to obtain a cleaner demonstration.

## 3. Show why a real quotation can still be insufficient — about 45 seconds

Open a model-review dataset in Argilla. The candidate is visibly machine-generated, and the semantic-support question is separate from the label fields. Use a speaker-count example: narration or a description of production sources does not necessarily identify the number of people speaking.

Show a submitted response by selecting the Submitted status filter. A disputed review can retain the user's interpretation while requesting review; it does not become an independent reference. Blind tasks and model-visible review tasks have different purposes.

## 4. Show reference revision without rewriting history — about 45 seconds

Use the saved reference-audit report beside the original experiment. The local pilot kept the same model outputs, changed one reference label after explicit user confirmation, and computed a separate sensitivity analysis with zero new model requests. A score change caused by a reference revision is not a model improvement or a new blinded result.

The reference audit checks input and taxonomy compatibility and retains hashes. Changed inputs or a changed label definition require another appropriate run rather than attaching old predictions to a new observation.

## 5. State the current limit — about 15 seconds

The prototype demonstrates local collection, independent annotation, model suggestions, human feedback, validation, explicit adjudication and immutable run history. A small, source-skewed, single-annotator pilot does not establish general model quality. Broader references and independent agreement checks remain further work.

Use synthetic or cleared inputs for public screenshots. Private labels, full publisher text, run dumps, credentials and deployment secrets remain outside the repository.
