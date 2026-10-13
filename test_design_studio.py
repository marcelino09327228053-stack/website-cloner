import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from fastapi.testclient import TestClient
from playwright.async_api import async_playwright
import main
import project_manager as pm
from builder import build_site

class DesignStudioTests(unittest.IsolatedAsyncioTestCase):
 async def test_builder_editor_and_responsive(self):
  with TemporaryDirectory() as folder:
   root=Path(folder);project=root/'Design Studio'
   build_site({'blueprint':{'layout_kind':'design_studio'}},str(project),'Design Studio')
   identity=json.loads((project/'project.json').read_text())['project_id']
   with patch.object(pm,'BASE',root/'source'),patch.object(pm,'REGISTRY',root/'registry.json'):
    pm.register_project(project,'Design Studio');client=TestClient(main.app)
    url=client.get('/api/projects').json()['projects'][0]['preview_url']
    async with async_playwright() as pw:
     browser=await pw.chromium.launch();page=await browser.new_page(viewport={'width':1440,'height':1000});errors=[]
     page.on('pageerror',lambda e:errors.append(str(e)))
     async def serve(route):
      r=route.request;response=client.request(r.method,r.url,content=r.post_data,headers=r.headers)
      await route.fulfill(status=response.status_code,headers=dict(response.headers),body=response.content)
     await page.route('http://app.test/**',serve);await page.goto('http://app.test'+url)
     self.assertEqual(await page.locator('#templateGrid .design-card').count(),8)
     await page.locator('#chips').get_by_role('button',name='Poster',exact=True).click();self.assertEqual(await page.locator('#templateGrid .design-card').count(),2)
     await page.locator('#chips').get_by_role('button',name='For you',exact=True).click()
     await page.locator('#search').fill('bloom');self.assertEqual(await page.locator('#templateGrid .design-card').count(),1)
     await page.get_by_role('button',name='Star Ideas in bloom',exact=True).click();await page.locator('[data-view=starred]').click()
     self.assertEqual(await page.locator('#templateGrid .design-card').count(),1)
     await page.get_by_role('button',name='Preview Ideas in bloom',exact=True).click();await page.locator('#useTemplate').click()
     await page.locator('#designName').fill('My creative direction');await page.locator('#textValue').fill('Made with imagination')
     await page.locator('#fontSize').fill('42');await page.locator('#textColor').fill('#123456');await page.locator('#backgroundColor').fill('#abcdef')
     await page.locator('#addText').click();await page.locator('#textValue').fill('Keep creating')
     target=page.locator('#canvas .selected');box=await target.bounding_box();await page.mouse.move(box['x']+10,box['y']+10);await page.mouse.down();await page.mouse.move(box['x']+60,box['y']+30);await page.mouse.up()
     position=await target.evaluate('(e)=>e.style.left');self.assertNotEqual(position,'10%')
     await page.locator('#addText').click();await page.locator('#deleteText').click();self.assertEqual(await page.locator('#canvas .design-text').count(),4)
     await page.locator('#saveDesign').click();await page.locator('#closeEditor').click();await page.reload()
     await page.locator('[data-view=projects]').click();await page.get_by_role('button',name='Open My creative direction').click()
     self.assertEqual(await page.locator('#backgroundColor').input_value(),'#abcdef');self.assertIn('Keep creating',await page.locator('#canvas').inner_text())
     await page.locator('#closeEditor').click()
     renamed=client.post('/api/projects/'+identity+'/rename',json={'name':'Renamed Studio'});self.assertEqual(renamed.status_code,200)
     await page.reload();await page.locator('[data-view=projects]').click();self.assertEqual(await page.locator('#templateGrid .design-card').count(),1)
     await page.locator('[data-view=home]').click()
     out=Path('C:/Users/marjun/.codex/visualizations/2026/09/26/01a0de87-b674-7683-b13e-036d953cc2de')
     for w,h in [(1440,1000),(768,1024),(390,844)]:
      await page.set_viewport_size({'width':w,'height':h});await page.wait_for_timeout(180)
      self.assertFalse(await page.evaluate('document.documentElement.scrollWidth>innerWidth'))
      await page.screenshot(path=str(out/f'design-studio-{w}.png'),full_page=True)
     await page.locator('.small-create').click();await page.locator('#formatChoices').get_by_role('button',name='Social').click();await page.locator('#addText').click();await page.locator('#saveDesign').click()
     await page.screenshot(path=str(out/'design-editor-mobile.png'))
     self.assertEqual(errors,[])
     await browser.close()
   build_site({'blueprint':{'layout_kind':'design_studio'}},str(root/'Renamed Studio'),'Design Studio')
   self.assertEqual(json.loads((root/'Renamed Studio'/'project.json').read_text())['project_id'],identity)

if __name__=='__main__':unittest.main()
