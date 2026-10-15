# Release checks

Use a fresh checklist for each release; checked boxes record that release only.

- [ ] Verify runtime and documented versions agree.
- [ ] Run the relevant regression tests and the complete runtime suite.
- [ ] Run the accuracy, quality and structure evaluators; review discrepancies and unsupported scope.
- [ ] Validate semantic, scanner and consumer outputs against their public contracts.
- [ ] Check identity stability, coverage/profile changes and uncertain diffs.
- [ ] Exercise local scanning, supported input modes and output/cleanup protection.
- [ ] Review the engineering-kit setup and companion checks when kit files change.
- [ ] Check README instructions, output interpretation, links and release notes against actual behavior.
- [ ] Record tested environments and unresolved limitations without generalizing fixture results.
- [ ] Inspect the exact files to publish; exclude credentials, private context, working notes, caches and generated scan outputs.
- [ ] Preserve licensing and third-party notices.

See [TESTING.md](TESTING.md) for reproducible commands and [the consumer contract](integrations/CONSUMER-CONTRACT.md) for compatibility requirements.
