from urllib.parse import urljoin, urlparse
import re
import socket
import ipaddress
import httpx
from bs4 import BeautifulSoup
from renderer import render_page, render_multi_viewport

HEADERS={"User-Agent":"Mozilla/5.0 VibeCoder Website Reference Analyzer/0.2"}

SECTION_HINTS={"hero":("hero","banner","masthead","welcome","build fast","get started","introducing"),"features":("feature","features","powerful","built for","why choose","benefits","tools"),"services":("service","services","solutions","what we do"),"about":("about","story","company","who we are"),"pricing":("pricing","price","plans","subscription"),"testimonials":("testimonial","testimonials","review","reviews","customers say"),"faq":("faq","questions","accordion","frequently asked"),"gallery":("gallery","portfolio","showcase","examples","projects"),"docs":("docs","documentation","guides","learn","tutorial"),"community":("community","contributors","join us","ecosystem"),"download":("download","install","installation","package manager"),"contact":("contact","reach","location","get in touch"),"footer":("footer",)}

def ensure_public_url(url):
    host=urlparse(url).hostname
    if not host or host.casefold() in {"localhost","localhost.localdomain"}: raise ValueError("Only public website URLs are allowed")
    try: addresses={item[4][0] for item in socket.getaddrinfo(host,None)}
    except socket.gaierror as error: raise ValueError("Website hostname could not be resolved") from error
    for address in addresses:
        ip=ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast: raise ValueError("Only public website URLs are allowed")

def infer_section(tag):
    marker=" ".join([tag.name or "",tag.get("id","")]+list(tag.get("class",[]))).casefold()
    role=str(tag.get("role","")).casefold()
    tag_name=(tag.name or "").casefold()
    if role=="navigation" or tag_name=="nav": return "navigation"
    if role=="feed": return "feed"
    if role=="main" or tag_name=="main": return "main_content"
    if tag_name=="footer": return "footer"
    heading=tag.find(["h1","h2","h3"])
    heading_text=heading.get_text(" ",strip=True).casefold() if heading else ""
    visible_text=tag.get_text(" ",strip=True).casefold()[:600]
    for name,keywords in SECTION_HINTS.items():
        if any(k in marker or k in heading_text or k in visible_text for k in keywords): return name
    return "generic"
def element_identity(item):
    dom_path = str(item.get("domPath", "")).strip()
    if dom_path:
        return "path:" + dom_path
    if item.get("id"):
        return "id:" + str(item.get("id"))
    text = re.sub(r"\s+", " ", str(item.get("text", "")).strip().casefold())[:80]
    class_name = re.sub(r"\s+", " ", str(item.get("className", "")).strip().casefold())
    parent_id = str(item.get("parentId", "")).strip().casefold()
    parent_class = re.sub(r"\s+", " ", str(item.get("parentClassName", "")).strip().casefold())
    return "|".join([
        str(item.get("tag", "")).casefold(),
        class_name,
        text,
        str(item.get("parentTag", "")).casefold(),
        parent_id,
        parent_class,
    ])


def group_elements_by_parent(elements):
    groups = {}
    for item in elements:
        parent_key = str(item.get("parentDomPath", "")).strip()
        if not parent_key:
            parent_key = "|".join([
                str(item.get("parentTag", "")).casefold(),
                str(item.get("parentId", "")).casefold(),
                re.sub(r"\s+", " ", str(item.get("parentClassName", "")).strip().casefold()),
            ])
        if not parent_key.strip("|"):
            continue
        groups.setdefault(parent_key, []).append(item)
    for items in groups.values():
        items.sort(key=lambda x: x.get("siblingIndex", -1))
    return groups


def infer_responsive_behavior(viewport_snapshots):
    result = {
        "available": False,
        "page_height_growth": {},
        "wrapped_elements": [],
        "stacking_signals": [],
        "row_to_column_groups": [],
        "visibility_changes": [],
    }
    desktop = viewport_snapshots.get("desktop", {}).get("design", {})
    tablet = viewport_snapshots.get("tablet", {}).get("design", {})
    mobile = viewport_snapshots.get("mobile", {}).get("design", {})
    if not desktop or not tablet or not mobile:
        return result

    result["available"] = True
    desktop_elements = desktop.get("elements", [])
    tablet_elements = tablet.get("elements", [])
    mobile_elements = mobile.get("elements", [])

    def page_height(elements):
        return max((item.get("y", 0) + item.get("height", 0) for item in elements), default=0)

    desktop_height = page_height(desktop_elements)
    tablet_height = page_height(tablet_elements)
    mobile_height = page_height(mobile_elements)
    if desktop_height:
        result["page_height_growth"] = {
            "tablet_vs_desktop": round(tablet_height / desktop_height, 2),
            "mobile_vs_desktop": round(mobile_height / desktop_height, 2),
        }

    desktop_map = {element_identity(item): item for item in desktop_elements}
    tablet_map = {element_identity(item): item for item in tablet_elements}
    mobile_map = {element_identity(item): item for item in mobile_elements}
    desktop_path_map = {
        str(item.get("domPath", "")).strip(): item
        for item in desktop_elements
        if str(item.get("domPath", "")).strip()
    }
    mobile_path_map = {
        str(item.get("domPath", "")).strip(): item
        for item in mobile_elements
        if str(item.get("domPath", "")).strip()
    }

    shared_keys = set(desktop_map) & set(tablet_map) & set(mobile_map)
    for key in shared_keys:
        d = desktop_map[key]
        t = tablet_map[key]
        m = mobile_map[key]
        d_height = max(d.get("height", 0), 1)
        if m.get("height", 0) >= d_height * 1.5:
            result["wrapped_elements"].append({
                "identity": key,
                "tag": d.get("tag"),
                "desktop_height": d.get("height"),
                "mobile_height": m.get("height"),
            })
        d_width = max(d.get("width", 0), 1)
        d_y = d.get("y", 0)
        m_y = m.get("y", 0)
        desktop_ratio = d_width / max(desktop.get("viewport", {}).get("width", 1), 1)
        mobile_ratio = m.get("width", 0) / max(mobile.get("viewport", {}).get("width", 1), 1)
        vertical_shift = m_y - d_y
        parent_path = str(d.get("parentDomPath", "")).strip()
        d_parent = desktop_path_map.get(parent_path)
        m_parent = mobile_path_map.get(parent_path)

        if not d_parent or not m_parent:
            continue

        d_relative_y = d_y - d_parent.get("y", 0)
        m_relative_y = m_y - m_parent.get("y", 0)
        relative_vertical_shift = m_relative_y - d_relative_y

        if (
            relative_vertical_shift >= max(80, d_height * 0.75)
            and desktop_ratio <= 0.65
            and mobile_ratio >= desktop_ratio + 0.15
        ):
            result["stacking_signals"].append({
                "identity": key,
                "tag": d.get("tag"),
                "desktop_x": d.get("x"),
                "desktop_y": d_y,
                "mobile_x": m.get("x"),
                "mobile_y": m_y,
                "vertical_shift": vertical_shift,
                "relative_vertical_shift": relative_vertical_shift,
                "desktop_width_ratio": round(desktop_ratio, 2),
                "mobile_width_ratio": round(mobile_ratio, 2),
            })

    desktop_groups = group_elements_by_parent(desktop_elements)
    tablet_groups = group_elements_by_parent(tablet_elements)
    mobile_groups = group_elements_by_parent(mobile_elements)

    all_paths = set(desktop_path_map) | set(mobile_path_map)
    for path in all_paths:
        d_item = desktop_path_map.get(path)
        m_item = mobile_path_map.get(path)
        d_visible = bool(d_item and d_item.get("visible", True))
        m_visible = bool(m_item and m_item.get("visible", True))
        if d_visible != m_visible:
            result["visibility_changes"].append({
                "path": path,
                "desktop_visible": d_visible,
                "mobile_visible": m_visible,
                "desktop_present": d_item is not None,
                "mobile_present": m_item is not None,
            })

    for parent_key in set(desktop_groups) & set(mobile_groups):
        d_items = desktop_groups[parent_key]
        m_items = mobile_groups[parent_key]
        if len(d_items) < 2 or len(m_items) < 2:
            continue

        d_by_index = {item.get("siblingIndex"): item for item in d_items}
        m_by_index = {item.get("siblingIndex"): item for item in m_items}
        shared_indexes = [i for i in d_by_index if i in m_by_index]
        if len(shared_indexes) < 2:
            continue

        detected = False
        for i in range(len(shared_indexes)):
            for j in range(i + 1, len(shared_indexes)):
                a = d_by_index[shared_indexes[i]]
                b = d_by_index[shared_indexes[j]]
                ma = m_by_index[shared_indexes[i]]
                mb = m_by_index[shared_indexes[j]]

                same_row_desktop = abs(a.get("y", 0) - b.get("y", 0)) <= 24
                horizontal_desktop = abs(a.get("x", 0) - b.get("x", 0)) >= 80
                same_column_mobile = abs(ma.get("x", 0) - mb.get("x", 0)) <= 40
                vertical_mobile = abs(ma.get("y", 0) - mb.get("y", 0)) >= 60

                if same_row_desktop and horizontal_desktop and same_column_mobile and vertical_mobile:
                    breakpoint_stage = "mobile"
                    breakpoint_width = int(mobile.get("viewport", {}).get("width") or 390)
                    breakpoint_lower_bound = breakpoint_width
                    breakpoint_upper_bound = int(tablet.get("viewport", {}).get("width") or 768)
                    t_items = tablet_groups.get(parent_key, [])
                    t_by_index = {item.get("siblingIndex"): item for item in t_items}
                    ta = t_by_index.get(shared_indexes[i])
                    tb = t_by_index.get(shared_indexes[j])
                    if ta and tb:
                        same_column_tablet = abs(ta.get("x", 0) - tb.get("x", 0)) <= 40
                        vertical_tablet = abs(ta.get("y", 0) - tb.get("y", 0)) >= 60
                        if same_column_tablet and vertical_tablet:
                            breakpoint_stage = "tablet"
                            breakpoint_width = int(tablet.get("viewport", {}).get("width") or 768)
                            breakpoint_lower_bound = breakpoint_width
                            breakpoint_upper_bound = int(desktop.get("viewport", {}).get("width") or 1440)

                    result["row_to_column_groups"].append({
                        "parent": parent_key,
                        "siblings": [shared_indexes[i], shared_indexes[j]],
                        "breakpoint_stage": breakpoint_stage,
                        "breakpoint_width": breakpoint_width,
                        "breakpoint_lower_bound": breakpoint_lower_bound,
                        "breakpoint_upper_bound": breakpoint_upper_bound,
                        "desktop": {
                            "a": {"x": a.get("x"), "y": a.get("y")},
                            "b": {"x": b.get("x"), "y": b.get("y")},
                        },
                        "mobile": {
                            "a": {"x": ma.get("x"), "y": ma.get("y")},
                            "b": {"x": mb.get("x"), "y": mb.get("y")},
                        },
                    })
                    detected = True
                    break
            if detected:
                break

    result["wrapped_elements"] = result["wrapped_elements"][:30]
    result["stacking_signals"] = result["stacking_signals"][:30]
    result["row_to_column_groups"] = result["row_to_column_groups"][:30]
    return result


def detect_technologies(soup):
    parts=[]
    parts.extend(x.get("src","") for x in soup.find_all("script"))
    parts.extend(x.get("href","") for x in soup.find_all("link"))
    parts.extend(" ".join(x.get("class",[])) for x in soup.find_all(class_=True))
    haystack=" ".join(parts).casefold()
    checks={"Bootstrap":("bootstrap",),"Tailwind CSS":("tailwind",),"React":("react",),"Next.js":("_next/","nextjs"),"Vue":("vue",),"Swiper":("swiper",),"Slick Carousel":("slick",),"jQuery":("jquery",),"Font Awesome":("font-awesome","fontawesome")}
    return [name for name,needles in checks.items() if any(n in haystack for n in needles)]

async def analyze_url(url: str):
    if not url.startswith(("http://","https://")):
        url="https://"+url
    parsed=urlparse(url)
    if not parsed.netloc:
        raise ValueError("Invalid URL")
    ensure_public_url(url)
    rendered=False
    viewport_snapshots={}
    try:
        viewport_pages=await render_multi_viewport(url)
        page=viewport_pages["desktop"]
        html=page["html"]
        final_url=page["final_url"]
        status_code=page["status_code"]
        snapshot=page.get("snapshot",{})
        viewport_snapshots={
            name: data.get("snapshot",{})
            for name, data in viewport_pages.items()
        }
        rendered=True
    except Exception:
        async with httpx.AsyncClient(follow_redirects=True,timeout=20,headers=HEADERS) as client:
            response=await client.get(url)
            response.raise_for_status()
        html=response.text
        final_url=str(response.url)
        status_code=response.status_code
        snapshot={}
    soup=BeautifulSoup(html,"lxml")
    title=soup.title.get_text(" ",strip=True) if soup.title else ""
    description=""
    meta=soup.find("meta",attrs={"name":re.compile("description$",re.I)})
    if meta: description=meta.get("content","").strip()
    headings=snapshot.get("headings",[]) if snapshot else []
    if not headings:
        for tag in soup.find_all(["h1","h2","h3"]):
            text=tag.get_text(" ",strip=True)
            if text: headings.append({"level":tag.name,"text":text[:180]})
    nav=snapshot.get("links",[]) if snapshot else []
    if not nav:
        for a in soup.find_all("a",href=True):
            text=a.get_text(" ",strip=True)
            href=urljoin(final_url,a.get("href"))
            if text and href.startswith(("http://","https://")):
                nav.append({"text":text[:120],"href":href})
    forms=[]
    for form in soup.find_all("form"):
        fields=[]
        for field in form.find_all(["input","textarea","select","button"]):
            fields.append({"tag":field.name,"type":field.get("type",""),"name":field.get("name",""),"placeholder":field.get("placeholder","")})
        forms.append({"action":urljoin(final_url,form.get("action", "")),"method":form.get("method","get").upper(),"fields":fields[:30]})
    sections=[]
    if snapshot and snapshot.get("landmarks"):
        for item in snapshot.get("landmarks",[]):
            text=item.get("text","")
            if text:
                fake=soup.new_tag(item.get("tag") or "section")
                fake["id"]=item.get("id","")
                fake["class"]=(item.get("className","") or "").split()
                fake["role"]=item.get("role","")
                sections.append({"type":infer_section(fake),"tag":item.get("tag","") or "section","id":item.get("id", ""),"class":item.get("className","")[:180],"preview":text[:220]})
    else:
        candidates=soup.find_all(["header","nav","main","section","article","aside","footer"])
        role_names={"main","region","navigation","feed"}
        candidates += [tag for tag in soup.find_all(True) if str(tag.get("role","")).casefold() in role_names]
        candidates += [tag for tag in soup.find_all(True) if tag.name and (tag.name.startswith("ytd-") or tag.name.startswith("yt-"))]
        seen=set()
        for tag in candidates:
            key=id(tag)
            if key in seen:
                continue
            seen.add(key)
            text=tag.get_text(" ",strip=True)
            if text:
                sections.append({"type":infer_section(tag),"tag":tag.name,"id":tag.get("id", ""),"class":" ".join(tag.get("class",[])[:4]),"preview":text[:220]})
    buttons=snapshot.get("buttons",[]) if snapshot else []
    if not buttons:
        for b in soup.find_all(["button"]):
            text=b.get_text(" ",strip=True)
            if text: buttons.append(text[:120])
    scripts=[urljoin(final_url,s.get("src")) for s in soup.find_all("script",src=True)]
    styles=[urljoin(final_url,l.get("href")) for l in soup.find_all("link",href=True) if "stylesheet" in (l.get("rel") or [])]
    images=snapshot.get("images",[]) if snapshot else []
    if not images:
        for image in soup.find_all("img"):
            src=image.get("src") or image.get("data-src") or ""
            if src:
                images.append({"src":urljoin(final_url,src),"alt":image.get("alt","")[:160]})
    marker_text=" ".join(" ".join(tag.get("class",[]))+" "+tag.get("id","") for tag in soup.find_all(True) if tag.get("class") or tag.get("id")).casefold()
    interactions=[]
    if any(x in marker_text for x in ("carousel","slider","slideshow","swiper","slick")): interactions.append("carousel_or_slideshow")
    if any(x in marker_text for x in ("accordion","faq")): interactions.append("accordion_or_faq")
    if any(x in marker_text for x in ("modal","dialog","popup")): interactions.append("modal_or_popup")
    if any(x in marker_text for x in ("dropdown","menu")): interactions.append("dropdown_or_menu")
    if forms: interactions.append("form_submission")
    section_order=[]
    for section in sections:
        if section["type"] not in section_order: section_order.append(section["type"])
    rebuild_plan=[]
    if section_order:
        rebuild_plan.append("Create page sections in this order: "+", ".join(section_order)+".")
    if interactions:
        rebuild_plan.append("Recreate equivalent user interactions with original implementation: "+", ".join(interactions)+".")
    if images:
        rebuild_plan.append("Use original or licensed replacement imagery; reference layout and aspect ratios only.")
    if forms:
        rebuild_plan.append("Rebuild form flows with new backend handling and validation appropriate to the client project.")
    if detect_technologies(soup):
        rebuild_plan.append("Detected frontend hints: "+", ".join(detect_technologies(soup))+". Use only if suitable for the new project.")

    return {
        "requested_url":url,
        "final_url":final_url,
        "status_code":status_code,
        "site":{"title":title,"description":description,"domain":urlparse(final_url).netloc},
        "blueprint":{"section_order":section_order,"interactions":interactions,"technologies":detect_technologies(soup),"rebuild_plan":rebuild_plan,"rendered_browser":rendered,"responsive_behavior":infer_responsive_behavior(viewport_snapshots)},
        "design": snapshot.get("design",{}) if snapshot else {},
        "viewport_snapshots": viewport_snapshots,
        "structure":{"headings":headings[:80],"sections":sections[:80],"forms":forms[:20],"buttons":buttons[:50]},
        "navigation":nav[:120],
        "resources":{"images":images[:120],"scripts":scripts[:80],"stylesheets":styles[:80]},
        "notes":["Blueprint is based on publicly delivered page structure and observable frontend content.","Rebuild should use original code, branding, assets, and copy unless reuse is authorized."]
    }
