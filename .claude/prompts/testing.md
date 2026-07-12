# Prompt: Test Design

```
Design tests for this story's Acceptance Criteria (Gherkin-style happy/edge/error/permission).
For each AC, write: Given/When/Then, and the concrete failing input that would catch a regression.
If this touches fact-check verdict logic, explicitly include boundary cases:
exactly 2 trusted sources, 1 trusted+1 untrusted, contradictory sources, partial_content sources.
If this touches a provider adapter, use respx to mock HTTP — no live network calls.
Confirm the suite passes with zero GPU/Ollama access (mock the LLM boundary).
```
