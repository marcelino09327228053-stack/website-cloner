from urllib.parse import urlparse
import ipaddress
import socket
from playwright.async_api import async_playwright


def public_host(url):
    host=urlparse(url).hostname
    if not host or host.lower() in {"localhost","localhost.localdomain"}:
        return False
    try:
        addresses={x[4][0] for x in socket.getaddrinfo(host,None)}
    except socket.gaierror:
        return False
    for address in addresses:
        ip=ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


VIEWPORTS = {
    "desktop": {"width":1440, "height":1000},
    "tablet": {"width":768, "height":1024},
    "mobile": {"width":390, "height":844},
}


async def render_multi_viewport(url):
    results = {}
    for name, viewport in VIEWPORTS.items():
        results[name] = await render_page(url, viewport)
    return results


async def render_page(url, viewport=None):
    if not public_host(url):
        raise ValueError("Only public website URLs are allowed")
    viewport = viewport or {"width":1440,"height":1000}
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True)
        context=await browser.new_context(
            viewport=viewport,
            user_agent="Mozilla/5.0 Website Reference Analyzer/0.4",
        )
        page=await context.new_page()
        response=await page.goto(url,wait_until="domcontentloaded",timeout=30000)
        try:
            await page.wait_for_load_state("networkidle",timeout=8000)
        except Exception:
            pass
        await page.wait_for_timeout(2500)
        final_url=page.url
        if not public_host(final_url):
            await browser.close()
            raise ValueError("Redirected to a non-public address")
        html=await page.content()
        snapshot=await page.evaluate("""
() => ({
  headings: Array.from(document.querySelectorAll('h1,h2,h3'))
    .filter(e => e.getClientRects().length)
    .slice(0,100)
    .map(e => ({level:e.tagName.toLowerCase(), text:(e.innerText || '').trim().slice(0,180)}))
    .filter(e => e.text),
  buttons: Array.from(document.querySelectorAll('button,[role="button"]'))
    .filter(e => e.getClientRects().length)
    .slice(0,120)
    .map(e => (e.innerText || e.getAttribute('aria-label') || '').trim().slice(0,160))
    .filter(Boolean),
  images: Array.from(document.images)
    .filter(e => e.getClientRects().length)
    .slice(0,160)
    .map(e => ({src:e.currentSrc || e.src || '', alt:(e.alt || '').slice(0,160)}))
    .filter(e => e.src),
  links: Array.from(document.querySelectorAll('a[href]'))
    .filter(e => e.getClientRects().length)
    .slice(0,180)
    .map(e => ({text:(e.innerText || e.getAttribute('aria-label') || '').trim().slice(0,140), href:e.href}))
    .filter(e => e.text),
  landmarks: Array.from(document.querySelectorAll('main,nav,header,footer,section,article,[role="main"],[role="navigation"],[role="region"],[role="feed"]'))
    .filter(e => e.getClientRects().length)
    .slice(0,120)
    .map(e => ({tag:e.tagName.toLowerCase(), role:e.getAttribute('role') || '', id:e.id || '', className:typeof e.className === 'string' ? e.className.slice(0,180) : '', text:(e.innerText || '').trim().slice(0,260)}))
    .filter(e => e.text),
  design: (() => {
    const body=getComputedStyle(document.body);
    const root=getComputedStyle(document.documentElement);
    const pathOf=e => {
      if(!e) return '';
      const parts=[];
      let n=e;
      while(n && n.nodeType===1 && parts.length<10){
        const tag=n.tagName.toLowerCase();
        if(n.id){ parts.unshift(tag+'#'+n.id); break; }
        const p=n.parentElement;
        const index=p ? Array.prototype.indexOf.call(p.children,n)+1 : 1;
        parts.unshift(tag+':nth-child('+index+')');
        n=p;
      }
      return parts.join('>');
    };
    // Separate DOM-order sample: hidden nodes must not displace layout samples.
    const visibilityCandidates=Array.from(document.body.querySelectorAll('*'))
      .filter(e => !['SCRIPT','STYLE','TEMPLATE','NOSCRIPT','META','LINK'].includes(e.tagName));
    const visibilityElements=visibilityCandidates.slice(0,2000).map(e => ({
      domPath:pathOf(e),
      tag:e.tagName.toLowerCase(),
      id:e.id || '',
      role:e.getAttribute('role') || '',
      controls:e.getAttribute('aria-controls') || '',
      links:(e.matches('nav,[role="navigation"]') ? Array.from(e.querySelectorAll('a[href]')).slice(0,6).map(a => ({text:(a.textContent || '').trim().slice(0,140)})) : []),
      visible:e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true,contentVisibilityAuto:true}),
    }));
    const regionCandidates=Array.from(document.querySelectorAll('section,article,main,div'))
      .filter(e => {
        const r=e.getBoundingClientRect();
        if(r.width<window.innerWidth*.3 || r.height<100 || !e.querySelector('h1,h2,h3')) return false;
        const children=Array.from(e.children).filter(c=>c.getBoundingClientRect().width>40);
        const row=children.some((a,i)=>children.slice(i+1).some(b=>Math.abs(a.getBoundingClientRect().y-b.getBoundingClientRect().y)<24 && Math.abs(a.getBoundingClientRect().x-b.getBoundingClientRect().x)>80));
        const contentGroups=children.filter(c=>c.querySelector('h1,h2,h3,img,video,canvas,svg') || c.matches('img,video,canvas,svg'));
        return e.matches('section,article') || row || contentGroups.length>=2;
      });
    // Prefer distinct leaf regions over a wrapper containing the entire page.
    const regions=regionCandidates.filter(e=>!regionCandidates.some(other=>other!==e && e.contains(other)))
      .slice(0,20).map(e=>{
        const r=e.getBoundingClientRect(),s=getComputedStyle(e);
        return {domPath:pathOf(e),tag:e.tagName.toLowerCase(),x:Math.round(r.x),y:Math.round(r.y),
          width:Math.round(r.width),height:Math.round(r.height),gap:s.gap,
          heading:(e.querySelector('h1,h2,h3')?.textContent || '').trim().slice(0,140),
          headingLevel:e.querySelector('h1,h2,h3')?.tagName.toLowerCase(),
          children:Array.from(e.children).filter(c=>c.getBoundingClientRect().width>40).slice(0,8).map(c=>{
            const b=c.getBoundingClientRect();
            return {domPath:pathOf(c),x:Math.round(b.x),y:Math.round(b.y),width:Math.round(b.width),height:Math.round(b.height),
              heading:(c.matches('h1,h2,h3')?c.textContent:c.querySelector('h1,h2,h3')?.textContent || '').trim().slice(0,140),
              media:c.matches('img,video,canvas,svg') || !!c.querySelector('img,video,canvas,svg')};
          })};
      });
    const sample=Array.from(document.querySelectorAll('header,nav,main,section,article,footer,div,button,a,h1,h2,h3'))
      .slice(0,120)
      .map(e => { const s=getComputedStyle(e),r=e.getBoundingClientRect(),p=e.parentElement; return {tag:e.tagName.toLowerCase(),id:e.id || '',className:typeof e.className === 'string' ? e.className.slice(0,180) : '',text:(e.innerText || '').trim().replace(/\\s+/g,' ').slice(0,140),parentTag:p ? p.tagName.toLowerCase() : '',parentId:p ? (p.id || '') : '',parentClassName:p && typeof p.className === 'string' ? p.className.slice(0,180) : '',domPath:pathOf(e),parentDomPath:pathOf(p),siblingIndex:p ? Array.prototype.indexOf.call(p.children,e) : -1,visible:!!(e.getClientRects().length && s.display!=="none" && s.visibility!=="hidden" && parseFloat(s.opacity || "1")>0),background:s.backgroundColor,backgroundImage:s.backgroundImage,color:s.color,fontSize:s.fontSize,fontWeight:s.fontWeight,borderRadius:s.borderRadius,border:s.border,boxShadow:s.boxShadow,display:s.display,position:s.position,margin:s.margin,padding:s.padding,gap:s.gap,flexDirection:s.flexDirection,justifyContent:s.justifyContent,alignItems:s.alignItems,gridTemplateColumns:s.gridTemplateColumns,objectFit:s.objectFit,opacity:s.opacity,width:Math.round(r.width),height:Math.round(r.height),x:Math.round(r.x),y:Math.round(r.y)}; });
    return {viewport:{width:window.innerWidth,height:window.innerHeight},page:{Background:body.backgroundColor,color:body.color,fontFamily:body.fontFamily,fontSize:body.fontSize},root:{background:root.backgroundColor},elements:sample,regions,visibilityElements,visibilitySampleTruncated:visibilityCandidates.length>2000};
  })()
})
""")
        status=response.status if response else 200
        await browser.close()
        return {
            "html":html,
            "final_url":final_url,
            "status_code":status,
            "rendered":True,
            "snapshot":snapshot,
        }
