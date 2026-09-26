import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient
from playwright.async_api import async_playwright
import main
import project_manager


class ProjectFlowTests(unittest.IsolatedAsyncioTestCase):
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
                        preview = await page.locator('#preview').get_attribute('href')
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
