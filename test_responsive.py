import ast
import copy
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.async_api import async_playwright
from analyzer import infer_responsive_behavior
from builder import build_site
from renderer import VIEWPORTS


def snapshots(states):
    return {name: {"design": {"viewport": VIEWPORTS[name], "elements": [],
            "visibilityElements": [{"domPath": path, "visible": visible}
                                   for path, visible in values.items()]}}
            for name, values in zip(VIEWPORTS, states)}


class VisibilityTests(unittest.TestCase):
    def test_transition_directions_and_sampled_ranges(self):
        data = snapshots([{"desktop": True, "mobile": False, "tablet": False},
                          {"desktop": False, "mobile": False, "tablet": True},
                          {"desktop": False, "mobile": True, "tablet": False}])
        changes = {item["path"]: item["transitions"]
                   for item in infer_responsive_behavior(data)["visibility_changes"]}
        self.assertEqual(changes["desktop"], [{"from_stage": "desktop",
            "breakpoint_stage": "tablet", "change": "hidden",
            "breakpoint_lower_bound": 768, "breakpoint_upper_bound": 1440}])
        self.assertEqual(changes["mobile"], [{"from_stage": "tablet",
            "breakpoint_stage": "mobile", "change": "shown",
            "breakpoint_lower_bound": 390, "breakpoint_upper_bound": 768}])
        self.assertEqual([t["change"] for t in changes["tablet"]], ["shown", "hidden"])
        self.assertEqual([t["breakpoint_stage"] for t in changes["tablet"]], ["tablet", "mobile"])

    def test_unknown_states_and_invalid_widths_do_not_invent_ranges(self):
        data = snapshots([{"a": True}, {}, {"a": False}])
        self.assertEqual(infer_responsive_behavior(data)["visibility_changes"][0]["transitions"], [])
        for width in (None, 0, -1, True, "768", 1440, 1500):
            with self.subTest(width=width):
                data = snapshots([{"a": True}, {"a": False}, {"a": False}])
                data["tablet"]["design"]["viewport"] = {"width": width}
                self.assertEqual(infer_responsive_behavior(data)["visibility_changes"][0]["transitions"], [])

    def test_tablet_only_and_missing_samples(self):
        data = snapshots([{"a": True, "missing": True}, {"a": False}, {"a": True}])
        changes = infer_responsive_behavior(data)["visibility_changes"]
        self.assertEqual(len(changes), 1)
        self.assertEqual([changes[0][f"{name}_visible"] for name in VIEWPORTS],
                         [True, False, True])

    def test_stable_order_cap_and_legacy_samples(self):
        data = snapshots([{str(i): True for i in range(40)}, {},
                          {str(i): False for i in reversed(range(40))}])
        for snapshot in data.values():
            design = snapshot["design"]
            design["elements"] = design.pop("visibilityElements")
        changes = infer_responsive_behavior(data)["visibility_changes"]
        self.assertEqual(len(changes), 30)
        self.assertEqual([c["path"] for c in changes], sorted(str(i) for i in range(40))[:30])
        self.assertIsNone(changes[0]["tablet_visible"])


class BrowserTests(unittest.IsolatedAsyncioTestCase):
    async def test_capture_and_layout_regression(self):
        tree = ast.parse(Path("renderer.py").read_text())
        script = next(node.args[0].value for node in ast.walk(tree)
                      if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                      and node.func.attr == "evaluate")
        html = '''<style>
          .row {display:flex;gap:100px}.row div{width:120px;height:100px}
          #hidden {display:none} #transparent {opacity:0}
          #concealed {visibility:hidden} #override {visibility:visible}
          #offscreen {position:absolute;top:5000px}
          #mobile-menu,#tablet-controls {display:none}
          @media(max-width:900px){#desktop-nav{display:none}}
          @media(max-width:600px){#mobile-menu{display:block}}
          @media(min-width:601px) and (max-width:900px){#tablet-controls{display:block}}
          @media(max-width:600px){.row{flex-direction:column} #desktop{display:none}}
          @media(min-width:601px) and (max-width:900px){#tablet{display:none}}
        </style><div class="row"><div>A</div><div>B</div></div>
        <div id="hidden"><span id="hidden-child">Hidden</span></div>
        <div id="transparent"><span id="transparent-child">Transparent</span></div>
        <div id="concealed"><span id="override">Visible override</span></div>
        <div id="offscreen">Below fold</div><input id="desktop"><img id="tablet">
        <nav id="desktop-nav">Desktop navigation</nav>
        <button id="mobile-menu">Mobile menu</button><button id="tablet-controls">Tablet controls</button>
        ''' + '<div>Filler</div>' * 130 + '<button id="late">Late</button>'
        data = {}
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            try:
                page = await browser.new_page()
                for name, viewport in VIEWPORTS.items():
                    await page.set_viewport_size(viewport)
                    await page.set_content(html)
                    data[name] = await page.evaluate(script)
            finally:
                await browser.close()
        values = {e["domPath"]: e["visible"] for e in data["desktop"]["design"]["visibilityElements"]}
        for path in ("div#hidden", "span#hidden-child", "span#transparent-child", "div#concealed"):
            self.assertFalse(values[path], path)
        for path in ("span#override", "div#offscreen", "button#late"):
            self.assertTrue(values[path], path)
        result = infer_responsive_behavior(data)
        changes = {c["path"]: c for c in result["visibility_changes"]}
        self.assertEqual(set(changes), {"input#desktop", "img#tablet", "nav#desktop-nav",
                                       "button#mobile-menu", "button#tablet-controls"})
        for path, expected in {
            "nav#desktop-nav": [("hidden", "tablet", 768, 1440)],
            "button#mobile-menu": [("shown", "mobile", 390, 768)],
            "button#tablet-controls": [("shown", "tablet", 768, 1440), ("hidden", "mobile", 390, 768)],
        }.items():
            self.assertEqual([(t["change"], t["breakpoint_stage"], t["breakpoint_lower_bound"],
                               t["breakpoint_upper_bound"]) for t in changes[path]["transitions"]], expected)
        legacy = copy.deepcopy(data)
        for snapshot in legacy.values():
            del snapshot["design"]["visibilityElements"]
        old = infer_responsive_behavior(legacy)
        for key in result.keys() - {"visibility_changes"}:
            self.assertEqual(result[key], old[key])
        group = result["row_to_column_groups"][0]
        self.assertEqual((group["breakpoint_lower_bound"], group["breakpoint_upper_bound"]), (390, 768))
        with TemporaryDirectory() as folder:
            build_site({"blueprint": {"responsive_behavior": result}}, project_dir=folder)
            self.assertIn("@media(max-width:579px)", Path(folder, "style.css").read_text())


if __name__ == "__main__":
    unittest.main()
