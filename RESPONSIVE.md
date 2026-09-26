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
query.

`navigation_mapping` is populated only for one unambiguous navigation/button
pair: a native button explicitly controls a `nav` or navigation-role element by
ID, all three visibility states are complementary, and both have one matching
transition range. Incomplete, tablet-only, and ambiguous pairs remain unmapped.
The renderer retains navigation link labels for this mapping; the builder uses
its own markup and local section destinations.

The builder estimates the navigation breakpoint at the mapped range midpoint.
It switches between inline links and a keyboard-operable Menu button, whose
panel closes on Escape, link selection, or crossing the breakpoint. Without a
mapping it uses an 800px fallback. Other source visibility rules are not yet
applied to generated components.

Run regression tests with
`.venv\Scripts\python.exe -m unittest -v test_responsive test_navigation`.

## Section-driven builder

The renderer captures up to 20 distinct content regions separately from the
existing layout sample. Regions include headings, child geometry, and media
presence. `blueprint.sections` normalizes these into ordered components with
source paths, measured desktop columns, media/text order, and per-section
responsive variants. Matching tablet/mobile regions supply midpoint estimates
for column transitions. A 700px collapse is the fallback when none are observed.

The builder uses these components when available, preserving repeated section
types, two-column proportions, card counts, and section-specific breakpoints.
Navigation points to generated section IDs. Existing interaction components and
the legacy fallback remain available. Original abstract artwork substitutes for
source media; descriptive copy is authored placeholder text, or an explicit
`description` supplied in the normalized section. This is a layout reconstruction,
not a complete reproduction of source content or application logic.

Region capture currently prefers leaf sections; nested wrappers and regions
without headings may be omitted. Old snapshots fall back to semantic sections
when available. Run `test_blueprint_sections` alongside the existing tests for
multi-layout rendering, contrast, overflow, and navigation regression coverage.
