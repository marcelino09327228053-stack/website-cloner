"""Original video-platform frontend. No network or AI required at build time."""
from html import escape
from pathlib import Path
import json
from urllib.parse import urlparse

ASSETS = Path(__file__).parent / 'templates' / 'media'

DEMO = [
    ('Beyond the ordinary: a journey into the wild', 'Northbound', 'Travel', '18:42', '128K', '2 days ago', 'photo-1464822759023-fed622ff2c3b'),
    ('A workspace that makes room for better ideas', 'Studio Journal', 'Design', '12:08', '86K', '4 days ago', 'photo-1497215728101-856f4ea42174'),
    ('City after hours — a different kind of energy', 'Frame by Frame', 'Films', '08:24', '214K', '1 week ago', 'photo-1519608487953-e999c86e7455'),
    ('Slow mornings, good coffee, no rush', 'Everyday Stories', 'Lifestyle', '06:35', '42K', '3 days ago', 'photo-1442512595331-e89e73853f31'),
    ('The creative process: from blank page to something real', 'Studio Journal', 'Design', '22:16', '97K', '1 week ago', 'photo-1455390582262-044cdead277a'),
    ('Finding your sound, one session at a time', 'Sound Room', 'Music', '15:09', '163K', '5 days ago', 'photo-1511379938547-c1f69419868d'),
    ('The scenic route is always worth it', 'Northbound', 'Travel', '24:51', '302K', '2 weeks ago', 'photo-1470770841072-f978cf4d019e'),
    ('Small details. A completely different space.', 'Form & Function', 'Design', '10:32', '58K', '6 days ago', 'photo-1600210492486-724fe5c67fb0'),
    ('Cook something worth slowing down for', 'Everyday Stories', 'Lifestyle', '09:47', '76K', '1 week ago', 'photo-1555939594-58d7cb561ad1'),
]


def detect_media_layout(analysis):
    """Require video evidence; a photo gallery alone is not a video platform."""
    explicit = analysis.get('blueprint', {}).get('layout_kind')
    if explicit:
        return explicit == 'video_platform'
    evidence = analysis.get('blueprint', {}).get('media_evidence', {})
    if evidence.get('video_count', 0) >= 3 or evidence.get('video_schema_count', 0) >= 3:
        return True
    links = analysis.get('navigation', [])
    video_links = len({str(x.get('href', '')) for x in links if '/watch' in urlparse(str(x.get('href', ''))).path or '/video/' in urlparse(str(x.get('href', ''))).path})
    labels = ' '.join(str(x.get('text', '')).lower() for x in links)
    signals = sum(word in labels for word in ('subscriptions', 'watch later', 'shorts', 'channels'))
    library_navigation = 'subscriptions' in labels and 'history' in labels
    video_categories = sum(word in labels for word in ('music', 'gaming', 'movies'))
    return (video_links >= 4
            or (signals >= 2 and len(analysis.get('resources', {}).get('images', [])) >= 6)
            or (evidence.get('video_count', 0) >= 1 and library_navigation and video_categories >= 2))


def media_breakpoints(analysis):
    groups = analysis.get('blueprint', {}).get('responsive_behavior', {}).get('row_to_column_groups', [])
    mobile, tablet = 640, 1100
    for stage in ('mobile', 'tablet'):
        values = []
        for group in groups:
            low, high = group.get('breakpoint_lower_bound'), group.get('breakpoint_upper_bound')
            if group.get('breakpoint_stage') == stage and isinstance(low, (int, float)) and isinstance(high, (int, float)) and 0 < low < high:
                values.append(int((low+high)/2))
        if values:
            if stage == 'mobile': mobile = max(480, min(800, max(values)))
            else: tablet = max(900, min(1300, max(values)))
    return mobile, tablet


def render_media_platform(analysis, name=None):
    brand = escape(name or 'Frame', quote=True)
    items = []
    supplied = analysis.get('blueprint', {}).get('media_items', [])
    for i, row in enumerate(DEMO):
        title, channel, category, duration, views, age, photo = row
        items.append(dict(id=str(i), title=title, channel=channel, category=category,
                          duration=duration, views=views+' views', age=age,
                          thumbnail=f'https://images.unsplash.com/{photo}?auto=format&fit=crop&w=960&q=85', video=''))
    if supplied:
        items = []
        for i, item in enumerate(supplied[:48]):
            def safe_url(key):
                value = str(item.get(key, ''))
                return value if urlparse(value).scheme in ('http', 'https') else ''
            items.append(dict(id=str(i), title=str(item.get('title') or 'Untitled video'),
                              channel=str(item.get('channel') or 'Independent creator'),
                              category=str(item.get('category') or 'Explore'), duration=str(item.get('duration') or ''),
                              views=str(item.get('views') or ''), age=str(item.get('age') or ''),
                              thumbnail=safe_url('thumbnail'), video=safe_url('video')))
    data = json.dumps(items, ensure_ascii=False).replace('<', '\\u003c')
    page = (ASSETS/'index.html').read_text(encoding='utf-8').replace('{{BRAND}}', brand).replace('{{DATA}}', data)
    mobile, tablet = media_breakpoints(analysis)
    css = (ASSETS/'style.css').read_text(encoding='utf-8').replace('MOBILE_BREAKPOINT', str(mobile)).replace('TABLET_BREAKPOINT', str(tablet))
    return page, css, (ASSETS/'app.js').read_text(encoding='utf-8')
