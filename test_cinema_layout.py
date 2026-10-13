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

class CinemaTests(unittest.IsolatedAsyncioTestCase):
 async def test_netflix_catalog_and_player(self):
  self.assertEqual(reference_template('https://www.netflix.com/browse'),'cinema')
  self.assertIsNone(reference_template('https://netflix.com.fake.test'))
  with TemporaryDirectory() as folder,patch.object(pm,'BASE',Path(folder)/'source'),patch.object(pm,'REGISTRY',Path(folder)/'registry.json'):
   client=TestClient(main.app);analysis=client.post('/api/analyze',json={'url':'https://www.netflix.com/'}).json()
   self.assertEqual(analysis['blueprint']['layout_kind'],'cinema')
   target=Path(folder)/'Nocturne';response=client.post('/api/build',json={'analysis':analysis,'project_path':str(target),'project_name':'Nocturne'})
   self.assertEqual(response.status_code,200);url=response.json()['preview_url']
   async with async_playwright() as pw:
    browser=await pw.chromium.launch();page=await browser.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    async def serve(route):
     r=route.request;res=client.request(r.method,r.url,content=r.post_data,headers=r.headers)
     await route.fulfill(status=res.status_code,headers=dict(res.headers),body=res.content)
    await page.route('http://app.test/**',serve);await page.goto('http://app.test'+url)
    self.assertIn('North',await page.locator('#heroTitle').text_content())
    await page.locator('#nextHero').click();self.assertIn('Signal',await page.locator('#heroTitle').text_content());await page.locator('#previousHero').click()
    await page.locator('#heroSave').click();await page.locator('[data-view=saved]').click();self.assertEqual(await page.locator('.movie-card').count(),1)
    await page.locator('.poster').click();self.assertTrue(await page.locator('#detailsDialog').is_visible());await page.locator('#detailPlay').click()
    await page.locator('#togglePlay').click();value=float(await page.locator('#seek').input_value());await page.wait_for_timeout(120);self.assertEqual(float(await page.locator('#seek').input_value()),value)
    await page.locator('#seek').fill('8');await page.locator('#closePlayer').click();await page.reload()
    await page.locator('#heroPlay').click();self.assertGreaterEqual(float(await page.locator('#seek').input_value()),8)
    await page.locator('#fullscreen').click();await page.wait_for_function('!!document.fullscreenElement')
    await page.locator('#closePlayer').click();await page.wait_for_function('!document.fullscreenElement && !document.querySelector("#playerDialog").open')
    await page.locator('[data-view=series]').click();self.assertEqual(await page.locator('.movie-card').count(),3)
    await page.locator('#search').fill('signal');self.assertEqual(await page.locator('.movie-card').count(),1)
    await page.locator('#search').fill('nothing found');self.assertTrue(await page.locator('#empty').is_visible());await page.locator('#reset').click()
    await page.locator('#genres').get_by_role('button',name='Sci-fi',exact=True).click();self.assertEqual(await page.locator('.movie-card').count(),2)
    await page.locator('#sort').select_option('title');self.assertIn('Other',await page.locator('.card-title').first.inner_text())
    identity=json.loads((target/'project.json').read_text(encoding='utf-8'))['project_id'];self.assertEqual(client.post('/api/projects/'+identity+'/rename',json={'name':'Nocturne Renamed'}).status_code,200)
    await page.reload();await page.locator('[data-view=saved]').click();self.assertEqual(await page.locator('.movie-card').count(),1)
    await page.locator('[data-view=home]').click();await page.locator('#sort').select_option('curated')
    out=Path('C:/Users/marjun/.codex/visualizations/2026/09/26/01a0de87-b674-7683-b13e-036d953cc2de')
    for w,h in [(1440,1000),(768,1024),(390,844)]:
     await page.set_viewport_size({'width':w,'height':h});await page.screenshot(path=str(out/f'nocturne-{w}.png'),full_page=True)
     self.assertFalse(await page.evaluate('document.documentElement.scrollWidth>innerWidth'))
    await page.locator('#heroDetails').click();await page.locator('#detailPlay').click();await page.screenshot(path=str(out/'nocturne-player-mobile.png'))
    self.assertEqual(errors,[]);await browser.close()

if __name__=='__main__':unittest.main()
