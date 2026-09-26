import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.async_api import async_playwright
from blueprint_sections import normalize_sections, readable_foreground
from builder import build_site
from renderer import VIEWPORTS


class BlueprintTests(unittest.IsolatedAsyncioTestCase):
    async def test_low_contrast_source_defaults_are_corrected(self):
        self.assertEqual(readable_foreground('rgb(16, 20, 24)', 'rgb(0, 0, 0)'), '#f1f5f9')
        self.assertEqual(readable_foreground('#ffffff', '#eeeeee'), '#17212b')
        self.assertEqual(readable_foreground('#ffffff', '#17212b'), '#17212b')

    async def test_measured_sections_drive_distinct_layouts(self):
        script = next(n.args[0].value for n in ast.walk(ast.parse(Path('renderer.py').read_text()))
                      if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'evaluate')
        fixture = '''<style>body{margin:0}section{padding:40px;min-height:240px}
          .split,.cards{display:grid;gap:30px}.split{grid-template-columns:2fr 1fr}
          .cards{grid-template-columns:repeat(3,1fr)}svg{width:100%;height:200px}
          @media(max-width:1000px){.cards{grid-template-columns:repeat(2,1fr)}}
          @media(max-width:600px){.split,.cards{grid-template-columns:1fr}}</style>
          <section id="intro" class="split"><div><h1>Build with purpose</h1><p>Text</p></div><svg></svg></section>
          <section id="tools" class="cards"><div><h2>Design</h2></div><div><h2>Develop</h2></div><div><h2>Deliver</h2></div></section>
          <section id="story"><h2>Our approach</h2><p>Details</p></section>'''
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            try:
                page = await browser.new_page()
                snapshots = {}
                for name, viewport in VIEWPORTS.items():
                    await page.set_viewport_size(viewport)
                    await page.set_content(fixture)
                    snapshots[name] = await page.evaluate(script)
                sections = normalize_sections(snapshots)
                self.assertEqual([s['columns'] for s in sections], [2,3,1])
                self.assertEqual([v['columns'] for v in sections[1]['responsive']], [2,1])
                self.assertEqual([v['max_width'] for v in sections[1]['responsive']], [1104,579])
                self.assertEqual(sections, normalize_sections(snapshots))
                with TemporaryDirectory() as folder:
                    build_site({'blueprint': {'sections': sections}}, project_dir=folder)
                    html = Path(folder,'index.html').read_text(encoding='utf-8')
                    self.assertNotIn('premium-hero', html)
                    self.assertNotIn('duration', html)
                    await page.goto('about:blank')
                    await page.set_content(html.replace('<script src="app.js"></script>', '').replace('<link rel="stylesheet" href="style.css">',''))
                    await page.add_style_tag(content=Path(folder,'style.css').read_text())
                    for width, counts in ((1440,[2,3,1]),(768,[2,2,1]),(390,[1,1,1])):
                        await page.set_viewport_size({'width':width,'height':900})
                        actual = await page.locator('.bp-layout').evaluate_all('(nodes)=>nodes.map(e=>getComputedStyle(e).gridTemplateColumns.split(" ").length)')
                        self.assertEqual(actual,counts)
                        self.assertFalse(await page.evaluate('document.documentElement.scrollWidth>innerWidth'))
                    self.assertEqual(await page.locator('h1').count(),1)
                    for link in await page.locator('.nav-links a').all():
                        self.assertEqual(await page.locator(await link.get_attribute('href')).count(),1)
            finally:
                await browser.close()

    async def test_fallback_keeps_repeated_section_types(self):
        sections=normalize_sections({}, {'sections':[{'type':'features'},{'type':'features'}]})
        self.assertEqual(len(sections),2)
        self.assertNotEqual(sections[0]['id'],sections[1]['id'])


if __name__ == '__main__':
    unittest.main()
