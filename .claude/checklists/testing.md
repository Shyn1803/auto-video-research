# Checklist: Testing

- [ ] Every story AC (happy/edge/error/permission) has a test
- [ ] Fact-check verdict boundary cases covered if touched (2 trusted sources, 1 trusted+1 untrusted, contradictory, partial_content)
- [ ] Provider adapter tests mock HTTP via respx — no live network calls
- [ ] Full suite passes with zero GPU/Ollama access
- [ ] Any manually-found bug has a regression test before being closed
- [ ] UI story exercised in a real running browser, golden path + ≥1 edge case
