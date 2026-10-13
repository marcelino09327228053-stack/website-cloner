# Gather

An original Facebook-inspired social frontend, explicitly authored rather than reconstructed from Facebook. Facebook and fb.com hostnames select `social_feed` through the existing builder workflow.

Includes fictional demo people, original CSS artwork, story previews, local post creation/edit/deletion, appreciation reactions, comments, following, saved posts, search, topic filters, and sorting. Interactions are stored in localStorage under a persistent project ID, retained through folder renames and rebuilds. No accounts, real messages, remote publishing, or friend requests are simulated. Copy text copies content rather than publishing it.

Use the same browser and origin to retain your data; clearing browser storage removes your local changes. Test with `python -m unittest test_social_layout`.
