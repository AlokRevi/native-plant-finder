"""Run from project root with: python -m unittest discover -s tests -v"""
import json
import threading
import unittest
import xml.etree.ElementTree as ET
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import app


class CatalogueTests(unittest.TestCase):
    def test_data_and_illustration_files(self):
        for image in app.ART.values():
            ET.parse(app.ROOT / "assets" / "illustrations" / image)

    def test_full_ontario_list(self):
        result = app.filter_catalogue({"province": "Ontario"})
        self.assertTrue(result["supported"])
        self.assertGreater(result["count"], 1000)
        self.assertEqual(result["total"], result["count"])
        self.assertEqual(50, len(result["plants"]))
        self.assertEqual(50, result["next_offset"])

    def test_outside_pilot_is_explicit(self):
        result = app.filter_catalogue({"province": "British Columbia"})
        self.assertFalse(result["supported"])
        self.assertEqual(0, result["count"])

    def test_all_selected_criteria_must_match(self):
        result = app.filter_catalogue({"province": "Ontario", "sun": "full", "soil": "loamy", "moisture": "average"})
        self.assertGreater(result["count"],0)
        for p in result["plants"]:
            self.assertIn("full",p["sun"])
            self.assertIn("loamy",p["soil"])
            self.assertIn("average",p["moisture"])

    def test_conifer(self):
        result = app.filter_catalogue({"province": "Ontario", "flowers": "nonflowering"})
        self.assertGreater(result["count"],0)
        self.assertTrue(all(not p["moisture"] or isinstance(p["moisture"],list) for p in result["plants"]))

    def test_no_irrigation_returns_only_drought_tolerant(self):
        result = app.filter_catalogue({"province": "Ontario", "irrigation": "no"})
        self.assertGreater(result["count"],0)
        self.assertTrue(all(p["drought_tolerant"] for p in result["plants"]))

    def test_missing_condition_does_not_count_as_a_match(self):
        self.assertFalse(app.db.matches({"conditions":[],"lifecycle":None},{"sun":"full"}))
        self.assertFalse(app.db.matches({"conditions":[],"lifecycle":None},{"lifecycle":"annual"}))

    def test_pagination_has_no_overlap(self):
        first=app.filter_catalogue({"province":"Ontario","limit":"10"})
        second=app.filter_catalogue({"province":"Ontario","limit":"10","offset":"10"})
        self.assertFalse({p["id"] for p in first["plants"]}&{p["id"] for p in second["plants"]})

    def test_coordinates_and_page_values_are_validated(self):
        for values in [{"latitude":"nan","longitude":"-79"},{"latitude":"43"},{"offset":"-1"},{"limit":"101"}]:
            with self.assertRaises(ValueError):app.filter_catalogue({"province":"Ontario",**values})

    def test_spatial_scope_and_provincial_fallback(self):
        toronto=app.filter_catalogue({"province":"Ontario","latitude":"43.65","longitude":"-79.38"})
        oakville=app.filter_catalogue({"province":"Ontario","latitude":"43.4489","longitude":"-79.6974"})
        self.assertTrue(toronto["local_native_status"])
        self.assertFalse(oakville["local_native_status"])
        self.assertIn("local status unverified",oakville["message"])

    def test_negative_local_evidence_blocks_provincial_fallback(self):
        row={"evidence":[{"region_id":"local","match":"verified","native":"introduced","occurrence":"present","kind":"native_classification","review":"accepted_source_assertion"},{"region_id":"ontario","match":"verified","native":"native","occurrence":"present","kind":"native_classification","review":"accepted_source_assertion"}]}
        self.assertEqual([],app.db.select_evidence([row],{"local"}))

    def test_invalid_filter(self):
        with self.assertRaisesRegex(ValueError, "Invalid choice"):
            app.filter_catalogue({"province": "Ontario", "sun": "purple"})
        with self.assertRaisesRegex(ValueError, "location"):
            app.filter_catalogue({})


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def read(self, path):
        with urlopen(self.base + path if isinstance(path, str) else path, timeout=4) as response:
            return response.status, response.headers.get("Content-Type"), response.read()

    def test_html_and_scripts(self):
        code, mime, data = self.read("/")
        self.assertEqual(200, code)
        self.assertIn("text/html", mime)
        self.assertIn(b"Native Plant Finder", data)
        code, mime, data = self.read("/assets/app.js")
        self.assertEqual(200, code)
        self.assertIn("javascript", mime)
        self.assertIn(b"loadPlants", data)

    def test_demo_api(self):
        code, mime, data = self.read("/api/demo-garden")
        payload = json.loads(data)
        self.assertEqual(200, code)
        self.assertEqual("Ontario", payload["province"])

    def test_filter_api(self):
        _, _, data = self.read("/api/plants?province=Ontario&form=tree")
        payload = json.loads(data)
        self.assertTrue(all(p["form"] == "tree" for p in payload["plants"]))
        self.assertGreater(payload["count"], 0)

    def test_database_outage_returns_503_without_credentials(self):
        with patch.object(app.db,"catalogue",side_effect=app.db.DatabaseUnavailable("Plant database unavailable")):
            with self.assertRaises(HTTPError) as context:self.read("/api/plants?province=Ontario")
            self.assertEqual(503,context.exception.code)
            self.assertEqual({"error":"Plant database unavailable"},json.load(context.exception))

    def test_geocoder_isolated_from_external_network(self):
        fake = {"latitude": 43.5, "longitude": -79.7, "province": "Ontario", "display_name": "Mock garden"}
        with patch.object(app, "geocode_address", return_value=fake) as mock:
            _, _, data = self.read(Request(self.base + "/api/geocode", data=json.dumps({"q": "Oakville, Ontario"}).encode(), headers={"Content-Type": "application/json"}))
            self.assertEqual(fake, json.loads(data))
            mock.assert_called_once_with("Oakville, Ontario")

    def test_rejects_bad_parameters_and_path(self):
        for path, expected in [
            ("/api/plants?province=Ontario&sun=unknown", 400),
            ("/api/geocode?q=a", 405),
            ("/assets/no-such-file.js", 404),
            ("/assets/../app.py", 404),
        ]:
            with self.assertRaises(HTTPError) as context:
                self.read(path)
            self.assertEqual(expected, context.exception.code)


if __name__ == "__main__":
    unittest.main()
