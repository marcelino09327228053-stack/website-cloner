# Visibility inference

`blueprint.responsive_behavior.visibility_changes` compares explicit visibility
states matched by DOM path. Each record retains desktop, tablet, and mobile
visibility and presence fields, plus a `transitions` list.

Transitions describe narrowing the viewport: `shown` means hidden to visible;
`hidden` means visible to hidden. `from_stage` identifies the larger sample and
`breakpoint_stage` the smaller sample. Bounds are the actual sampled viewport
widths, not an exact CSS breakpoint. Tablet-only elements can have two transitions.

Only adjacent stages with known boolean visibility and positive, descending
numeric widths produce ranges. Missing samples remain unknown, so a record can
report different observed states with an empty transitions list. This avoids
guessing a transition stage through a missing tablet observation.

The renderer captures up to 2,000 visibility nodes independently of its existing
layout sample and reports `visibilitySampleTruncated`. Visibility changes are
sorted by path and capped at 30 records. DOM mutation between renders can still
affect matching; these are observed viewport differences, not proof of a media
query. The builder does not yet apply these rules to generated components.

Run regression tests with `.venv\Scripts\python.exe -m unittest -v test_responsive`.
