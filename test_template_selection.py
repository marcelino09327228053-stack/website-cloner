import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from fastapi.testclient import TestClient
import main
import project_manager as pm
from builder import build_site
from template_selection import reference_template

class TemplateSelectionTests(unittest.TestCase):
 def test_hosts_and_lookalikes(self):
  for url,expected in [('https://www.canva.com/en_ph/','design_studio'),('canva.com','design_studio'),('https://WWW.YOUTUBE.COM/watch?v=abc','video_platform'),('https://m.youtube.com/','video_platform'),('https://youtu.be/abc','video_platform')]:
   self.assertEqual(reference_template(url),expected)
  for url in ['https://notcanva.com','https://canva.com.evil.test','https://example.com/?url=youtube.com','https://youtube.com@evil.test','ftp://canva.com','https://canva.com:bad','https://photopea.com']:
   self.assertIsNone(reference_template(url))
 def test_analyze_build_routes(self):
  with TemporaryDirectory() as folder,patch.object(main,'analyze_url') as analyzer,patch.object(pm,'REGISTRY',Path(folder)/'registry.json'):
   client=TestClient(main.app)
   for host,kind,marker in [('canva.com','design_studio','id="editor"'),('youtube.com','video_platform','video-grid')]:
    response=client.post('/api/analyze',json={'url':'https://'+host})
    self.assertEqual(response.status_code,200);analysis=response.json()
    self.assertEqual(analysis['blueprint']['layout_kind'],kind)
    target=Path(folder)/kind
    built=client.post('/api/build',json={'analysis':analysis,'project_path':str(target),'project_name':'My Project'})
    self.assertEqual(built.status_code,200)
    preview=client.get(built.json()['preview_url'])
    self.assertEqual(preview.status_code,200);self.assertIn(marker,preview.text)
   analyzer.assert_not_called()
 def test_other_sites_still_analyze(self):
  with patch.object(main,'analyze_url',return_value={'site':{'title':'Reference'}}) as analyze:
   self.assertEqual(TestClient(main.app).post('/api/analyze',json={'url':'https://example.com'}).status_code,200)
   analyze.assert_awaited_once_with('https://example.com')
 def test_direct_builder_and_explicit_override(self):
  with TemporaryDirectory() as folder:
   build_site({'requested_url':'https://canva.com'},folder,'Demo')
   self.assertIn('id="editor"',(Path(folder)/'index.html').read_text(encoding="utf-8"))
   build_site({'requested_url':'https://canva.com','blueprint':{'layout_kind':'video_platform'}},folder,'Frame')
   self.assertIn('video-grid',(Path(folder)/'index.html').read_text(encoding="utf-8"))

if __name__=='__main__':unittest.main()

