[简体中文](原理与实现.md) | **English**

# TagLab: principles and implementation

This project asks how to define a correct classification, find errors, collect attributable human judgments and evaluate whether a change helps. The fork provides a traceable workflow for those decisions.

## 1. System responsibilities

The TagLab workbench collects permitted RSS titles/descriptions, preserves source and cleaning records, manages references, calls the configured model, runs paired experiments and computes metrics. Argilla provides task schemas, suggestions and user responses; the extension aligns the two systems and converts submitted answers into staged proposals. SDK integration, local deployment, web response return and explicit adjudication have been exercised.

The upstream deployment includes a web frontend, Python API, relational store, Elasticsearch, Redis and a worker. These components persist and retrieve annotation data; they do not run the language model automatically. A fork records code provenance, while live data exchange and deployment checks establish integration.

## 2. A sample has a version

Each record has an ID, title, cleaned text, split, input hash and reference revision. Canonical JSON and SHA-256 identify the exact input. People and models need to judge the same text; a cleaning change must not silently replace the observation used in an older run. Input and revision checks catch mismatches but are not authentication or digital signatures.

Blind tasks omit dedicated programme-name, RSS-category and existing-label fields. The supplied text can still contain a programme name. Two business/technology-heavy sources also remain a sampling limitation regardless of field selection.

## 3. Suggestions, responses and adjudication

Argilla Records contain inputs; Suggestions contain machine candidates; Responses contain each user's answers and submission state. The bridge adds a proposal layer. A submitted answer must pass label, quotation, input and revision checks before staging, followed by a separate reasoned adjudication to update a reference.

Different users' answers are preserved separately. Attribution does not make an answer automatically true. Blind annotations can support relatively independent references; model-visible review has anchoring effects and is blocked from the independent-reference adjudication path.

## 4. What the model does

The model predicts up to three topics, one format and quoted evidence with a review state. A supplies IDs and label names; B adds definitions, boundaries and counterexamples. Inputs, model settings and the JSON/continuous-quotation contract are shared.

A temperature of 0.2 reduces some variation without making generation deterministic. A single run cannot establish a general improvement; paired samples, independent references and repeated validation are needed. Prompting does not modify weights. This work does not currently perform RAG, embeddings, fine-tuning or RLHF, and collecting feedback is not training.

## 5. Layered validation

The layers are transport, JSON syntax, schema, quotation integrity, semantic support and decision readiness. Code checks the first four; the latter two need separate judgment. Genuine text about analysing a report does not by itself establish that only one person speaks. Likewise, individually present words joined with ellipses do not form a continuous quotation.

Human paste-only boundary whitespace may be removed only when the result exactly matches input, with the original and normalized values retained. Internal wording, punctuation and model-output validation are not repaired to make an experiment appear successful.

## 6. Metrics and review workload

For topic sets, aggregate true positives, false positives and false negatives. Precision is TP/(TP+FP), recall TP/(TP+FN), and micro F1 2TP/(2TP+FP+FN). Format agreement is separate; complete match requires the full topic set and format to agree. Report per-label support as well as totals.

End-to-end scoring counts invalid predictions as misses, so validity and error categories must accompany scores. Structurally valid predictions requesting review are still compared by the current scorer; those metrics do not establish safe automatic adoption. Operational evaluation would also need adoption coverage, human-review workload and errors among automatically adopted outputs.

The local corpus has seven references, including two holdout references excluded from development. Reference revisions retain history rather than rewriting earlier run scores. A separate audit can reuse unchanged predictions against updated references, but its score change is reference sensitivity, not improved model performance or a new blinded test.

## 7. Engineering changes

The actual fork is MariaMaizi/taglab-argilla, based on upstream commit `5338519accb13ae422f8bf9c0642651c249c49af`. It adds the application, public companion workbench, exchange protocol and tests. Two SDK fixes declare requests and allow explicit HTTP transport injection without passing it twice.

Forty tests exercise real SDK objects with explicitly mocked offline authentication where appropriate. The live synthetic QA check is separate: four records cover a valid submission, an ignored draft, a noncontinuous quotation and changed input. Its adjudication touches only an isolated fixture database and provides no model-quality or human-label result.

Proposal acceptance, reference updates and audit history share a SQLite transaction with revision checks. Exact accepted replays are no-ops so later answers from the same batch can still synchronize. Stale unaccepted proposals and cross-batch provenance remain checked.

## 8. Deployment and actual feedback

The five-service localhost deployment used the official Argilla v2.8.0 image. Eighteen previously unannotated pilot records were uploaded without holdout records, references or machine suggestions. Two real blind submissions were returned, checked and explicitly accepted after assisted evidence review. The local total rose from five references to seven; this is not independent dual-human agreement.

A fixed ten-record model A/B run made twenty requests; eighteen outputs passed mechanical checks. Two semantic-support cases were reviewed separately. The user retained disputed interpretations outside independent references and explicitly revised another reference label. Saved outputs were reused for a separate analysis with zero new model requests; original experiments remained unchanged.

The local history now has seven references and eight runs. Broader category coverage, independent annotator checks and larger evaluation remain future work. See the architecture, validation and pilot notes for the recorded boundaries and current evidence.
