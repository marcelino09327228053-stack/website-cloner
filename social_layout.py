"""Original local social-feed template, not reconstructed Facebook content."""
from pathlib import Path
import json
import uuid
ASSETS = Path(__file__).parent / 'templates' / 'social'

def render_social_platform(project):
    try:
        previous = json.loads((project/'project.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        previous = {}
    identity = previous.get('project_id') or uuid.uuid4().hex
    html = (ASSETS/'index.html').read_text(encoding='utf-8').replace('__STORAGE_ID__', json.dumps(str(identity)).replace('<', '\\u003c'))
    return html, (ASSETS/'style.css').read_text(encoding='utf-8'), (ASSETS/'app.js').read_text(encoding='utf-8'), identity
