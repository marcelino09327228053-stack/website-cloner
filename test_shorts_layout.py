import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from fastapi.testclient import TestClient
from playwright.async_api import async_playwright
import main
import project_manager as pm
from template_selection import reference_template

class ShortsTests(unittest.IsolatedAsyncioTestCase):
 async def test_tiktok_build_and_feed(self):
  self.assertEqual(reference_template('https://vm.tiktok.com/abc'),'short_video')
  self.assertIsNone(reference_template('https://tiktok.com.fake.test'))
  with TemporaryDirectory() as folder,patch.object(pm,'BASE',Path(folder)/'source'),patch.object(pm,'REGISTRY',Path(folder)/'registry.json'):
   client=TestClient(main.app)
   analysis=client.post('/api/analyze',json={'url':'https://www.tiktok.com/'}).json()
   self.assertEqual(analysis['blueprint']['layout_kind'],'short_video')
   target=Path(folder)/'Loop';result=client.post('/api/build',json={'analysis':analysis,'project_path':str(target),'project_name':'Loop'})
   self.assertEqual(result.status_code,200);url=result.json()['preview_url']
   async with async_playwright() as pw:
    browser=await pw.chromium.launch();page=await browser.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    async def serve(route):
     r=route.request;response=client.request(r.method,r.url,content=r.post_data,headers=r.headers)
     await route.fulfill(status=response.status_code,headers=dict(response.headers),body=response.content)
    await page.route('http://app.test/**',serve);await page.goto('http://app.test'+url)
    self.assertEqual(await page.locator('.clip').count(),6)
    first=page.locator('.clip').first
    await first.locator('[data-list=liked]').click();await first.locator('[data-list=saved]').click();await first.locator('.follow').click()
    await first.get_by_role('button',name='Pause clip',exact=True).click();value=float(await first.locator('.timeline').input_value());await page.wait_for_timeout(150);self.assertEqual(float(await first.locator('.timeline').input_value()),value)
    await first.locator('.timeline').fill('8');await first.get_by_role('button',name='Play clip',exact=True).click()
    await first.get_by_role('button',name='Notes Somewhere',exact=False).click();await page.locator('#noteInput').fill('Love this color palette.');await page.locator('#noteForm button').click();await page.get_by_role('button',name='Close comments').click()
    await page.reload();await page.locator('[data-view=saved]').click();self.assertEqual(await page.locator('.clip').count(),1)
    await page.locator('[data-view=following]').click();self.assertEqual(await page.locator('.clip').count(),2)
    await page.locator('[data-view=all]').click();await page.locator('#search').fill('orbit');self.assertEqual(await page.locator('.clip').count(),1)
    await page.locator('#search').fill('nothing found');self.assertTrue(await page.locator('#empty').is_visible());await page.locator('#reset').click()
    await page.locator('#categories').get_by_role('button',name='Motion',exact=True).click();self.assertEqual(await page.locator('.clip').count(),2)
    await page.locator('[data-view=all]').click();await page.locator('#feed').focus();await page.keyboard.press('ArrowDown');await page.wait_for_timeout(600);self.assertIn('02',await page.locator('#feedCounter').inner_text())
    await page.locator('[data-view=all]').click()
    out=Path('C:/Users/marjun/.codex/visualizations/2026/09/26/01a0de87-b674-7683-b13e-036d953cc2de')
    for w,h in [(1440,1000),(768,1024),(390,844)]:
     await page.set_viewport_size({'width':w,'height':h});await page.wait_for_timeout(200)
     self.assertFalse(await page.evaluate('document.documentElement.scrollWidth>innerWidth'))
     await page.screenshot(path=str(out/f'loop-{w}.png'))
    self.assertFalse(await page.evaluate('document.documentElement.scrollHeight>innerHeight'))
    identity=json.loads((target/'project.json').read_text())['project_id']
    self.assertEqual(client.post('/api/projects/'+identity+'/rename',json={'name':'Loop Renamed'}).status_code,200)
    await page.reload();await page.locator('[data-view=saved]').click();self.assertEqual(await page.locator('.clip').count(),1)
    self.assertEqual(errors,[]);await browser.close()

if __name__=='__main__':unittest.main()
