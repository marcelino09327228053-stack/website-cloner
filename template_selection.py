"""Deterministic reference-URL routing to explicitly authored templates."""
from urllib.parse import urlsplit


def reference_template(url):
    value = str(url or '').strip()
    if '://' not in value:
        value = 'https://' + value
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or '').lower().rstrip('.')
        if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
            return None
        if parsed.port not in (None, 80, 443):
            return None
    except ValueError:
        return None
    for domain, template in (('canva.com', 'design_studio'), ('youtube.com', 'video_platform'), ('youtu.be', 'video_platform'), ('tiktok.com', 'short_video')):
        if host == domain or host.endswith('.' + domain):
            return template
    return None


def template_blueprint(url):
    kind = reference_template(url)
    if not kind:
        return None
    name = {'design_studio': 'Design Studio', 'video_platform': 'Frame', 'short_video': 'Loop'}[kind]
    return {
        'requested_url': url.strip(), 'final_url': url.strip(),
        'site': {'title': name},
        'blueprint': {'layout_kind': kind, 'authored_template': True, 'rendered_browser': False},
        'notes': ['Selected an original authored template by reference hostname. The reference was not rendered or reconstructed.'],
    }
