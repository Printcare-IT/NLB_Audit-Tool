---
name: audit-review-spec
description: Help the auditor resolve the review items in a job's spec.md (BLOCKING, LAYOUT, check) so the settings can be built. Use when status is needs_review, build exits 3, or the user asks about a review item, a spec.md table, or spec.draft.md.
---

# Help review spec.md

You prepare and propose. **The auditor decides.** Never tick an item to get
the pipeline moving. Full guide:
[docs/spec-review.md](../../../docs/spec-review.md).

1. `python audit_tool.py status --job <job> --json` and list `review_items`.
2. Group items that share a root cause, and handle each group as one.
3. For each item or group, collect the evidence: the game spec and data spec
   wording (quote it, name the file), the figure in
   `jobs/<job>/measured_facts.json`, and the current anchored table in
   `spec.md`.
4. Present: what each source says → likely cause → proposed change (the
   exact table cell and its new value), or "no table change, tick as LAYOUT".
5. **LAYOUT items keep the specification's values.** Never copy the file's
   behaviour into the tables unless the client has confirmed the spec is
   wrong, and record who confirmed it.
6. After the auditor decides: edit the table (values only, never headings or
   anchors), tick the item `- [x]`, and append
   `— <who>, <date>: <decision>`.
7. When none are left, `python audit_tool.py build --job <job> --json`.
   If validation fails, each `X [game] ...` line points at a table. Go back
   to step 3 for it.
8. Read the change list `build` prints. Every change should follow from the
   decisions just made.
