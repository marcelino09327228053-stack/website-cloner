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
        "blueprint":{"section_order":section_order,"interactions":interactions,"technologies":detect_technologies(soup),"rebuild_plan":rebuild_plan,"rendered_browser":rendered},
        "design": snapshot.get("design",{}) if snapshot else {},
        "structure":{"headings":headings[:80],"sections":sections[:80],"forms":forms[:20],"buttons":buttons[:50]},
        "navigation":nav[:120],
        "resources":{"images":images[:120],"scripts":scripts[:80],"stylesheets":styles[:80]},
        "notes":["Blueprint is based on publicly delivered page structure and observable frontend content.","Rebuild should use original code, branding, assets, and copy unless reuse is authorized."]
    }
