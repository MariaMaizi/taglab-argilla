# Architecture and evaluation

## 1. The unit of work is a versioned observation

A sample is `(record_id, title, cleaned_text, input_hash, split, reference_revision)`. The hash uses canonical JSON with sorted keys and SHA-256 over the exact title and text. It detects accidental changes; it is not a digital signature or authentication mechanism. Origin validation and server credentials still matter.

A different cleaning result is a different observation. The model and the human must see the same text for an outcome to be comparable. The bridge rejects response imports if input or reference revisions changed, rather than attaching a judgment to the wrong revision.

The source programme and RSS category are intentionally absent from the annotation fields and model input. Otherwise a classifier could learn or exploit channel identity instead of the episode's content. This reduces one leakage route; it does not eliminate collection bias.

## 2. Argilla is a collaboration layer

The SDK sends Settings (the task schema), Records (inputs), Suggestions (machine proposals), and receives Responses (each user's submitted answers). Those objects have different roles. Changing a Suggestion to a Response without a real human submission would fabricate supervision.

The service architecture supplied upstream has a web frontend, a Python API, relational persistence, a search engine, Redis and background workers. The relational store holds durable records and responses; Elasticsearch supports indexed retrieval/filtering; Redis supports background work. None of these components replaces the language model. The companion TagLab service calls the model, records experiments, and applies project-specific validation.

This extension keeps Argilla's core unchanged and adds an application module. Its contribution is the task schema, versioned exchange protocol, evidence checks and proposal staging. A Fork establishes code provenance and a place to maintain changes; by itself it is not an integration.

## 3. Two distinct human workflows

**Blind annotation:** expose only title, input text and label definitions. Existing gold and model labels are not sent. Human submissions become proposals, not immediate truth. Distinct annotators remain separate. An adjudicator can inspect disagreement and accept one response with a written reason.

**Model review:** show a single experiment/strategy candidate. This mode asks whether the evidence supports the candidate. It helps diagnose failures, but the reviewer has seen the prediction, so it is not an independent gold-labeling process. The local bridge refuses automatic promotion of model-visible responses to independent references.

A/B candidates use separate dataset fingerprints. Argilla Suggestions are one candidate per question; mixing A and B into a single suggestion would destroy experiment provenance.

## 4. Classification and inference

Topic prediction is multi-label: the output is a set of up to three labels. Programme format is a single-label decision with an explicit unknown option. A prompt conditions the model's next-token distribution; it does not retrain model weights. The current workbench calls an external Qwen endpoint with the same model, input and generation parameters for A/B. A supplies label names; B supplies definitions and counterexamples; both use a shared JSON and quotation contract.

Temperature and fixed input reduce some variation, but a single call is still not a deterministic scientific result. An A/B improvement needs paired samples, sufficient independent references and repeated validation. Updating both the output contract and prompt definitions at once prevents attributing a change to only one factor.

The workflow does not currently perform RAG, embeddings, fine-tuning or RLHF. Argilla data could later support supervised training, but collecting feedback does not itself train a model.

## 5. Evidence checks are a layered contract

1. **Transport:** request completed, or an explicit timeout/quota/authentication failure stops the run.
2. **Syntax:** response is parseable JSON.
3. **Schema:** known label IDs, topic cardinality, programme format, boolean review state.
4. **Quotation integrity:** each required quote is a continuous substring of the exact input. A fragment assembled with ellipses is rejected.
5. **Semantic support:** does this quote justify this label under the guideline? This is a separate human judgment.
6. **Decision readiness:** a valid output with `needs_review` still needs review before use.

For example, a passage saying a podcast analyses a published report does not establish that only one person speaks. Such a quotation can be genuine while the monologue label remains unsupported. This is why quotation matching cannot be advertised as a hallucination detector or factual certification.

## 6. Evaluating quality and abstention

For a predicted topic set P and a human reference G, count TP = |P ∩ G|, FP = |P − G|, FN = |G − P| across samples. Micro precision = TP/(TP+FP), recall = TP/(TP+FN), and F1 = 2TP/(2TP+FP+FN). Per-label support must accompany the aggregate: a high score on one frequent class says little about unseen classes.

Format accuracy measures format agreement. Exact match requires both the whole topic set and format to match. The workbench's end-to-end score counts invalid outputs as failures. It must be shown alongside schema pass rate and semantic error categories, because a zero caused by invalid serialization is different from valid but incorrect classification.

The workbench presently scores all structurally valid predictions including those requesting review. Therefore those scores do not measure automatic publication readiness. A production decision policy should additionally report auto-accept coverage, human-review rate, and error rate among auto-accepted outputs. This distinction is documented, not silently hidden in a single accuracy number.

## 7. Splits, bias and audit

Pilot samples expose ambiguous guidelines. Development samples support strategy iteration. Holdout samples are reserved for a frozen evaluation. The development bridge excludes holdout records by construction. Existing hand-labeled holdout samples are retained locally rather than shown with development suggestions.

The current local corpus is small and comes from two programmes, skewed toward business and technology. Random per-source splitting and exact-title grouping do not establish independence or remove near-duplicate content. Before a defensible benchmark, add topic diversity, inspect near-duplicates, use more than one annotator on a subset, measure disagreement, and adjudicate. No benchmark claim follows from one or two references.

Each model run preserves inputs, taxonomy, prompts, output contract, parameters, usage and errors. Each human change preserves actor and revision. Import failures and accepted proposals are auditable. These are reproducibility and quality-control mechanisms, not guarantees that a human reference is infallible.

## Sources

- Upstream repository and license: https://github.com/argilla-io/argilla
- Records: https://docs.argilla.io/latest/reference/argilla/records/records/
- Responses: https://docs.argilla.io/latest/reference/argilla/records/responses/
- Suggestions: https://docs.argilla.io/latest/reference/argilla/records/suggestions/
- Deployment: https://docs.argilla.io/latest/getting_started/how-to-deploy-argilla-with-docker/
