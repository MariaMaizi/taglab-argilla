[简体中文](UPSTREAM.md) | **English**

# Upstream provenance

- Upstream: https://github.com/argilla-io/argilla
- Fork: https://github.com/MariaMaizi/taglab-argilla
- Base branch: develop
- Base commit: 5338519accb13ae422f8bf9c0642651c249c49af
- Extension branch: taglab/podcast-review
- License: Apache-2.0, retained at repository root.
- SDK installed from this fork: 2.8.0.dev0 (reported by the pinned source).
- Optional server image: argilla/argilla-server:v2.8.0 (official release image, not a custom fork server image).

Upstream states in its README that original authors have moved on, with fixes and patches planned rather than new features. This fork is an educational/application extension and makes no claim of official upstream endorsement or contribution acceptance.

Modified/additional application code: examples/taglab/. Two additional SDK fixes declare requests and support explicit HTTP transport injection. The upstream server and web frontend have not been modified by this extension.
