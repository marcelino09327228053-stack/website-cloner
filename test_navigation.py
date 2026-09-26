import ast
import copy
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.async_api import async_playwright
from analyzer import infer_responsive_behavior
from builder import build_site
from navigation import infer_navigation_mapping
from renderer import VIEWPORTS


class NavigationTests(unittest.IsolatedAsyncioTestCase):
    async def test_semantic_mapping_and_generated_menu(self):
        tree = ast.parse(Path('renderer.py').read_text())
        script = next(n.args[0].value for n in ast.walk(tree)
                      if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                      and n.func.attr == 'evaluate')
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            try:
                page = await browser.new_page()
                for cutoff, expected in ((600, 579), (1000, 1104)):
                    data = {}
                    for name, viewport in VIEWPORTS.items():
                        await page.set_viewport_size(viewport)
                        await page.set_content(f'''<style>button{{display:none}}
                          @media(max-width:{cutoff}px){{nav{{display:none}}button{{display:block}}}}
                          </style><nav id="primary"><a href="#about">About</a></nav>
                          <button aria-controls="primary">Menu</button>''')
                        data[name] = await page.evaluate(script)
                    result = infer_responsive_behavior(data)
                    mapping = result['navigation_mapping']
                    self.assertEqual(mapping['navigation_path'], 'nav#primary')
                    self.assertEqual(mapping['links'], [{'text': 'About'}])
                    design = copy.deepcopy(data['desktop']['design'])
                    button = next(e for e in design['visibilityElements'] if e['tag'] == 'button')
                    button['controls'] = 'unrelated'
                    self.assertIsNone(infer_navigation_mapping(design, result))
                    button['controls'] = 'primary'
                    design['visibilityElements'].append(copy.deepcopy(button))
                    self.assertIsNone(infer_navigation_mapping(design, result))
                    incomplete = copy.deepcopy(result)
                    incomplete['visibility_changes'][0]['tablet_visible'] = None
                    self.assertIsNone(infer_navigation_mapping(data['desktop']['design'], incomplete))
                    await self.check_generated(page, result, expected)
                await self.check_generated(page, {}, 800)
            finally:
                await browser.close()

    async def check_generated(self, page, result, breakpoint):
        await page.goto('about:blank')
        with TemporaryDirectory() as folder:
            build_site({'blueprint': {'responsive_behavior': result}}, project_dir=folder)
            html = Path(folder, 'index.html').read_text(encoding='utf-8')
            css = Path(folder, 'style.css').read_text(encoding='utf-8')
            js = Path(folder, 'app.js').read_text(encoding='utf-8')
            await page.set_content(html.replace('<link rel="stylesheet" href="style.css">', '')
                                   .replace('<script src="app.js"></script>', ''))
            await page.add_style_tag(content=css)
            await page.add_script_tag(content=js)
            toggle = page.locator('.navigation-toggle')
            links = page.locator('#generated-navigation')
            for width in sorted({320, 390, 579, 768, 800, 801, 1104, 1440,
                                 breakpoint - 1, breakpoint, breakpoint + 1}):
                await page.set_viewport_size({'width': width, 'height': 900})
                await page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                if width > breakpoint:
                    self.assertTrue(await links.is_visible(), width)
                    self.assertFalse(await toggle.is_visible(), width)
                else:
                    self.assertTrue(await toggle.is_visible(), width)
                    self.assertFalse(await links.is_visible(), width)
                    await toggle.focus()
                    await page.keyboard.press('Enter')
                    self.assertTrue(await links.is_visible(), width)
                    self.assertEqual(await toggle.get_attribute('aria-expanded'), 'true')
                    await page.keyboard.press('Escape')
                    self.assertFalse(await links.is_visible(), width)
                    self.assertTrue(await toggle.evaluate('(e)=>e===document.activeElement'))
                    await toggle.click()
                    await links.locator('a').first.click()
                    self.assertEqual(await toggle.get_attribute('aria-expanded'), 'false')
            await page.set_viewport_size({'width': 390, 'height': 900})
            await page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
            await toggle.click()
            await page.set_viewport_size({'width': 1440, 'height': 900})
            await page.wait_for_function("document.querySelector('.navigation-toggle').getAttribute('aria-expanded')==='false'")
            self.assertTrue(await links.is_visible())


if __name__ == '__main__':
    unittest.main()
