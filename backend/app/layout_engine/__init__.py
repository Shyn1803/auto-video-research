"""Layout Engine — deterministic pipeline: Scene Tree → Scene JSON (resolved).

Nothing in this package calls the LLM. The Layout Engine boundary is architectural:
AI stops at the Semantic Storyboard (scene_tree.py). From Scene Tree onward, every
step is a pure function over the tree and a config/theme input.

Pipeline:
    SceneTree → SemanticAnalysis → LayoutClassifier → ConstraintResolver
             → ThemeEngine → MotionPlanner → Scene JSON (resolved)
"""