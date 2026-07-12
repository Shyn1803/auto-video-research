# Rule: Testing

See [context/testing-strategy.md](../context/testing-strategy.md) for the full picture; enforceable points:

- Every AC in a story's Gherkin-style block (happy/edge/error/permission) needs a corresponding test before the story is done.
- Provider adapter tests mock HTTP with `respx` — no live network calls in the test suite.
- All unit tests must pass with zero GPU/Ollama access — mock the LLM boundary, don't skip the test.
- Fact-check verdict logic gets explicit boundary tests: exactly 2 trusted sources, 1 trusted+1 untrusted, contradictory sources, `partial_content` sources.
- A bug found manually gets a regression test added before the fix is considered done — see [agents/debugger.md](../agents/debugger.md).
- UI/frontend stories require exercising the feature in a real running browser before being marked complete — type-checks and unit tests are necessary, not sufficient.
