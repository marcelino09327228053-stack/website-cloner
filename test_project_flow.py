import json
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient
from playwright.async_api import async_playwright
import main
import project_manager


class ProjectFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_history_scrolls_inside_single_screen_and_searches(self):
        client=TestClient(main.app)
        entries=[{'id':str(i),'display_name':f'Project {i}','project_path':f'I:/Samples/Project {i}',
                  'available':True,'updated_at':'','source_url':'','preview_url':None} for i in range(12)]
        async with async_playwright() as pw:
            browser=await pw.chromium.launch()
            try:
                page=await browser.new_page()
                async def serve(route):
                    if route.request.url.endswith('/api/projects'):
                        await route.fulfill(json={'projects':entries})
                    else:
                        response=client.get(route.request.url)
                        await route.fulfill(status=response.status_code,headers=dict(response.headers),body=response.content)
                await page.route('http://app.test/**',serve)
                await page.goto('http://app.test/')
                await page.locator('.history-row').last.wait_for()
                for width,height in ((1440,900),(1366,768),(390,844)):
                    await page.set_viewport_size({'width':width,'height':height})
                    self.assertFalse(await page.evaluate('document.documentElement.scrollHeight>innerHeight'))
                    self.assertFalse(await page.evaluate('document.documentElement.scrollWidth>innerWidth'))
                    self.assertTrue(await page.locator('#projectHistory').evaluate('(e)=>e.scrollHeight>e.clientHeight'))
                await page.locator('#historySearch').fill('Project 11')
                self.assertEqual(await page.locator('.history-row:visible').count(),1)
                await page.locator('#historySearch').fill('no such project')
                self.assertEqual(await page.locator('.history-row:visible').count(),0)
                self.assertIn('no matches',await page.locator('#historyStatus').inner_text())
            finally:
                await browser.close()

    async def test_history_discovery_preview_and_reveal(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);old=root/'generated'/'Old Project';old.mkdir(parents=True)
            (old/'project.json').write_text(json.dumps({'display_name':'Old Project','source_url':'https://example.com','updated_at':'2026-10-13T10:00:00'}))
            (old/'index.html').write_text('<h1>Saved site</h1>')
            with patch.object(project_manager,'BASE',root), patch.object(project_manager,'REGISTRY',root/'registry.json'):
                project_manager.register_project(root/'missing','Missing Project')
                client=TestClient(main.app)
                entries=client.get('/api/projects').json()['projects']
                self.assertEqual(len(entries),2)
                found=next(item for item in entries if item['display_name']=='Old Project')
                self.assertEqual(found['source_url'],'https://example.com')
                self.assertEqual(client.get(found['preview_url']).status_code,200)
                with patch.object(main.os,'startfile') as reveal:
                    self.assertEqual(client.post('/api/projects/'+found['id']+'/reveal').status_code,200)
                    reveal.assert_called_once_with(str(old.resolve()))
                missing=next(item for item in entries if not item['available'])
                self.assertIsNone(missing['preview_url'])
                self.assertEqual(client.post('/api/projects/'+missing['id']+'/reveal').status_code,404)
                self.assertEqual(client.post('/api/projects/unknown/reveal').status_code,404)

    async def test_html_always_requests_current_assets(self):
        client = TestClient(main.app)
        response = client.get('/')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        assets = re.findall(r'/static/[^" ]+\?v=[a-f0-9]+', response.text)
        self.assertEqual(len(assets), 2)
        for asset in assets:
            fetched = client.get(asset)
            self.assertEqual(fetched.status_code, 200)
            self.assertEqual(fetched.headers['cache-control'], 'no-store')
        self.assertIn('openFolder', client.get(next(a for a in assets if 'app.js' in a)).text)

    async def test_actual_picker_processing_preserves_folder_and_handles_bad_metadata(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'project.json').write_text('not valid JSON')
            with patch.object(project_manager, 'REGISTRY', root/'registry.json'), \
                 patch.object(project_manager.subprocess, 'run') as run:
                run.return_value.stdout = json.dumps(folder)
                selected = project_manager.choose_project_folder()
                self.assertEqual(selected['project_path'], str(root.resolve()))
                self.assertEqual(selected['project_name'], root.name)
                self.assertEqual((root/'project.json').read_text(), 'not valid JSON')

    async def test_folder_build_and_preview(self):
        with TemporaryDirectory() as folder:
            project = Path(folder, 'My Project'); project.mkdir()
            selected = {'project_name': 'My Project', 'project_path': str(project)}
            async def analyze(url):
                return {'site': {'title': 'Reference'}, 'blueprint': {'rendered_browser': True}}
            with patch.object(project_manager, 'REGISTRY', Path(folder, 'registry.json')), \
                 patch.object(main, 'choose_project_folder', return_value=selected), \
                 patch.object(main, 'analyze_url', side_effect=analyze):
                client = TestClient(main.app)
                async with async_playwright() as pw:
                    browser = await pw.chromium.launch()
                    try:
                        page = await browser.new_page()
                        errors = []
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        async def serve(route):
                            request = route.request
                            response = client.request(request.method, request.url,
                                                      content=request.post_data, headers=request.headers)
                            await route.fulfill(status=response.status_code,
                                                headers=dict(response.headers), body=response.content)
                        await page.route('http://app.test/**', serve)
                        await page.goto('http://app.test/')
                        self.assertTrue(await page.locator('#build').is_disabled())
                        await page.locator('#openFolder').click()
                        await page.wait_for_function("!document.getElementById('build').disabled")
                        self.assertEqual(await page.locator('#projectTitle').inner_text(), 'My Project')
                        await page.locator('#projectName').fill('Client Website')
                        await page.locator('#url').fill('https://example.com')
                        await page.locator('#build').click()
                        await page.wait_for_function("!document.getElementById('build').disabled")
                        self.assertTrue(await page.locator('#preview').is_visible(), await page.locator('#status').inner_text())
                        self.assertEqual(json.loads((project/'project.json').read_text())['display_name'], 'Client Website')
                        self.assertTrue((project/'index.html').exists())
                        await page.reload()
                        row=page.locator('.history-row').filter(has_text='Client Website')
                        await row.get_by_role('button',name='Open Project',exact=True).click()
                        self.assertEqual(await page.locator('#projectName').input_value(),'Client Website')
                        self.assertEqual(await page.locator('#folderPath').inner_text(),str(project))
                        self.assertFalse(await page.locator('#build').is_disabled())
                        preview = await row.get_by_role('link',name='Preview',exact=True).get_attribute('href')
                        await page.goto('http://app.test'+preview)
                        self.assertEqual(await page.locator('.topbar').evaluate('(e)=>getComputedStyle(e).position'), 'sticky')
                        await page.set_viewport_size({'width':390,'height':844})
                        await page.locator('.navigation-toggle').click()
                        self.assertTrue(await page.locator('#generated-navigation').is_visible())
                        self.assertEqual(errors, [])
                        self.assertEqual(client.get(preview.replace('index.html','analysis.json')).status_code,404)
                        self.assertEqual(client.get('/api/preview/unknown/style.css').status_code,404)
                    finally:
                        await browser.close()

    async def test_cancel_and_picker_error(self):
        client = TestClient(main.app)
        with patch.object(main, 'choose_project_folder', return_value=None):
            self.assertEqual(client.post('/api/projects/open-folder').json(), {'project': None})
        with patch.object(main, 'choose_project_folder', side_effect=RuntimeError('Unavailable')):
            self.assertEqual(client.post('/api/projects/open-folder').status_code, 400)


if __name__ == '__main__':
    unittest.main()
