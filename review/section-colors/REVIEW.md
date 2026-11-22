# Section color coding — 1.12.1 review

Right-click any sidebar category or an item in Hidden sections → **Section color**. Choose Blue, Teal, Green, Amber, Orange, Red, Purple or Gray, or open **Custom color…**. Cancel leaves the current color unchanged. **No color** resets one category. **Use suggested colors for all sections** applies a full optional palette; **Clear all section colors** removes it.

A small marker appears to the left of the category. Text, selection, hide/restore eyes and drag insertion highlights retain their normal theme colors. Markers appear in both the main sidebar and hidden drawer. Colors are optional: existing workspaces remain uncolored until a user chooses them.

Colors follow stable category identities, not list positions, across drag/reorder, hide/restore, theme switching, F5 and restart. They apply across projects in the same local data folder. They are stored in the existing `appearance.ini`, alongside theme settings, separately from the database. Copy that file too when moving appearance preferences; database-only backup/restore does not include it. No project record, report, deadline, order, visibility or schema field is modified.

The displayed app version now uses the same package version constant as the build; this removes the prior stale status-bar version label. The frozen executable smoke check verifies both its version label and setting/resetting a section marker.

## Validation

`tests/test_section_colors.py` covers:

- Presets/custom chooser/cancel/reset and suggested/all reset actions.
- Persistence through restart, projects, hide/restore, dragging, themes and F5, while original task records remain equal.
- Malformed saved JSON and invalid colors/categories without corrupting prior settings or records.
- Actual delegate painting and marker pixels in both themes, including the hidden drawer.

Linux/Windows test logs, JUnit, artifact metadata and exact-download verification are recorded here after their actual successful runs. No merge or GitHub Release publication is performed. PR #1 remains a draft; the Windows ZIP is a review artifact.


Verified results: **413/413 passed on Windows** (287.31 seconds) and **413/413 passed locally on Linux** (62.78 seconds), including four new color tests. Source smoke exited 0. [Successful Windows workflow](https://github.com/felixzax/construction-project-coordinator/actions/runs/44995013084) built commit `fe4b64a60a225561f242f792cffe958a98eeaf57`. Extracted ZIP, isolated native/offscreen executable checks and verification of the exact downloaded artifact all passed.

[Download 1.12.1 Windows review ZIP](https://github.com/felixzax/construction-project-coordinator/actions/runs/44995013084/artifacts/14743129576) (GitHub sign-in may be required; expires February 20, 2027). Artifact SHA-256: `5bd89d6a563d3381e5bc8ff0be8d2149f91fb7b496605cdf2b5436b87d9a0911`. No schema change; schema remains 12. PR #1 remains draft.
