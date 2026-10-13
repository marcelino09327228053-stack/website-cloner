# Loop

Original short-form creative feed, explicitly authored rather than reconstructed from TikTok. TikTok hostnames select `short_video`; other templates are preserved.

Six silent procedural canvas motion studies are included. There are no downloaded TikTok videos, accounts, public comments, or uploads. Likes, follows, saves, and private notes persist in localStorage under the stable project ID. Playback, pause, seeking, feed scrolling, keyboard navigation, search, categories, and clip-link copying work locally. Share links require the recipient to have access to the running local server; they are not public hosting links.

Build through the existing builder with `blueprint.layout_kind = "short_video"` or a TikTok reference URL. Use the same browser and origin to retain local collections. Reduced-motion preferences pause the artworks initially.

Verify with `python -m unittest test_shorts_layout`.
