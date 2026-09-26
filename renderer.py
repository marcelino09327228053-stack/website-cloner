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


async def render_page(url):
    if not public_host(url):
        raise ValueError("Only public website URLs are allowed")
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True)
        context=await browser.new_context(
            viewport={"width":1440,"height":1000},
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
    const sample=Array.from(document.querySelectorAll('header,nav,main,section,article,footer,button,a,h1,h2,h3'))
      .filter(e => e.getClientRects().length).slice(0,80)
      .map(e => { const s=getComputedStyle(e),r=e.getBoundingClientRect(); return {tag:e.tagName.toLowerCase(),background:s.backgroundColor,color:s.color,fontSize:s.fontSize,fontWeight:s.fontWeight,borderRadius:s.borderRadius,display:s.display,position:s.position,width:Math.round(r.width),height:Math.round(r.height),x:Math.round(r.x),y:Math.round(r.y)}; });
    return {viewport:{width:window.innerWidth,height:window.innerHeight},page:{Background:body.backgroundColor,color:body.color,fontFamily:body.fontFamily,fontSize:body.fontSize},root:{background:root.backgroundColor},elements:sample};
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
