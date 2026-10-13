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

class SocialTests(unittest.IsolatedAsyncioTestCase):
 async def test_social_build_and_interactions(self):
  self.assertEqual(reference_template('https://m.facebook.com/'),'social_feed')
  self.assertIsNone(reference_template('https://facebook.com.fake.test'))
  with TemporaryDirectory() as folder,patch.object(pm,'BASE',Path(folder)/'source'),patch.object(pm,'REGISTRY',Path(folder)/'registry.json'):
   client=TestClient(main.app);analysis=client.post('/api/analyze',json={'url':'https://www.facebook.com/'}).json()
   self.assertEqual(analysis['blueprint']['layout_kind'],'social_feed')
   target=Path(folder)/'Gather';response=client.post('/api/build',json={'analysis':analysis,'project_path':str(target),'project_name':'Gather'})
   self.assertEqual(response.status_code,200);url=response.json()['preview_url']
   async with async_playwright() as pw:
    browser=await pw.chromium.launch();page=await browser.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    async def serve(route):
     r=route.request;res=client.request(r.method,r.url,content=r.post_data,headers=r.headers)
     await route.fulfill(status=res.status_code,headers=dict(res.headers),body=res.content)
    await page.route('http://app.test/**',serve);await page.goto('http://app.test'+url)
    self.assertEqual(await page.locator('.post').count(),4)
    await page.get_by_role('button',name='View story by Leo Santos').click();await page.locator('#nextStory').click();self.assertIn('room',await page.locator('#storyTitle').inner_text());await page.get_by_role('button',name='Close story').click()
    first=page.locator('.post').first;await first.locator('.save-button').click();await first.get_by_role('button',name='Appreciate',exact=False).click()
    await first.get_by_role('button',name='Comment',exact=False).click();await first.get_by_label('Write a comment').fill('Great view!');await first.locator('.comment-form button').click()
    await page.get_by_role('button',name='Follow Leo Santos',exact=True).click();await page.locator('nav [data-view=following]').click();self.assertEqual(await page.locator('.post').count(),1)
    await page.locator('nav [data-view=all]').click();await page.locator('#search').fill('curious');self.assertEqual(await page.locator('.post').count(),1);await page.locator('#search').fill('')
    await page.locator('#categories').get_by_role('button',name='Design',exact=True).click();self.assertEqual(await page.locator('.post').count(),2)
    await page.locator('#newPost').click();await page.locator('#postText').fill('A new original thought.');await page.locator('#postArtwork').select_option('bloom');await page.locator('#submitPost').click()
    self.assertEqual(await page.locator('.post').count(),1);await page.get_by_role('button',name='Edit post',exact=True).click();await page.locator('#postText').fill('A revised original thought.');await page.locator('#submitPost').click()
    await page.reload();await page.locator('nav [data-view=mine]').click();self.assertIn('revised',await page.locator('.post-copy').inner_text())
    page.once('dialog',lambda d:d.dismiss());await page.get_by_role('button',name='Delete post',exact=True).click();self.assertEqual(await page.locator('.post').count(),1)
    page.once('dialog',lambda d:d.accept());await page.get_by_role('button',name='Delete post',exact=True).click();self.assertEqual(await page.locator('.post').count(),0)
    await page.locator('nav [data-view=saved]').click();self.assertEqual(await page.locator('.post').count(),1);await page.locator('.post').get_by_role('button',name='Comment').click();self.assertIn('Great view!',await page.locator('.comments').inner_text())
    identity=json.loads((target/'project.json').read_text(encoding='utf-8'))['project_id'];self.assertEqual(client.post('/api/projects/'+identity+'/rename',json={'name':'Gather Renamed'}).status_code,200)
    await page.reload();await page.locator('nav [data-view=saved]').click();self.assertEqual(await page.locator('.post').count(),1)
    await page.locator('nav [data-view=all]').click()
    out=Path('C:/Users/marjun/.codex/visualizations/2026/09/26/01a0de87-b674-7683-b13e-036d953cc2de')
    for w,h in [(1440,1000),(768,1024),(390,844)]:
     await page.set_viewport_size({'width':w,'height':h});await page.screenshot(path=str(out/f'gather-{w}.png'),full_page=True)
     self.assertFalse(await page.evaluate('document.documentElement.scrollWidth>innerWidth'))
    self.assertEqual(errors,[]);await browser.close()

if __name__=='__main__':unittest.main()
