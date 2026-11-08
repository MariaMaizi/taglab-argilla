[简体中文](README.md) | **English**

# TagLab · Content Annotation and Model Evaluation Workbench

TagLab connects human labels, paired model outputs and error review. For each decision, it keeps the exact model input, quoted evidence, human revisions and the scores before and after a reference change.

The first use case is classifying podcast titles and descriptions by topic and programme format. Each selected label needs input evidence; unknown format is allowed when the text is insufficient. This is an application extension of [Argilla](https://github.com/argilla-io/argilla), maintained in [examples/taglab](examples/taglab/README.en.md).

## Capabilities

- **Independent annotation:** blind tasks expose neither model suggestions nor existing references.
- **Paired model experiments:** compare a basic prompt with one containing definitions and counterexamples, using the same inputs and generation settings.
- **Evidence checks:** validate continuous input quotations, then review whether they support the conclusion.
- **Feedback and adjudication:** preserve authors, disagreements, versions and reasons while keeping machine suggestions separate from references.
- **History and reference audits:** keep original experiment snapshots and calculate reference-revision effects separately without another model request.

Workflow: **public material → cleaning and versions → blind annotation / model experiments → evidence checks → disagreement review → explicit adjudication → evaluation and archive**.

## Verified scope

As of 2026-11-08, the local Docker deployment, web annotation and return path, repeated synchronization and separate model-review tasks have been exercised. The application suite has **40 passing tests**.

A fixed ten-record paired run made 20 real requests; 18 outputs passed structural and continuous-quotation checks. Follow-up review found genuine quotations that did not establish programme format, and retained disagreement between the user's interpretation and the guideline. Reference-revision analyses preserve the original outputs and scores.

The development machine has seven references and eight run records. The small corpus comes from two programmes skewed toward business and technology. These observations test the workflow and expose failure cases; they do not establish general model quality or a winning strategy. See the [pilot notes](examples/taglab/docs/PILOT-20261108.en.md).

## Documentation

| Topic | English | 中文 |
| --- | --- | --- |
| Installation and tests | [Guide](examples/taglab/README.en.md) | [使用说明](examples/taglab/README.md) |
| Three-minute walkthrough | [Demo](examples/taglab/docs/DEMO.en.md) | [演示步骤](examples/taglab/docs/DEMO.md) |
| Principles and examples | [Principles](examples/taglab/docs/PRINCIPLES.en.md) | [原理与实现](examples/taglab/docs/原理与实现.md) |
| Architecture and metrics | [Architecture](examples/taglab/docs/ARCHITECTURE.en.md) | [架构与评测](examples/taglab/docs/ARCHITECTURE.md) |
| Validation and limits | [Validation](examples/taglab/docs/VALIDATION.en.md) | [验证记录](examples/taglab/docs/VALIDATION.md) |
| Recorded experiment | [Pilot notes](examples/taglab/docs/PILOT-20261108.en.md) | [实验记录](examples/taglab/docs/PILOT-20261108.md) |
| Open-source provenance | [Provenance](examples/taglab/UPSTREAM.en.md) | [上游说明](examples/taglab/UPSTREAM.md) |

A fresh checkout contains code, documentation and synthetic fixtures. Publisher text, private annotations, full run dumps and credentials remain local. Follow the guide to prepare permitted data.

## Upstream relationship

This fork adds a companion workbench, exchange protocol, evidence checks and evaluation logic. Two SDK fixes declare a missing dependency and support explicit HTTP transport injection. The annotation server uses the official `v2.8.0` image; the upstream web frontend and server source have not been modified.

The upstream [Apache-2.0 license](LICENSE), attribution and [original project README](README.upstream.md) are retained.
