import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from playwright.async_api import async_playwright
from builder import build_site
from business_layout import describe_website

class PremiumBusinessTests(unittest.IsolatedAsyncioTestCase):
 async def test_both_layouts_and_local_planner(self):
  async with async_playwright() as pw:
   browser=await pw.chromium.launch();page=await browser.new_page();errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   for kind in ['hotel','auto shop']:
    with TemporaryDirectory() as folder:
     build_site(describe_website('A beautiful '+kind+' website in blue.\nName: Original Business\nServices: Service One, Service Two'),folder,'Sample')
     await page.goto((Path(folder)/'index.html').as_uri())
     self.assertEqual(await page.locator('.service-card').count(),2)
     for width in [1440,768,390]:
      await page.set_viewport_size({'width':width,'height':900})
      self.assertFalse(await page.evaluate('document.documentElement.scrollWidth>innerWidth'))
     await page.locator('.hero [data-service]').click();await page.locator('#planDate').fill('2027-01-10')
     await page.locator('#planExtra').fill('Sedan' if kind=='auto shop' else '2');await page.locator('#planNotes').fill('Morning preferred')
     await page.locator('#planForm .cta').click();self.assertIn('Plan saved',await page.locator('#planStatus').inner_text())
     await page.locator('#closePlanner').click();await page.reload();await page.locator('.hero [data-service]').click()
     self.assertEqual(await page.locator('#planNotes').input_value(),'Morning preferred')
   self.assertEqual(errors,[]);await browser.close()

if __name__=='__main__':unittest.main()
