# Prompt: Knowledge Extraction (post-task retrospective)

```
Task just completed: [summary].
Run the Knowledge Curator decision rule (.claude/agents/knowledge-curator.md):
1. What changed? One line.
2. What did I learn that isn't already written down anywhere in docs/ or .claude/?
3. Classify: repeated code-writing correction → rule; reusable solution shape used twice → pattern;
   a concrete way something went wrong → anti-pattern; a structural tradeoff decision → ADR;
   a bug fixed with a root cause worth remembering → postmortem; sprint-level state/debt/question → memory.
4. Check for an existing file on this topic first — extend, don't duplicate.
5. Write it to the correct location. Update memory/project-memory.md's changelog regardless.
Do not create a file for a one-off observation that hasn't repeated — wait for the second occurrence.
```
