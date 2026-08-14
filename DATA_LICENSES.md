# Third-party data terms

The MIT license applies to SynthLadder software. It does not relicense
third-party datasets.

| Source | Upstream term recorded by the builder | Current-tree treatment |
|---|---|---|
| PMechDB | CC BY-NC-ND 4.0 | Composite keys, task metadata, execution status, score method, and numeric scores only. Chemical inputs, references, candidate answers, and judge comments are excluded. Users obtain the source from its official distribution and reconstruct complete rows locally. |
| USPTO-50K | CC BY 4.0 | Attribution and provenance retained; upstream terms control. |
| ORDerly | CC BY 4.0 | Attribution and provenance retained; upstream terms control. |
| PaRoutes | Apache-2.0 applies to the PaRoutes software repository; terms for every downloaded reaction or route dataset were not independently established | Source attribution retained. The release does not infer dataset rights from the software license. |

The current-tree PMechDB boundary is checked by
`scripts/audit_release_payloads.py`. Earlier objects in the original Git
history remain subject to the procedure in `docs/RELEASE_HISTORY_NOTICE.md`.
