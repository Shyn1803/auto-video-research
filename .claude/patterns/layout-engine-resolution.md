# Pattern: Layout Engine Resolution (Gamma-style)

**Problem:** AI-generated video content needs structurally valid, visually varied, on-brand layouts — but letting an LLM choose position/font/animation directly makes output non-deterministic, untestable, expensive to regenerate (any format/theme change re-burns tokens), and prone to repetitive "AI slop" layouts.

**Solution:** a strict layered pipeline where the AI touches only the first layer. Full spec: `docs/specs/layout-engine.md`.

```
[AI, one LLM call]   Semantic Storyboard: purpose, narration, components (kind, narration_anchor, beat)
        ↓ (everything below is a pure function — no LLM call)
Scene Tree            → structural parse of components
Semantic Analysis     → profile: n_heading, n_bullet, dominant type, etc.
Layout Classifier     → rule table maps profile → 1 of 11 PascalCase classes
                         + anti-repetition post-pass (max 2 consecutive same class,
                           max 40% of scenes, ≥4 classes if ≥8 scenes — an ENGINE rule,
                           never a prompt instruction)
Constraint Resolver    → class + format → flex preset (slots/gap/padding, not pixels)
Responsive Solver      → same preset family adapted per format (9:16 / 16:9)
Theme Engine           → independent tokens (motion_intensity, visual_density dials,
                           1 accent color, 1 radius_scale — "no theme without dials")
Motion Planner         → two-pass: Pass 1 estimated timing (storyboard time),
                           Pass 2 real word-level TTS timestamps (after produce) —
                           re-resolves motion_plan only, layout unchanged, still no LLM call
        ↓
Scene JSON (resolved) — the only thing Remotion ever renders
```

**Rules:**
- A `layout`, position, font, camera, transition, or animation field appearing in AI output is a parse failure by design — not something to coerce/accept.
- `beat` (reveal|contrast|escalation|calm) and `narration_anchor` (verbatim narration excerpt) are the only AI-authored signals that influence motion — they're content-adjacent intent, not layout choices. The Motion Planner interprets them; the AI doesn't choose timing/easing/stagger.
- Changing format or theme never re-calls the LLM — it re-runs the deterministic layers only.
- User can `layout_override` a scene manually; the override is sticky across regenerate-same-content, reset on content-nature change.

**When to use:** any code that turns AI-authored content into visual output. See [anti-patterns/ai-chooses-layout.md](../anti-patterns/ai-chooses-layout.md) for what this pattern exists to prevent — that anti-pattern has real incident history in this project's own design process.
