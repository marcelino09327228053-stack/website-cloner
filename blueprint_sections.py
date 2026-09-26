"""Deterministic region normalization and original component markup."""
import html
import re


def readable_foreground(background, foreground):
    def luminance(value):
        match = re.fullmatch(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,[^)]+)?\)', value)
        if match:
            rgb = [int(v)/255 for v in match.groups()]
        elif re.fullmatch(r'#[0-9a-fA-F]{6}', value):
            rgb = [int(value[i:i+2],16)/255 for i in (1,3,5)]
        else:
            return None
        return sum((v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4)*w for v,w in zip(rgb,(.2126,.7152,.0722)))
    bg, fg = luminance(background), luminance(foreground)
    if bg is None:
        return foreground
    if fg is not None and (max(bg,fg)+.05)/(min(bg,fg)+.05) >= 4.5:
        return foreground
    return '#f1f5f9' if bg < .18 else '#17212b'


def column_count(region):
    children = region.get('children', [])
    if not children:
        return 1
    top = min(c.get('y', 0) for c in children)
    row = sorted((c for c in children if abs(c.get('y', 0)-top) <= 24), key=lambda c: c.get('x', 0))
    positions = []
    for child in row:
        if not positions or child.get('x', 0)-positions[-1] > 40:
            positions.append(child.get('x', 0))
    return max(1, min(len(positions), 4))


def normalize_sections(snapshots, structure=None):
    desktop = snapshots.get('desktop', {}).get('design', {})
    regions = desktop.get('regions', [])
    result = []
    for index, region in enumerate(regions):
        columns = column_count(region)
        children = region.get('children', [])
        cells = children if columns > 1 else []
        variants = []
        previous_columns = columns
        previous_width = desktop.get('viewport', {}).get('width', 1440)
        for stage in ('tablet', 'mobile'):
            design = snapshots.get(stage, {}).get('design', {})
            matched = next((r for r in design.get('regions', []) if r.get('domPath') == region.get('domPath')), None)
            width = design.get('viewport', {}).get('width')
            if matched is None or not isinstance(width, (int, float)):
                break
            count = column_count(matched)
            if count != previous_columns and 0 < width < previous_width:
                variants.append({'max_width': int((width+previous_width)/2), 'columns': count,
                                 'lower_bound': width, 'upper_bound': previous_width})
            previous_columns, previous_width = count, width
        result.append({'id': f'section-{index+1}', 'source_path': region.get('domPath'),
                       'title': region.get('heading') or f'Section {index+1}',
                       'kind': 'hero' if region.get('headingLevel') == 'h1' else ('cards' if columns >= 3 else 'feature'),
                       'columns': columns, 'responsive': variants,
                       'max_width': region.get('width', 1100),
                       'cells': [{'title': c.get('heading', ''), 'media': bool(c.get('media')),
                                  'width': max(1, c.get('width', 1))} for c in cells]})
    if not result:
        for item in (structure or {}).get('sections', [])[:20]:
            if item.get('type') in ('navigation', 'footer'):
                continue
            index = len(result)+1
            result.append({'id': f'section-{index}', 'source_path': None,
                           'title': item.get('type', 'Overview').replace('_', ' ').title(),
                           'kind': 'feature', 'columns': 1, 'responsive': [], 'cells': []})
    return result


def render_sections(sections):
    esc = lambda value: html.escape(str(value), quote=True)
    blocks = []
    rules = []
    for index, section in enumerate(sections):
        identifier = f'section-{index+1}'
        columns = max(1, min(int(section.get('columns', 1)), 4))
        title = esc(section.get('title', 'Overview'))
        cells = section.get('cells', [])
        heading = 'h1' if index == 0 else 'h2'
        content = ''
        split = columns == 2 and sum(not c.get('media') for c in cells) == 1
        description = esc(section.get('description') or [
            'A focused space for your ideas. Start with the essentials and make something that feels your own.',
            'From the first detail to the finished experience, bring your work together with clarity and intention.',
            'Explore a new perspective. Make room for experimentation, refinement, and the next possibility.',
            'Designed around your everyday work, with a straightforward path from inspiration to creation.'
        ][index % 4])
        if columns > 1:
            for number, cell in enumerate(cells):
                if cell.get('media'):
                    content += '<div class="bp-art" role="img" aria-label="Original abstract illustration"><span></span><span></span><span></span></div>'
                else:
                    label = esc(cell.get('title') or section.get('title', 'Overview'))
                    cell_heading = f'<{heading}>{title}</{heading}>' if split else f'<h3>{label}</h3>'
                    content += f'<article class="bp-cell {"bp-feature-copy" if split else ""}"><span class="bp-kicker">{index+1:02d} / Discover</span>{cell_heading}<p>{description}</p></article>'
        else:
            content = f'<div class="bp-copy"><p>{description}</p></div>'
        heading_markup = '' if split else f'<div class="bp-heading"><span class="bp-kicker">{index+1:02d} / {"Welcome" if index == 0 else "Discover"}</span><{heading}>{title}</{heading}></div>'
        blocks.append(f'<section id="{identifier}" class="blueprint-section"><div class="bp-wrap">{heading_markup}<div class="bp-layout">{content}</div></div></section>')
        ratios = 'repeat('+str(columns)+',minmax(0,1fr))'
        if columns == 2 and len(cells) == 2:
            total = sum(c.get('width', 1) for c in cells)
            ratios = ' '.join(f'minmax(0,{max(.25, min(.75, c.get("width", 1)/total)):.3f}fr)' for c in cells)
        rules.append(f'#{identifier} .bp-layout{{grid-template-columns:{ratios}}}')
        variants = section.get('responsive', [])
        if not variants and columns > 1:
            variants = [{'max_width': 700, 'columns': 1}]
        for variant in sorted(variants, key=lambda v: v['max_width'], reverse=True):
            count = max(1, min(int(variant['columns']), 4))
            rules.append(f'@media(max-width:{int(variant["max_width"])}px){{#{identifier} .bp-layout{{grid-template-columns:repeat({count},minmax(0,1fr))}}}}')
    return blocks, ''.join(rules)


def section_styles(background, foreground, surface, border, muted, width, radius, spacing):
    return f'''
body{{background:{background};color:{foreground};font-family:Inter,Segoe UI,system-ui,sans-serif}}
.topbar{{background:{background};color:{foreground}}}.topbar .nav-inner{{flex-wrap:wrap;padding-top:16px;padding-bottom:16px}}.topbar .brand-wrap{{min-width:0}}.topbar .brand{{max-width:260px}}.topbar .nav-links{{font-size:13px;gap:20px}}
.blueprint-section{{padding:{spacing}px 0;border-bottom:1px solid {border}}}
.blueprint-section:first-of-type{{padding-top:100px;padding-bottom:100px}}
.blueprint-section:nth-of-type(even){{background:{surface}}}
.bp-wrap{{width:min(100% - 48px,{width}px);margin:auto}}
.bp-heading{{max-width:860px;margin-bottom:40px}}
.bp-kicker{{font-size:12px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:{muted}}}
.bp-heading h1{{font-size:clamp(40px,5.5vw,80px);line-height:1.06;letter-spacing:-.045em;margin:18px 0}}
.bp-heading h2{{font-size:clamp(30px,3.5vw,52px);line-height:1.12;letter-spacing:-.035em;margin:16px 0}}
.bp-layout{{display:grid;gap:28px;align-items:stretch}}
.bp-layout>*{{min-width:0;overflow-wrap:anywhere}}
.bp-cell{{padding:32px;border:1px solid {border};border-radius:{radius};background:{background}}}
.bp-number{{color:{muted};font-size:13px;font-weight:700}}
.bp-cell h3{{font-size:clamp(22px,2.5vw,32px);line-height:1.2;letter-spacing:-.025em;margin:32px 0 18px}}
.bp-feature-copy{{border:0;background:transparent;align-self:center;padding:40px}}
.bp-feature-copy h1,.bp-feature-copy h2{{font-size:clamp(32px,4vw,58px);line-height:1.08;letter-spacing:-.04em;margin:24px 0}}
.bp-cell p,.bp-copy p{{color:{muted};font-size:18px;line-height:1.75;max-width:65ch}}
.bp-art{{min-height:380px;border-radius:{radius};background:linear-gradient(145deg,{surface},#204856);color:#89e3d1;border:1px solid {border};position:relative;overflow:hidden;display:grid;place-items:center}}
.bp-art span{{position:absolute;width:55%;aspect-ratio:1;border:2px solid currentColor;border-radius:24%;transform:rotate(-25deg);opacity:.18}}
.bp-art span:nth-child(2){{width:40%;transform:rotate(15deg);opacity:.3}}
.bp-art span:nth-child(3){{width:22%;background:currentColor;transform:rotate(35deg);opacity:.12}}
@media(max-width:600px){{.blueprint-section,.blueprint-section:first-of-type{{padding:52px 0}}.bp-wrap{{width:calc(100% - 32px)}}.bp-cell{{padding:24px}}.bp-heading{{margin-bottom:28px}}.bp-art{{min-height:230px}}}}
'''
