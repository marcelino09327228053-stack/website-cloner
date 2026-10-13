import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from fastapi.testclient import TestClient
from playwright.async_api import async_playwright
import main
import project_manager as pm
from business_layout import describe_website

class DescriptionTests(unittest.IsolatedAsyncioTestCase):
 async def test_description_ui_build_and_reopen(self):
  for text,kind in [('A modern hotel website in blue','hotel'),('An auto shop with car repair services','auto'),('A massage and wellness spa website','spa'),('A website for my accounting services','business')]:
   self.assertEqual(describe_website(text)['blueprint']['brief']['kind'],kind)
  with TemporaryDirectory() as folder,patch.object(pm,'BASE',Path(folder)/'source'),patch.object(pm,'REGISTRY',Path(folder)/'registry.json'):
   target=Path(folder)/'Hotel';target.mkdir()
   with patch.object(main,'choose_project_folder',return_value={'project_name':'Hotel','project_path':str(target)}):
    client=TestClient(main.app)
    self.assertEqual(client.post('/api/describe',json={'description':'short'}).status_code,400)
    async with async_playwright() as pw:
     browser=await pw.chromium.launch();page=await browser.new_page();errors=[]
     page.on('pageerror',lambda e:errors.append(str(e)))
     async def serve(route):
      r=route.request;res=client.request(r.method,r.url,content=r.post_data,headers=r.headers)
      await route.fulfill(status=res.status_code,headers=dict(res.headers),body=res.content)
     await page.route('http://app.test/**',serve);await page.goto('http://app.test/')
     await page.locator('#openFolder').click();await page.locator('#descriptionMode').click()
     brief='I want a hotel website with blue theme.\nName: Sea & Sky\nServices: Ocean rooms, Dining\nLocation: Cebu'
     await page.locator('#description').fill(brief);await page.locator('#build').click();await page.locator('#preview').wait_for()
     preview=await page.locator('#preview').get_attribute('href')
     self.assertIn('Sea &amp; Sky',(target/'index.html').read_text(encoding='utf-8'))
     self.assertIn('Ocean rooms',(target/'index.html').read_text(encoding='utf-8'))
     await page.reload();await page.get_by_role('button',name='Open Project').click()
     self.assertEqual(await page.locator('#description').input_value(),brief)
     for w,h in [(1440,900),(390,844)]:
      await page.set_viewport_size({'width':w,'height':h})
      self.assertFalse(await page.evaluate('document.documentElement.scrollWidth>innerWidth'))
      self.assertFalse(await page.evaluate('document.documentElement.scrollHeight>innerHeight'))
     await page.goto('http://app.test'+preview);await page.locator('#menu').click();self.assertTrue(await page.locator('#links').is_visible())
     self.assertFalse(await page.evaluate('document.documentElement.scrollWidth>innerWidth'))
     self.assertEqual(errors,[]);await browser.close()

if __name__=='__main__':unittest.main()
