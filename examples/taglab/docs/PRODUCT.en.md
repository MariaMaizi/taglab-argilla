[简体中文](PRODUCT.md) | **English**

# Product design and strategy validation

TagLab uses a concrete content-classification task to examine how model outputs can enter an inspectable review workflow. It connects content understanding, evaluation and data quality with rule design, error analysis and strategy validation. This document ties these practices to decisions, implementation and recorded checks.

## Starting problem

Consider a content product that organizes podcasts by topic and programme format. Generating labels is straightforward. A product owner must also know what supports a label, what happens when information is missing, how to assess a prompt change, and how to trace a correction when a human reference was wrong.

The prototype addresses annotation/content operations, model evaluation and product strategy roles. These are task-based usage hypotheses, not a demand assessment supported by external user interviews. Actual user operations so far come from the project user and do not replace production user research.

Inputs are titles and cleaned descriptions. Outputs contain topics, format, verbatim evidence and review state. Unsupported judgments may remain unknown. Labels could support organization, filtering or retrieval downstream, but effects on discovery, clicks or retention have not been evaluated.

## Two connected workstreams

| Area | Product work | Implementation and evidence |
| --- | --- | --- |
| Content understanding and taxonomy | Separate subject matter from conversation format; define inclusion/exclusion conditions instead of treating keywords as sufficient evidence. | [Taxonomy](../workbench/taxonomy.json): six topics with at most three selected, and four formats including unknown. |
| Cleaning and data quality | Preserve raw input, removed text, truncation and short-text flags; inspect whether cleaning removed necessary evidence. | [Data processing and scoring](../workbench/core.py), with inspectable cleaning records. False removals still need review. |
| Evaluation and experiment design | Compare basic and definition/counterexample prompts on shared inputs, parameters and output contracts. | [Model adapter and contract](../workbench/model_adapter.py), [pilot notes](PILOT-20261108.en.md). |
| Rules and strategy implementation | Allocate rules to prompts, programmatic checks and human adjudication according to the failure being addressed. | [Argilla exchange](../taglab_argilla.py), [staging and adjudication](../workbench/argilla_bridge.py). |
| Error analysis and version decisions | Distinguish prediction errors, insufficient input and reference disputes; retain reasons for rule and reference changes. | [Reference audit](../workbench/reference_audit.py), [validation notes](VALIDATION.en.md). |

Data quality determines whether a comparison is credible; error analysis can expose problems in the taxonomy or strategy. Keeping them together makes the source of a score change inspectable.

## Four design decisions

**Allow unknown rather than force completion.** A description that mentions no guest does not establish a monologue. Unknown format can coexist with a supported topic. This reduces unsupported guesses, while a high unknown rate could reduce label usefulness and requires separate observation.

**Check quotation presence programmatically and support separately.** Continuous-string matching can reject rewritten or assembled quotations. It cannot establish semantic support or external factual truth. Mechanical validity must not be presented as classification accuracy.

**Separate blind labels from model-visible review.** Blind tasks omit machine suggestions. Feedback collected after showing candidates retains that provenance and cannot enter the blind-reference adjudication path. This reduces circular reuse of model answers, but the current single annotator still does not establish independent agreement.

**Preserve experiments and analyze reference revisions separately.** Correcting a reference should not overwrite the old snapshot. Scores recomputed with unchanged predictions describe a change in scoring evidence. Changed inputs or taxonomy block direct reuse of predictions.

## Inspecting strategy through failures

These cases come from recorded runs and review. They support diagnosis, not population-level incidence estimates.

| Observation | Diagnosis | Response and check |
| --- | --- | --- |
| Several source fragments joined with ellipses as a quotation | Violates the shared continuous-quotation contract. | Reject the output; preserve fields, usage and error rather than silently repair and count a success. |
| Monologue selected without format evidence | Actual fields violate evidence requirements, even if the explanation acknowledges uncertainty. | Validate the fields as returned and retain the failure for review. |
| Genuine quotation does not establish speaker count | String validity is insufficient semantic support. | Use a separate model-review task; retain disputed feedback without promoting it to an independent scoring reference. |
| Lifestyle reference label lacks adequate support | Disagreement may originate in the reference rather than both prompts being wrong. | Revise one reference after the user's explicit decision and save a separate analysis without altering the experiment. |

An extra whitespace suffix in a pasted human quotation is a distinct issue. Only boundary trimming that yields an exact input substring is permitted, with both values retained; model quotation rules remain unchanged.

## Validating a strategy change

The offline paired experiment asks whether adding definitions and counterexamples changes guideline adherence, errors and review requests. A/B here means paired prompt comparison, not a live traffic experiment or model-weight training.

1. Fix ten pilot inputs before inspecting outputs. Keep the model, generation parameters and contract the same; A uses a basic prompt and B adds definitions and counterexamples.
2. Save input versions, prompts, outputs, usage and errors rather than silently substitute successful-looking outputs for failures.
3. Examine protocol validity, label metrics, format decisions, disagreement, review flags and request overhead together rather than choosing from one score.
4. Return to the input to diagnose disagreement, then decide whether to change a prompt, clarify a rule, obtain information or correct a reference.
5. For further iteration, use development data, obtain sufficient independent references, freeze acceptance criteria, and conduct a later holdout check.

Completed work covers the pilot, error review and reference-revision traceability. It does not establish a winning strategy or completed locked-holdout acceptance. Further evaluation needs broader topic coverage, independent annotations, repeated runs and predeclared thresholds.

## Metrics and product decisions

| Metric or record | Question | Current status |
| --- | --- | --- |
| Structural and continuous-quotation validity | Can the output enter subsequent processing? | 18/20 in this run; mechanical validity only, not content correctness. |
| Topic micro F1, format match and exact match | Where do predictions differ from the references available at that time? | Four usable original references, with revision analysis saved separately; insufficient for general quality claims. |
| Disagreement and review flags | Which records should be inspected first? | Five of eight mutually valid pairs differ in topic or format; flags do not detect every error. |
| Tokens, latency and failure causes | What overhead and failures accompany additional rules? | Request-level records retained; API token usage is not a cash bill. |
| Auto-acceptance coverage, accepted-output error rate and review time | Can the workflow reduce effort while controlling errors? | Acceptance rules and usage studies are pending; no business benefit has been established. |
| Independent annotator agreement | Are guidelines understood and applied consistently? | Additional independent annotators are needed; assistant review is not dual-human agreement. |

## Delivery and scope

As of 2026-11-08, the project has prepared 80 real RSS metadata records from two programmes; the local workbench retains seven references and eight experiment records. One paired run made 20 real model requests. Forty application tests cover exchange, revision conflicts, quotations, adjudication and reference audits. These validate workflow behavior, not forty model-evaluation samples.

The project demonstrates task definition, taxonomy and rule design, an API-based prototype, model experiments, error analysis and version audits. External demand, multi-user efficiency and live product effects remain untested. No audio understanding, fine-tuning or RAG experiment has been performed. Publisher text, private annotations, full model dumps and keys remain local; see the [guide](../README.en.md) to run the public code and synthetic tests.

Continue with [architecture](ARCHITECTURE.en.md), [recorded experiment and review](PILOT-20261108.en.md), or the [three-minute demo](DEMO.en.md).
