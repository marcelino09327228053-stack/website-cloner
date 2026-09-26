from pathlib import Path
from datetime import datetime
import re
import html
import json
BASE = Path(__file__).resolve().parent
GENERATED = BASE / "generated"

def safe_name(value):
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", (value or "generated-site").strip().lower()).strip("-") or "generated-site"


def e(value):
    return html.escape(str(value or ""))

def build_site(analysis, project_dir=None, project_name=None):
    GENERATED.mkdir(exist_ok=True)
    site = analysis.get("site", {})
    bp = analysis.get("blueprint", {})
    structure = analysis.get("structure", {})
    navigation = analysis.get("navigation", [])
    design = analysis.get("design", {})
    design_page = design.get("page", {})
    design_root = design.get("root", {})
    headings = structure.get("headings", [])
    buttons = structure.get("buttons", [])
    interactions = bp.get("interactions", [])
    name = safe_name(project_name or site.get("domain") or site.get("title"))
    if project_dir:
        project = Path(project_dir).expanduser().resolve()
        project.mkdir(parents=True, exist_ok=True)
    else:
        project = GENERATED / f"{name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        project.mkdir(parents=True, exist_ok=False)

    sections = bp.get("section_order") or ["hero", "features", "contact", "footer"]
    heading_texts = [h.get("text", "") for h in headings if h.get("text")]
    blocks = []
    if "hero" not in sections:
        hero_title = e(site.get("title") or (heading_texts[0] if heading_texts else "Explore Something Better"))
        hero_desc = e(site.get("description") or "A more polished original experience inspired by the reference, redesigned with stronger hierarchy, richer visuals, and modern interactions.")
        blocks.append(f'<section id="enhanced-hero" class="hero premium-hero"><div class="wrap hero-grid"><div class="hero-copy"><span class="eyebrow">Enhanced Experience</span><h1>{hero_title}</h1><p>{hero_desc}</p><div class="hero-actions"><button class="cta">Explore Now</button><button class="secondary-cta" type="button">Discover More</button></div><div class="hero-meta"><span>Modern layout</span><span>Responsive design</span><span>Original experience</span></div></div><div class="hero-visual"><div class="hero-orb orb-one"></div><div class="hero-orb orb-two"></div><div class="hero-showcase"><div class="showcase-top"><span></span><span></span><span></span></div><div class="showcase-main"><div class="showcase-preview"><span class="showcase-play">&#9654;</span></div><div class="showcase-lines"><i></i><i></i><i></i></div></div></div></div></div></section>')
    for index, section in enumerate(sections):
        label = section.replace("_", " ").title()
        detected_title = heading_texts[index] if index < len(heading_texts) else label
        section_id = f"sec-{index:06d}"
        if section == "hero":
            cta = buttons[0] if buttons else "Get Started"
            blocks.append(f'<section id="{section_id}" class="hero premium-hero"><div class="wrap hero-grid"><div class="hero-copy"><span class="eyebrow">Enhanced Experience</span><h1>{e(site.get("title") or detected_title or "Generated Website")}</h1><p>{e(site.get("description") or "A refined original experience inspired by the reference structure and enhanced with stronger visual hierarchy.")}</p><div class="hero-actions"><button class="cta">{e(cta)}</button><button class="secondary-cta" type="button">Explore More</button></div><div class="hero-meta"><span>Modern layout</span><span>Responsive design</span><span>Enhanced interactions</span></div></div><div class="hero-visual"><div class="hero-orb orb-one"></div><div class="hero-orb orb-two"></div><div class="hero-showcase"><div class="showcase-top"><span></span><span></span><span></span></div><div class="showcase-main"><div class="showcase-preview"><span class="showcase-play">&#9654;</span></div><div class="showcase-lines"><i></i><i></i><i></i></div></div></div></div></div></section>')
        elif section in ("main_content", "feed"):
            blocks.append(f'<section id="{section_id}" class="content media-section"><div class="wrap"><div class="content-heading"><div><span class="eyebrow">{e(label)}</span><h2>{e(detected_title)}</h2></div><button class="view-more" type="button">View More</button></div><div class="card-grid"><article class="card media-card"><div class="thumb thumb-one"><span class="play-icon">&#9654;</span><span class="duration">8:24</span></div><div class="media-info"><div class="avatar"></div><div><h3>Featured content</h3><p>Original media preview inspired by the reference layout.</p></div></div></article><article class="card media-card"><div class="thumb thumb-two"><span class="play-icon">&#9654;</span><span class="duration">12:10</span></div><div class="media-info"><div class="avatar"></div><div><h3>Recommended content</h3><p>Responsive card layout with original content.</p></div></div></article><article class="card media-card"><div class="thumb thumb-three"><span class="play-icon">&#9654;</span><span class="duration">5:42</span></div><div class="media-info"><div class="avatar"></div><div><h3>Explore more</h3><p>Enhanced visual hierarchy and spacing.</p></div></div></article></div></div></section>')
        elif section == "navigation":
            blocks.append(f'<section id="{section_id}" class="category-strip"><div class="wrap"><div class="category-scroll"><button class="category-chip active" type="button">All</button><button class="category-chip" type="button">Featured</button><button class="category-chip" type="button">Trending</button><button class="category-chip" type="button">Popular</button><button class="category-chip" type="button">New</button></div></div></section>')
        elif section == "footer":
            blocks.append(f'<footer id="{section_id}"><div class="wrap"><strong>{e(site.get("title") or "Generated Website")}</strong><p>Original generated preview.</p></div></footer>')
        else:
            blocks.append(f'<section id="{section_id}" class="content"><div class="wrap"><span class="eyebrow">{e(label)}</span><h2>{e(detected_title)}</h2><p>Rebuild this section with original client content, assets, and business logic.</p></div></section>')

    if "carousel_or_slideshow" in interactions:
        blocks.append('<section id="interaction-slideshow" class="content interaction-block"><div class="wrap"><span class="eyebrow">Slideshow</span><h2>Featured Content</h2><div class="generated-slider"><article class="slide active">Featured item 1</article><article class="slide">Featured item 2</article><article class="slide">Featured item 3</article></div><div class="slider-controls"><button type="button" data-slide="prev">Previous</button><button type="button" data-slide="next">Next</button></div></div></section>')
    if "accordion_or_faq" in interactions:
        blocks.append('<section id="interaction-faq" class="content interaction-block"><div class="wrap"><span class="eyebrow">FAQ</span><h2>Frequently Asked Questions</h2><div class="generated-accordion"><button type="button" class="accordion-trigger">Question 1</button><div class="accordion-panel">Original answer content for the rebuilt website.</div><button type="button" class="accordion-trigger">Question 2</button><div class="accordion-panel">Add client-specific information here.</div></div></div></section>')
    if "form_submission" in interactions:
        blocks.append('<section id="interaction-form" class="content interaction-block"><div class="wrap"><span class="eyebrow">Contact</span><h2>Send a Message</h2><form class="generated-form"><label>Name<input name="name" required></label><label>Email<input type="email" name="email" required></label><label>Message<textarea name="message" rows="5" required></textarea></label><button type="submit" class="cta">Submit</button><p class="form-status" aria-live="polite"></p></form></div></section>')
    if "dropdown_or_menu" in interactions:
        blocks.append('<section id="interaction-menu" class="content interaction-block"><div class="wrap"><span class="eyebrow">Menu Interaction</span><h2>Explore Options</h2><div class="generated-dropdown"><button type="button" class="dropdown-trigger" aria-expanded="false">Open Menu</button><div class="dropdown-menu"><a href="#">Option One</a><a href="#">Option Two</a><a href="#">Option Three</a></div></div></div></section>')
    if "modal_or_popup" in interactions:
        blocks.append('<section id="interaction-modal" class="content interaction-block"><div class="wrap"><span class="eyebrow">Dialog Interaction</span><h2>More Information</h2><button type="button" class="modal-open">Open Dialog</button></div></section><div class="generated-modal" role="dialog" aria-modal="true" aria-hidden="true"><div class="modal-card"><button type="button" class="modal-close" aria-label="Close">&times;</button><h2>Information</h2><p>Original modal content for the rebuilt website.</p></div></div>')

    nav_labels=[]
    nav_seen=set()
    for item in navigation:
        text=(item.get("text") or "").strip()
        key=text.casefold()
        if text and key not in nav_seen:
            nav_seen.add(key)
            nav_labels.append(text)
        if len(nav_labels)>=6:
            break
    if not nav_labels:
        nav_labels=["Home","Explore","About","Contact"]
    section_ids=[f"sec-{i:06d}" for i in range(len(sections))]
    nav_links="".join('<a href="#{}">{}</a>'.format(section_ids[i % len(section_ids)] if section_ids else "top", e(text)) for i,text in enumerate(nav_labels))
    brand=e(site.get("title") or site.get("domain") or "Generated Website")
    detected_font = design_page.get("fontFamily") or "Inter, Segoe UI, system-ui, sans-serif"
    detected_bg = design_root.get("background") or design_page.get("background") or design_page.get("Background") or "#0b1017"
    if detected_bg in ("transparent", "rgba(0, 0, 0, 0)", "rgba(0,0,0,0)"):
        detected_bg = "#0b1017"
    detected_color = design_page.get("color") or "#e8eef7"
    rgb_match = re.search(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", detected_bg)
    if rgb_match:
        r, g, b = map(int, rgb_match.groups())
        is_light_theme = (0.2126*r + 0.7152*g + 0.0722*b) > 160
    else:
        is_light_theme = detected_bg.lower() in ("#fff", "#ffffff", "white")
    surface_color = "#f6f7f9" if is_light_theme else "#121a24"
    border_color = "#dfe3e8" if is_light_theme else "#243242"
    muted_color = "#5f6368" if is_light_theme else "#aebdcc"
    nav_bg = "rgba(255,255,255,.92)" if is_light_theme else "rgba(11,16,23,.92)"
    hero_bg = "linear-gradient(135deg,#ffffff,#f2f5f8)" if is_light_theme else "radial-gradient(circle at 80% 20%,#174b6e 0,#0b1017 46%)"
    radius_values = []
    for item in design.get("elements", []):
        match = re.search(r"([0-9]+(?:\\.[0-9]+)?)px", str(item.get("borderRadius", "")))
        if match and float(match.group(1)) > 0:
            radius_values.append(float(match.group(1)))
    radius_values.sort()
    detected_radius = radius_values[len(radius_values)//2] if radius_values else 12
    detected_radius = max(2, min(detected_radius, 32))
    radius_css = f"{detected_radius:g}px"
    design_elements = design.get("elements", [])
    viewport_width = int(design.get("viewport", {}).get("width") or 1440)
    layout_widths = [int(x.get("width") or 0) for x in design_elements if x.get("tag") in ("main", "section", "article") and 320 <= int(x.get("width") or 0) < viewport_width * 0.98]
    if not layout_widths:
        layout_widths = [int(x.get("width") or 0) for x in design_elements if 320 <= int(x.get("width") or 0) < viewport_width * 0.98]
    layout_widths.sort()
    detected_wrap_width = layout_widths[len(layout_widths)//2] if layout_widths else min(1180, max(720, viewport_width - 48))
    detected_wrap_width = max(720, min(detected_wrap_width, 1440))
    y_values = sorted(set(int(x.get("y") or 0) for x in design_elements if x.get("tag") in ("main", "section", "article", "h1", "h2", "h3") and int(x.get("y") or 0) >= 0))
    y_gaps = [b-a for a,b in zip(y_values,y_values[1:]) if 40 <= b-a <= 240]
    y_gaps.sort()
    detected_section_space = y_gaps[len(y_gaps)//2] if y_gaps else 88
    detected_section_space = max(56, min(detected_section_space, 120))
    gap_values = []
    for item in design_elements:
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)px", str(item.get("gap", "")))
        if match and 4 <= float(match.group(1)) <= 80:
            gap_values.append(float(match.group(1)))
    gap_values.sort()
    detected_gap = gap_values[len(gap_values)//2] if gap_values else 24
    detected_gap = max(8, min(detected_gap, 48))
    def font_samples(tags):
        values=[]
        for item in design_elements:
            if item.get("tag") in tags:
                m=re.search(r"([0-9]+(?:\\.[0-9]+)?)px", str(item.get("fontSize", "")))
                if m:
                    values.append(float(m.group(1)))
        values.sort()
        return values
    heading_fonts = font_samples(("h1","h2","h3"))
    button_fonts = font_samples(("button","a"))
    detected_heading_size = heading_fonts[-1] if heading_fonts else 54
    detected_heading_size = max(36, min(detected_heading_size, 86))
    detected_button_size = button_fonts[len(button_fonts)//2] if button_fonts else 14
    detected_button_size = max(12, min(detected_button_size, 20))
    html = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+brand+'</title><link rel="stylesheet" href="style.css"></head><body><nav class="topbar"><div class="wrap nav-inner"><div class="brand-wrap"><span class="brand-mark">&#9654;</span><strong class="brand">'+brand+'</strong></div><div class="search-shell"><input\1><button type="button">&#128269;</button></div><div class="nav-links">'+nav_links+'</div></div></nav>' + ''.join(blocks) + '<script src="app.js"></script></body></html>'
    css = '*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Inter,Segoe UI,system-ui,sans-serif;background:#0b1017;color:#e8eef7}a{color:inherit;text-decoration:none}.wrap{max-width:1180px;margin:auto;padding:0 24px}.topbar{position:sticky;top:0;z-index:20;background:rgba(11,16,23,.92);backdrop-filter:blur(14px);border-bottom:1px solid #202a36}.nav-inner{min-height:68px;display:flex;align-items:center;justify-content:space-between;gap:24px}.brand{font-size:18px;max-width:420px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.nav-links{display:flex;gap:18px;flex-wrap:wrap}.nav-links a{font-size:14px;opacity:.82}.nav-links a:hover{opacity:1}.hero{min-height:620px;display:flex;align-items:center;background:radial-gradient(circle at 80% 20%,#174b6e 0,#0b1017 46%)}.hero h1{font-size:clamp(44px,7vw,86px);line-height:.98;margin:16px 0 24px}.hero p{font-size:19px;line-height:1.7;color:#bcc8d5;max-width:760px}.eyebrow{text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:700;color:#7cd6ff}.cta{margin-top:24px;border:0;border-radius:12px;padding:14px 20px;font-weight:700;cursor:pointer}.content{padding:88px 0;border-bottom:1px solid #1d2732}.content h2{font-size:clamp(34px,5vw,54px)}.content p{max-width:760px;color:#aebdcc;line-height:1.7}.card-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-top:34px}.card{min-height:190px;padding:24px;border:1px solid #243242;border-radius:18px;background:#121a24;display:flex;align-items:flex-end;font-weight:700}footer{padding:52px 0;background:#070c11}@media(max-width:800px){.nav-links{display:none}.hero{min-height:auto;padding:96px 0}.card-grid{grid-template-columns:1fr}.content{padding:68px 0}}'
    css = css.replace("font-family:Inter,Segoe UI,system-ui,sans-serif;background:#0b1017;color:#e8eef7", f"font-family:{detected_font};background:{detected_bg};color:{detected_color}")
    css = css.replace("border-radius:12px", f"border-radius:{radius_css}")
    css = css.replace("border-radius:18px", f"border-radius:{radius_css}")
    css = css.replace("max-width:1180px", f"max-width:{detected_wrap_width}px")
    css = css.replace("padding:88px 0", f"padding:{detected_section_space}px 0")
    css = css.replace("font-size:clamp(44px,7vw,86px)", f"font-size:clamp(36px,7vw,{detected_heading_size:g}px)")
    css = css.replace("font-size:clamp(34px,5vw,54px)", f"font-size:clamp(30px,5vw,{min(detected_heading_size,64):g}px)")
    css = css.replace("font-size:14px", f"font-size:{detected_button_size:g}px")
    css = css.replace("background:rgba(11,16,23,.92)", f"background:{nav_bg}")
    css = css.replace("border-bottom:1px solid #202a36", f"border-bottom:1px solid {border_color}")
    css = css.replace("background:radial-gradient(circle at 80% 20%,#174b6e 0,#0b1017 46%)", f"background:{hero_bg}")
    css = css.replace("color:#bcc8d5", f"color:{muted_color}")
    css = css.replace("color:#aebdcc", f"color:{muted_color}")
    css = css.replace("border-bottom:1px solid #1d2732", f"border-bottom:1px solid {border_color}")
    css = css.replace("border:1px solid #243242", f"border:1px solid {border_color}")
    css = css.replace("background:#121a24", f"background:{surface_color}")
    css = css.replace("gap:18px", f"gap:{detected_gap:g}px")
    css = css.replace("gap:24px", f"gap:{detected_gap:g}px")
    css += ".interaction-block button{font:inherit}.generated-slider{position:relative;min-height:220px;margin-top:28px}.slide{display:none;min-height:220px;padding:28px;border:1px solid var(--generated-border,#dfe3e8);border-radius:"+radius_css+";background:"+surface_color+";align-items:flex-end;font-weight:700}.slide.active{display:flex}.slider-controls{display:flex;gap:12px;margin-top:16px}.slider-controls button,.accordion-trigger{padding:12px 16px;border:1px solid "+border_color+";border-radius:"+radius_css+";background:"+surface_color+";color:inherit;cursor:pointer}.generated-accordion{display:grid;gap:10px;margin-top:24px}.accordion-trigger{text-align:left;font-weight:700}.accordion-panel{display:none;padding:4px 16px 18px;line-height:1.7;color:"+muted_color+"}.accordion-panel.open{display:block}.generated-form{display:grid;gap:16px;max-width:720px;margin-top:24px}.generated-form label{display:grid;gap:8px;font-weight:600}.generated-form input,.generated-form textarea{width:100%;padding:13px 14px;border:1px solid "+border_color+";border-radius:"+radius_css+";background:"+surface_color+";color:inherit;font:inherit}.form-status{min-height:1.5em;margin:0;color:"+muted_color+"}.generated-dropdown{position:relative;display:inline-block;margin-top:20px}.dropdown-trigger,.modal-open,.modal-close{padding:12px 16px;border:1px solid "+border_color+";border-radius:"+radius_css+";background:"+surface_color+";color:inherit;cursor:pointer}.dropdown-menu{display:none;position:absolute;top:calc(100% + 8px);left:0;min-width:220px;padding:8px;border:1px solid "+border_color+";border-radius:"+radius_css+";background:"+surface_color+";box-shadow:0 18px 45px rgba(0,0,0,.18);z-index:30}.dropdown-menu.open{display:grid}.dropdown-menu a{padding:10px 12px;border-radius:"+radius_css+"}.dropdown-menu a:hover{background:rgba(127,127,127,.12)}.generated-modal{display:none;position:fixed;inset:0;z-index:100;background:rgba(0,0,0,.55);padding:24px;align-items:center;justify-content:center}.generated-modal.open{display:flex}.modal-card{position:relative;width:min(560px,100%);padding:28px;border:1px solid "+border_color+";border-radius:"+radius_css+";background:"+surface_color+";color:inherit;box-shadow:0 24px 80px rgba(0,0,0,.28)}.modal-close{position:absolute;top:14px;right:14px;padding:6px 10px}"
    if is_light_theme:
        css = css.replace("footer{padding:52px 0;background:#070c11}", f"footer{{padding:52px 0;background:{surface_color}}}")
    css += ".premium-hero{position:relative;overflow:hidden;min-height:680px}.hero-grid{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(360px,.95fr);align-items:center;gap:72px;min-height:680px}.hero-copy{position:relative;z-index:2}.hero-copy h1{max-width:820px;letter-spacing:-.04em}.hero-copy p{max-width:700px}.hero-actions{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.secondary-cta{margin-top:24px;padding:14px 20px;border:1px solid "+border_color+";border-radius:"+radius_css+";background:"+surface_color+";color:inherit;font-weight:700;cursor:pointer}.hero-meta{display:flex;gap:18px;flex-wrap:wrap;margin-top:30px;color:"+muted_color+";font-size:13px}.hero-meta span{display:flex;align-items:center;gap:7px}.hero-meta span:before{content:'';width:7px;height:7px;border-radius:50%;background:#ff0033}.hero-visual{position:relative;min-height:520px;display:grid;place-items:center}.hero-showcase{position:relative;z-index:2;width:min(100%,520px);padding:14px;border:1px solid "+border_color+";border-radius:calc("+radius_css+" + 10px);background:"+surface_color+";box-shadow:0 30px 90px rgba(0,0,0,.18);transform:rotate(-2deg)}.showcase-top{display:flex;gap:6px;padding:4px 2px 12px}.showcase-top span{width:9px;height:9px;border-radius:50%;background:rgba(127,127,127,.35)}.showcase-main{display:grid;grid-template-columns:1.25fr .75fr;gap:14px}.showcase-preview{min-height:290px;border-radius:"+radius_css+";display:grid;place-items:center;background:linear-gradient(135deg,#ff0033,#7c3aed 55%,#2563eb);color:white}.showcase-play{display:grid;place-items:center;width:68px;height:68px;border-radius:50%;background:rgba(255,255,255,.18);backdrop-filter:blur(10px);font-size:24px}.showcase-lines{display:grid;align-content:center;gap:14px}.showcase-lines i{display:block;height:64px;border-radius:"+radius_css+";background:linear-gradient(90deg,rgba(127,127,127,.15),rgba(127,127,127,.05))}.hero-orb{position:absolute;border-radius:50%;filter:blur(4px);opacity:.45}.orb-one{width:260px;height:260px;background:#ff0033;right:5%;top:5%}.orb-two{width:220px;height:220px;background:#2563eb;left:0;bottom:3%}@media(max-width:900px){.hero-grid{grid-template-columns:1fr;gap:32px;padding-top:72px;padding-bottom:72px}.hero-visual{min-height:420px}.hero-showcase{max-width:620px}.premium-hero{min-height:auto}}@media(max-width:600px){.hero-meta{gap:10px}.showcase-main{grid-template-columns:1fr}.showcase-lines{display:none}.hero-visual{min-height:340px}.showcase-preview{min-height:240px}}.category-strip{position:sticky;top:68px;z-index:15;padding:12px 0;background:"+nav_bg+";backdrop-filter:blur(14px);border-bottom:1px solid "+border_color+"}.category-scroll{display:flex;gap:10px;overflow:auto;scrollbar-width:none}.category-scroll::-webkit-scrollbar{display:none}.category-chip{flex:0 0 auto;border:1px solid "+border_color+";border-radius:999px;padding:9px 15px;background:"+surface_color+";color:inherit;font:inherit;font-weight:650;cursor:pointer;transition:.18s ease}.category-chip:hover{transform:translateY(-1px);box-shadow:0 7px 18px rgba(0,0,0,.08)}.category-chip.active{background:#ff0033;color:white;border-color:#ff0033}.topbar{box-shadow:0 2px 14px rgba(0,0,0,.06)}.brand-wrap{display:flex;align-items:center;gap:10px;min-width:220px}.brand-mark{display:grid;place-items:center;width:34px;height:24px;border-radius:8px;background:#ff0033;color:#fff;font-size:12px;padding-left:2px}.search-shell{flex:1;max-width:620px;display:flex;border:1px solid "+border_color+";border-radius:999px;overflow:hidden;background:"+surface_color+"}.search-shell input{flex:1;min-width:0;border:0;outline:0;padding:11px 18px;background:transparent;color:inherit;font:inherit}.search-shell button{width:54px;border:0;border-left:1px solid "+border_color+";background:rgba(127,127,127,.08);color:inherit;font-size:20px;cursor:pointer}.content-heading{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-bottom:28px}.content-heading h2{margin-bottom:0}.view-more{border:1px solid "+border_color+";background:"+surface_color+";color:inherit;border-radius:999px;padding:10px 16px;font-weight:700;cursor:pointer}.media-section .card-grid{grid-template-columns:repeat(3,minmax(0,1fr));align-items:start}.media-card{display:block;min-height:0;padding:0;border:0;background:transparent;border-radius:0}.thumb{position:relative;aspect-ratio:16/9;border-radius:"+radius_css+";overflow:hidden;background:linear-gradient(135deg,#ff1744,#7c3aed);box-shadow:0 8px 24px rgba(0,0,0,.12);transition:.2s ease}.thumb-two{background:linear-gradient(135deg,#2563eb,#06b6d4)}.thumb-three{background:linear-gradient(135deg,#f59e0b,#ef4444)}.play-icon{position:absolute;inset:0;display:grid;place-items:center;color:white;font-size:38px;text-shadow:0 3px 12px rgba(0,0,0,.35);opacity:.92}.duration{position:absolute;right:8px;bottom:8px;padding:3px 6px;border-radius:5px;background:rgba(0,0,0,.78);color:#fff;font-size:12px;font-weight:700}.media-info{display:grid;grid-template-columns:42px 1fr;gap:12px;padding:14px 2px 8px}.avatar{width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#ff0033,#ff8a00)}.media-info h3{margin:0 0 6px;font-size:16px;line-height:1.35}.media-info p{margin:0;font-size:14px;line-height:1.45;color:"+muted_color+"}.media-card:hover .thumb{transform:translateY(-2px);box-shadow:0 14px 36px rgba(0,0,0,.16)}.eyebrow{color:#ff0033}.cta{background:#ff0033;color:white}.nav-links a:hover{color:#ff0033}@media(max-width:1000px){.search-shell{max-width:420px}.media-section .card-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:700px){.search-shell{display:none}.brand-wrap{min-width:0}.media-section .card-grid{grid-template-columns:1fr}.content-heading{align-items:start}.view-more{display:none}}"
    css += ".content:nth-of-type(even){background:linear-gradient(180deg,transparent,rgba(127,127,127,.035),transparent)}.content h2{letter-spacing:-.025em}.interaction-block .wrap{padding-top:12px;padding-bottom:12px}.generated-slider,.generated-accordion,.generated-form,.generated-dropdown{position:relative}.slide,.generated-accordion,.generated-form{box-shadow:0 16px 50px rgba(0,0,0,.06)}footer{position:relative;overflow:hidden}footer:before{content:'';position:absolute;width:260px;height:260px;border-radius:50%;background:#ff0033;filter:blur(100px);opacity:.12;right:-80px;top:-120px}footer .wrap{position:relative;z-index:1;display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap}footer strong{font-size:20px}footer p{margin:0;color:"+muted_color+"}.media-section{position:relative}.media-section:before{content:'';position:absolute;width:320px;height:320px;border-radius:50%;background:#7c3aed;filter:blur(130px);opacity:.06;left:-180px;top:10%}.media-section .wrap{position:relative;z-index:1}.card-grid{gap:24px}.media-card{cursor:pointer}.media-info h3{font-weight:750}.view-more:hover,.secondary-cta:hover{transform:translateY(-1px);box-shadow:0 10px 24px rgba(0,0,0,.08)}.view-more,.secondary-cta,.cta{transition:.18s ease}.cta:hover{transform:translateY(-1px);box-shadow:0 12px 28px rgba(255,0,51,.22)}@media(max-width:700px){footer .wrap{align-items:flex-start;flex-direction:column}.card-grid{gap:18px}}"
    js = 'document.querySelectorAll(".cta").forEach(b=>b.addEventListener("click",()=>{if(b.closest("form"))return;const t=document.querySelector(".content");if(t)t.scrollIntoView({behavior:"smooth"})}));document.querySelectorAll("[data-slide]").forEach(b=>b.addEventListener("click",()=>{const slides=[...document.querySelectorAll(".slide")];if(!slides.length)return;let i=slides.findIndex(s=>s.classList.contains("active"));slides[i].classList.remove("active");i=b.dataset.slide==="next"?(i+1)%slides.length:(i-1+slides.length)%slides.length;slides[i].classList.add("active")}));document.querySelectorAll(".accordion-trigger").forEach(b=>b.addEventListener("click",()=>{const p=b.nextElementSibling;if(p)p.classList.toggle("open")}));document.querySelectorAll(".generated-form").forEach(f=>f.addEventListener("submit",e=>{e.preventDefault();const s=f.querySelector(".form-status");if(s)s.textContent="Demo form ready. Connect this to the client backend."}));console.log("Generated website ready");document.querySelectorAll(".dropdown-trigger").forEach(b=>b.addEventListener("click",()=>{const m=b.nextElementSibling;if(!m)return;const o=m.classList.toggle("open");b.setAttribute("aria-expanded",String(o))}));document.querySelectorAll(".modal-open").forEach(b=>b.addEventListener("click",()=>{const m=document.querySelector(".generated-modal");if(m){m.classList.add("open");m.setAttribute("aria-hidden","false")}}));document.querySelectorAll(".modal-close").forEach(b=>b.addEventListener("click",()=>{const m=b.closest(".generated-modal");if(m){m.classList.remove("open");m.setAttribute("aria-hidden","true")}}));document.querySelectorAll(".generated-modal").forEach(m=>m.addEventListener("click",e=>{if(e.target===m){m.classList.remove("open");m.setAttribute("aria-hidden","true")}}));'

    (project / "index.html").write_text(html, encoding="utf-8")
    (project / "style.css").write_text(css, encoding="utf-8")
    (project / "app.js").write_text(js, encoding="utf-8")
    (project / "analysis.json").write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
    history_dir = project / "history"
    history_dir.mkdir(exist_ok=True)
    metadata = {
        "project_name": project.name,
        "display_name": project_name or project.name,
        "project_path": str(project),
        "source_url": analysis.get("final_url") or analysis.get("requested_url") or "",
        "main_file": "index.html",
        "files": ["index.html", "style.css", "app.js", "analysis.json"],
        "updated_at": datetime.now().isoformat(timespec="seconds")
    }
    metadata_file = project / "project.json"
    if metadata_file.exists():
        try:
            previous = json.loads(metadata_file.read_text(encoding="utf-8"))
            metadata["created_at"] = previous.get("created_at") or metadata["updated_at"]
        except Exception:
            metadata["created_at"] = metadata["updated_at"]
    else:
        metadata["created_at"] = metadata["updated_at"]
    metadata_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"project_name": project.name, "project_path": str(project), "files": metadata["files"] + ["project.json"], "main_file": "index.html"}

