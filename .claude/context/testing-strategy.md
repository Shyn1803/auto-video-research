# Context: Testing Strategy

**Full detail:** `docs/test-plan.md`. **Status: no test suite exists yet** — this summarizes intent.

**Layers:** unit (pytest/vitest, no network — provider adapters mocked with `respx`), integration (real Postgres via test container, LangGraph pipeline run end-to-end against a fixture project), UI (component-level via the frontend test runner; full flows manually verified in-browser per this project's UI-testing rule — see below).

**Mandatory case categories per story:** every Acceptance Criterion written in `story-template.md`'s Gherkin-style format (happy / edge / error / permission) needs a corresponding test — see [qa-engineer agent](../agents/qa-engineer.md).

**Domain-specific test emphasis (from fact-check logic, the highest-risk correctness area):** boundary cases around the PASS/WARN/FAIL verdict — exactly 2 independent trusted sources (PASS boundary), 1 trusted + 1 untrusted (should be WARN not PASS), contradictory sources (FAIL), `partial_content` sources (WARN even with 2+).

**No-GPU constraint:** all unit tests must pass without Ollama/GPU access — mock the LLM call, don't skip the test.

**UI/frontend changes:** per this project's own working agreement (not test-plan.md, but a standing engineering principle) — start the dev server and exercise the feature in a real browser before calling a UI story done; type checking and unit tests verify correctness of code, not of the actual user-facing behavior.

**CI:** planned but not yet created — no `.github/workflows/` exists. Once it does, PR gate = CI green + 1 review + docs updated if contract changed (dev-guide.md §4).

See [checklists/testing.md](../checklists/testing.md), [rules/testing.md](../rules/testing.md).
