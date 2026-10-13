import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from fastapi.testclient import TestClient
from playwright.async_api import async_playwright
import main
import project_manager as pm

class HistoryActions(unittest.IsolatedAsyncioTestCase):
    async def test_real_endpoints_from_ui(self):
        with TemporaryDirectory() as temporary:
            root=Path(temporary); source=root/'source'; source.mkdir()
            project=root/'Sample'; project.mkdir()
            (project/'index.html').write_text('<h1>Sample</h1>')
            (project/'project.json').write_text(json.dumps({'project_path':str(project),'display_name':'Sample','main_file':'index.html'}))
            with patch.object(pm,'BASE',source),patch.object(pm,'REGISTRY',source/'registry.json'),patch.object(main.os,'startfile') as reveal:
                pm.register_project(project)
                client=TestClient(main.app)
                async with async_playwright() as pw:
                    browser=await pw.chromium.launch()
                    page=await browser.new_page(); errors=[]
                    page.on('pageerror',lambda e:errors.append(str(e)))
                    async def serve(route):
                        r=route.request
                        response=client.request(r.method,r.url,content=r.post_data,headers=r.headers)
                        await route.fulfill(status=response.status_code,headers=dict(response.headers),body=response.content)
                    await page.route('http://app.test/**',serve)
                    await page.goto('http://app.test/')
                    await page.get_by_role('button',name='Open Project').click()
                    await page.get_by_role('button',name='Open Location').click()
                    reveal.assert_called_once_with(str(project))
                    original=await page.get_by_role('link',name='Preview').get_attribute('href')
                    await page.get_by_role('button',name='Rename',exact=True).click()
                    await page.locator('#renameName').fill('CON')
                    await page.locator('#confirmAction').click()
                    await page.wait_for_function("document.querySelector('#dialogStatus').textContent.includes('reserved')")
                    await page.locator('#renameName').fill('Renamed')
                    await page.locator('#confirmAction').click()
                    await page.wait_for_function("!document.querySelector('#projectDialog').open")
                    self.assertTrue((root/'Renamed'/'index.html').exists())
                    self.assertIn('Renamed',await page.locator('#folderPath').inner_text())
                    self.assertEqual(await page.get_by_role('link',name='Preview').get_attribute('href'),original)
                    self.assertEqual(client.get(original).status_code,200)
                    await page.get_by_role('button',name='Delete',exact=True).click()
                    self.assertIn(str(root/'Renamed'),await page.locator('#dialogPath').inner_text())
                    await page.locator('#cancelAction').click()
                    self.assertTrue((root/'Renamed').exists())
                    await page.get_by_role('button',name='Delete',exact=True).click()
                    await page.get_by_label('Remove from history only',exact=True).check()
                    await page.locator('#confirmAction').click()
                    await page.wait_for_function("!document.querySelector('#projectDialog').open")
                    self.assertTrue((root/'Renamed').exists())
                    self.assertTrue(await page.locator('#build').is_disabled())
                    await page.locator('#refreshHistory').click()
                    await page.wait_for_function("document.querySelector('#historyStatus').textContent==='No saved projects yet.'")
                    pm.register_project(root/'Renamed')
                    await page.locator('#refreshHistory').click()
                    await page.get_by_role('button',name='Delete',exact=True).click()
                    await page.get_by_label('Delete project folder and files',exact=True).check()
                    await page.locator('#confirmAction').click()
                    await page.wait_for_function("!document.querySelector('#projectDialog').open")
                    self.assertFalse((root/'Renamed').exists())
                    self.assertEqual(errors,[])
                    await browser.close()

if __name__=='__main__':unittest.main()
