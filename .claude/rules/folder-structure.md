# Rule: Folder Structure

Follow [context/folder-structure.md](../context/folder-structure.md) / `docs/dev-guide.md` §1 exactly — don't invent a parallel structure.

- New provider adapter → `app/adapters/{capability}/{provider}.py`, never inline in a pipeline node.
- New pipeline node → `app/pipeline/nodes/{node_name}.py`, registered in `app/pipeline/graph.py`.
- Remotion primitives → `packages/remotion-templates/src/primitives/`, one component per component-kind. Never create a composition per layout class — there is exactly one composition (`SceneRenderer`) that reads a preset and renders slots (layout-engine.md §11).
- Layout constraint presets are DATA (JSON under `src/presets/layouts/`), not code — don't implement a layout as a TSX component.
- Frontend routes follow `src/app/(auth)/`, `src/app/projects/[id]/`, `src/app/admin/` — matches the 5-station stepper + Admin's split menus, not a flat route list.
- Tests live under `tests/unit/`, `tests/integration/`, `tests/fixtures/` mirroring the module under test — don't co-locate ad hoc.
