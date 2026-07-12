# Checklist: Before Commit

- [ ] Lint/format clean (ruff / eslint+prettier)
- [ ] Type check clean (mypy strict on new code / tsc)
- [ ] No secret, key, or token in the diff
- [ ] No `layout`/position/font/animation field introduced in any AI-facing schema or prompt output
- [ ] If `app/schemas/scene.py` changed: ran `make gen-scene-schema`
- [ ] If API shape changed: ran `make gen-api-client`
- [ ] Commit message follows Conventional Commits + story ID if applicable
- [ ] No dead code / commented-out blocks left in
