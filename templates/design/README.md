# Design Studio

An explicitly authored, original design-workspace template. It is not an automatic reconstruction of Canva.

Generate through `builder.build_site` with `blueprint.layout_kind = "design_studio"` and display name `Design Studio`. The builder writes the same HTML/CSS/JS/metadata files as other projects and preserves the persistent project ID on rebuild.

All artwork is original CSS and editable text. No external fonts, assets, APIs, frameworks, or account services are needed. Search, categories, starred templates, and the text editor run locally. Saved designs use localStorage keyed by the persistent project ID; renaming the project preserves that key. Use the same browser and origin (port 8021) to reopen saved designs. Clearing browser storage removes those designs.

Run `python -m unittest test_design_studio` for builder, editing, drag, save/reload, rename persistence, and responsive browser checks.
