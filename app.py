"""Native Plant Finder: Python web server backed by the central PostgreSQL/PostGIS database.

The browser uses Leaflet.js for map interactions. Python serves the page,
converts explicitly submitted addresses to coordinates, and filters plant data.
Run: python app.py
"""
from __future__ import annotations

import json
import hashlib
import sys
import mimetypes
import math
import plant_database as db
import os
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from security_limits import BoundedHTTPServer, TTLCache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
ART = json.loads((ROOT / "data" / "plant-art.json").read_text(encoding="utf-8"))
NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search"
# Configure the deployment identity through NATIVE_PLANT_USER_AGENT.
USER_AGENT = os.environ.get(
    "NATIVE_PLANT_USER_AGENT",
    "CODG136NativePlantFinder/1.0 (student educational demonstration; https://alokrevi.com/gis)",
)

# The public Nominatim server allows a maximum of 1 request/second per app.
# Rate limiting and caching are process-local; multiple workers need shared coordination.
_geocode_lock = threading.Lock()
_geocode_cache = TTLCache(max_entries=256, ttl=900)
_last_request = 0.0

FILTER_VALUES = {
    "sun": {"full", "partial", "shade"},
    "soil": {"sandy", "loamy", "clay"},
    "moisture": {"dry", "average", "moist"},
    "irrigation": {"yes", "no"},
    "form": {"herb", "shrub", "tree"},
    "flowers": {"flowering", "nonflowering"},
    "lifecycle": {"annual", "biennial", "perennial"},
}


def filter_catalogue(params: dict[str, str]) -> dict:
    """Return Ontario-native candidates matching all selected conditions."""
    province = params.get("province", "").strip().casefold()
    if not province:
        raise ValueError("Find your Canadian garden location first.")

    chosen = {}
    for field, allowed in FILTER_VALUES.items():
        value = params.get(field, "").strip().lower()
        if value and value not in allowed:
            raise ValueError(f"Invalid choice for {field}.")
        chosen[field] = value

    if province not in {"ontario", "on"}:
        return {"supported": False, "region": "Ontario", "total": 0, "count": 0, "plants": [], "message": "Plant recommendations are currently available for Ontario only."}
    latitude = longitude = None
    if params.get("latitude") or params.get("longitude"):
        try:
            latitude, longitude = float(params["latitude"]), float(params["longitude"])
            if not math.isfinite(latitude) or not math.isfinite(longitude) or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                raise ValueError()
        except (ValueError, KeyError):
            raise ValueError("Enter a valid latitude and longitude together.") from None
    try:
        offset = int(params.get("offset", "0"))
        limit = int(params.get("limit", "50"))
        if offset < 0 or not 1 <= limit <= 100:
            raise ValueError()
    except ValueError:
        raise ValueError("Invalid page size or offset.") from None
    regions, local_scopes = db.location_regions(latitude, longitude)
    candidates = db.select_evidence(db.catalogue(), local_scopes)
    matches = [(row, evidence) for row, evidence in candidates if db.matches(row, chosen)]
    cards = [db.card(row, evidence, bool(local_scopes)) for row, evidence in matches[offset:offset+limit]]
    for card in cards:
        card["image"] = ART.get(card["scientific_name"])
    scope_names = [r["region_name"] for r in regions if r["region_id"] in local_scopes]
    return {"supported": True, "region": " / ".join(scope_names) if local_scopes else "Ontario",
            "total": len(candidates), "count": len(matches), "plants": cards,
            "offset": offset, "next_offset": offset + len(cards) if offset + len(cards) < len(matches) else None,
            "regions": regions, "local_native_status": bool(local_scopes),
            "message": "Local native-status records are used for the mapped region. Boundary snapshots may be older than plant records." if local_scopes else "Ontario native; local status unverified. A verified local checklist boundary is not available for this location.",
            "condition_note": "Plants with missing information for a selected condition are excluded. Matches use recorded conditions and do not guarantee survival."}



class GeocoderBusy(ConnectionError):
    pass


def geocode_address(query: str) -> dict | None:
    """Geocode one address with bounded storage and no waiting request queue."""
    global _last_request
    cache_key = hashlib.sha256(query.casefold().encode("utf8")).hexdigest()
    cached = _geocode_cache.get(cache_key)
    if cached is not None:
        return cached
    if not _geocode_lock.acquire(blocking=False):
        raise GeocoderBusy("Address lookup is busy. Try again shortly.")
    try:
        cached = _geocode_cache.get(cache_key)
        if cached is not None:
            return cached
        interval = time.monotonic() - _last_request
        if interval < 1.1:
            time.sleep(1.1 - interval)
        _last_request = time.monotonic()
        url = NOMINATIM_ENDPOINT + "?" + urlencode({
            "q": query, "format": "jsonv2", "countrycodes": "ca", "limit": 1,
            "addressdetails": 1,
        })
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urlopen(request, timeout=12) as response:
                matches = json.load(response)
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            raise ConnectionError("Address lookup is temporarily unavailable. You can use the Ontario demo garden instead.") from exc
        if not matches:
            return None
        try:
            first = matches[0]
            data = {
                "latitude": float(first["lat"]), "longitude": float(first["lon"]),
                "province": first.get("address", {}).get("state", ""),
                "display_name": first.get("display_name", query),
            }
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise ConnectionError("The address service returned an incomplete result.") from exc
        _geocode_cache.put(cache_key, data)
        return data
    finally:
        _geocode_lock.release()


class Handler(BaseHTTPRequestHandler):
    """Serve API routes and allowlisted static files."""

    def log_request(self, code="-", size="-"):
        # Only fixed route labels are logged; queries and user text are omitted.
        try:
            route = urlsplit(getattr(self, "path", "")).path
        except ValueError:
            route = ""
        if route not in {"/", "/api/geocode", "/api/plants", "/api/demo-garden", "/favicon.ico"}:
            route = "/assets/[file]" if route.startswith("/assets/") else "/[unmatched]"
        command = getattr(self, "command", "")
        method = command if command in {"GET", "POST", "HEAD"} else "OTHER"
        status = str(code) if str(code).isdigit() else "-"
        sys.stderr.write(f"{method} {route} {status}\n")

    def log_message(self, format, *args):
        sys.stderr.write("HTTP request event\n")

    def do_POST(self):
        if self.path != "/api/geocode":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            self.send_json({"error": "Use application/json."}, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
            return
        if self.headers.get("Transfer-Encoding"):
            self.send_json({"error": "Transfer encoding is not supported."}, HTTPStatus.BAD_REQUEST)
            return
        try:
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) != 1:
                raise ValueError()
            length = int(lengths[0])
            if not 1 <= length <= 2048:
                self.send_json({"error": "Request body must be 1â€“2048 bytes."}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                return
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError()
            payload = json.loads(raw)
            if not isinstance(payload, dict) or not isinstance(payload.get("q"), str):
                raise ValueError()
            text = payload["q"].strip()
            if not 3 <= len(text) <= 180:
                raise ValueError()
        except (ValueError, UnicodeError):
            self.send_json({"error": "Enter a Canadian place or address (3â€“180 characters)."}, HTTPStatus.BAD_REQUEST)
            return
        try:
            result = geocode_address(text)
        except GeocoderBusy as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.TOO_MANY_REQUESTS)
            return
        except ConnectionError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return
        if result is None:
            self.send_json({"error": "No Canadian location found. Try a city and province."}, HTTPStatus.NOT_FOUND)
        else:
            self.send_json(result)

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        contents = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(contents)))
        self.send_header("Cache-Control", "no-store")
        if status == HTTPStatus.TOO_MANY_REQUESTS:
            self.send_header("Retry-After", "2")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(contents)

    def send_asset(self, relative_path: str) -> None:
        # resolve + containment check prevents path traversal.
        asset_root = (ROOT / "assets").resolve()
        path = (asset_root / relative_path).resolve()
        if not path.is_relative_to(asset_root) or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        contents = path.read_bytes()
        media_type, _ = mimetypes.guess_type(path.name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", media_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(contents)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(contents)

    def do_GET(self) -> None:  # noqa: N802 (required BaseHTTPRequestHandler API)
        try:
            parsed = urlsplit(self.path)
            query = {k: vals[0] for k, vals in parse_qs(parsed.query, keep_blank_values=True, max_num_fields=32).items()}
        except ValueError:
            self.send_json({"error": "Invalid request."}, HTTPStatus.BAD_REQUEST)
            return

        if parsed.path == "/":
            contents = (ROOT / "index.html").read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(contents)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(contents)
        elif parsed.path.startswith("/assets/"):
            self.send_asset(parsed.path.removeprefix("/assets/"))
        elif parsed.path == "/api/plants":
            try:
                self.send_json(filter_catalogue(query))
            except ValueError as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except db.DatabaseUnavailable as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.SERVICE_UNAVAILABLE)
        elif parsed.path == "/api/geocode":
            self.send_json({"error": "Submit address searches using POST JSON."}, HTTPStatus.METHOD_NOT_ALLOWED)
        elif parsed.path == "/api/demo-garden":
            # Fixed approximate coordinates for the Oakville example.
            self.send_json({"latitude": 43.4489, "longitude": -79.6974,
                            "province": "Ontario", "display_name": "Demo garden Â· Oakville, Ontario (approximate)"})
        elif parsed.path == "/favicon.ico":
            self.send_asset("favicon.svg")
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")


def start_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = BoundedHTTPServer((host, port), Handler, housekeeping=_geocode_cache.expire)
    print(f"Native Plant Finder running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    start_server(port=int(os.environ.get("PORT", "8000")))
