import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from playwright.async_api import async_playwright
from builder import build_site
from media_layout import detect_media_layout, media_breakpoints, render_media_platform


class MediaDetectionTests(unittest.TestCase):
    def test_positive_and_negative_detection(self):
        self.assertFalse(detect_media_layout({'resources':{'images':[{}]*40},'blueprint':{'section_order':['gallery']}}))
        self.assertFalse(detect_media_layout({'blueprint':{'media_evidence':{'video_count':1}}}))
        self.assertTrue(detect_media_layout({'blueprint':{'media_evidence':{'video_count':4}}}))
        self.assertTrue(detect_media_layout({'navigation':[{'href':f'https://example.com/watch?v={i}'} for i in range(5)]}))
        self.assertFalse(detect_media_layout({'navigation':[{'href':'https://example.com/watch?v=1'}]*8}))
        self.assertTrue(detect_media_layout({'blueprint':{'media_evidence':{'video_count':1}},'navigation':[{'text':s} for s in ('Subscriptions','History','Music','Gaming')]}))

    def test_inferred_ranges_and_escaping(self):
        analysis={'blueprint':{'responsive_behavior':{'row_to_column_groups':[{'breakpoint_stage':'mobile','breakpoint_lower_bound':390,'breakpoint_upper_bound':768}]},'media_items':[{'title':'</script><script>alert(1)</script>','thumbnail':'javascript:alert(1)'}]}}
        self.assertEqual(media_breakpoints(analysis),(579,1100))
        html,css,js=render_media_platform(analysis,'<unsafe>')
        self.assertNotIn('</script><script>alert',html)
        self.assertIn('&lt;unsafe&gt;',html)
        self.assertIn('@media(max-width:579px)',css)
        self.assertNotIn('javascript:alert',html)


class MediaBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def test_generated_feed_interactions_and_responsive_layout(self):
        with TemporaryDirectory() as folder:
            analysis={'blueprint':{'layout_kind':'video_platform','responsive_behavior':{'row_to_column_groups':[{'breakpoint_stage':'mobile','breakpoint_lower_bound':390,'breakpoint_upper_bound':768}]}}}
            build_site(analysis,project_dir=folder,project_name='Frame')
            async with async_playwright() as pw:
                browser=await pw.chromium.launch()
                try:
                    page=await browser.new_page()
                    errors=[]
                    page.on('pageerror',lambda error:errors.append(str(error)))
                    await page.route('https://images.unsplash.com/**',lambda route:route.fulfill(content_type='image/svg+xml',body='<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450"><rect width="800" height="450" fill="#284554"/></svg>'))
                    await page.goto(Path(folder,'index.html').as_uri())
                    self.assertEqual(await page.locator('.video-card').count(),9)
                    for width,columns in ((1440,3),(1000,2),(768,2),(580,2),(579,1),(390,1),(320,1)):
                        await page.set_viewport_size({'width':width,'height':900})
                        self.assertEqual(await page.locator('.video-grid').evaluate('(e)=>getComputedStyle(e).gridTemplateColumns.split(" ").length'),columns)
                        self.assertFalse(await page.evaluate('document.documentElement.scrollWidth>innerWidth'),width)
                    await page.locator('.menu-toggle').click()
                    self.assertEqual(await page.locator('.menu-toggle').get_attribute('aria-expanded'),'true')
                    await page.locator('[data-view="saved"]').click()
                    self.assertTrue(await page.locator('#empty').is_visible())
                    await page.locator('#resetFilters').click()
                    await page.locator('.save').first.click()
                    self.assertEqual(await page.locator('#savedCount').inner_text(),'1')
                    await page.locator('#search').fill('workspace')
                    self.assertEqual(await page.locator('.video-card').count(),1)
                    await page.locator('#search').fill('')
                    await page.locator('.chip',has_text='Music').click()
                    self.assertEqual(await page.locator('.video-card').count(),1)
                    await page.locator('.thumbnail').click()
                    self.assertTrue(await page.locator('#details').is_visible())
                    await page.keyboard.press('Escape')
                    self.assertFalse(await page.locator('#details').is_visible())
                    await page.locator('.chip',has_text='All').click()
                    await page.locator('#sort').select_option('popular')
                    self.assertIn('scenic route',await page.locator('.card-title').first.inner_text())
                    await page.reload()
                    self.assertEqual(await page.locator('#savedCount').inner_text(),'1')
                    self.assertEqual(errors,[])
                finally:
                    await browser.close()


if __name__=='__main__':unittest.main()
