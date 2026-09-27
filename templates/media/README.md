# Video-platform generator

`media_layout.py` selects this original frontend using video/schema evidence or
video-library navigation patterns. A photo gallery or a single embedded video
alone keeps the legacy builder. Explicit `blueprint.layout_kind` can be
`video_platform` to select it, or another value to opt out.

The layout has a featured collection, sidebar, search, category filtering,
sorting, persistent Watch later, keyboard shortcuts, mobile drawer, and an
accessible details dialog. Playback is enabled only when a video URL is supplied.
No backend accounts, upload, or streaming service is implied.

`blueprint.media_items` optionally supplies up to 48 records with `title`,
`channel`, `category`, `duration`, `views`, `age`, `thumbnail`, and `video` fields.
Media URLs accept HTTP(S) only; strings are escaped or assigned through textContent.
Without these records the output uses an explicitly labeled curated demo
collection, including illustrative metadata and remote Unsplash stock photos.
Photos need an internet connection; broken images fall back to the card surface.
Use client-owned or licensed assets and real metadata for production.

Inferred mobile/tablet transition midpoints influence grid breakpoints within
480–800px and 900–1300px respectively. Defaults are 640px and 1100px. The sidebar
becomes a drawer below 850px independently to maintain usable content width.
Existing analyzer layout, stacking, visibility, and breakpoint inference is not
modified. All project writes still go through the existing builder workflow.

Run `python -m unittest -v test_media_layout test_responsive test_navigation test_project_flow`.
