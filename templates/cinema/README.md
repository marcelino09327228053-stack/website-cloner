# Nocturne

An explicitly authored Netflix-inspired catalog, not an automatic reconstruction or a Netflix streaming client. Netflix hostnames select the `cinema` layout in the existing builder.

Includes ten fictional film/series concepts and original SVG artwork. Browse featured titles, genres, film/series views, search, sort, title details, horizontal rows, and a persistent watchlist. The playable content consists of original silent 20-second motion-art previews, not full films or external trailers. Playback supports pause, seeking, fullscreen, keyboard controls, and local progress/resume. Reduced-motion preferences disable the art movement.

Watchlist and preview progress use localStorage keyed by persistent project ID, preserved across folder rename and rebuild. Use the same browser/origin; clearing browser storage removes these settings. No accounts, payments, subscriptions, remote APIs, or downloaded assets.

Run `python -m unittest test_cinema_layout` for generation, routing, browser interactions, persistence, fullscreen, and responsive layout verification.
