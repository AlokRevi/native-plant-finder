"""Security regressions for privacy, resource bounds and runtime archives."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import app
from security_limits import TTLCache, RequestLimiter, BoundedHTTPServer

spec = importlib.util.spec_from_file_location('runtime_setup', app.ROOT/'scripts/database/setup_local_database.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class StorageTests(unittest.TestCase):
    def test_cache_expires_and_evicts(self):
        clock = Mock(return_value=0)
        cache = TTLCache(max_entries=2, ttl=10, clock=clock)
        for key in ['a', 'b', 'c']:
            cache.put(key, {'value': key})
        self.assertIsNone(cache.get('a'))
        self.assertEqual(2, len(cache.entries))
        clock.return_value = 11
        self.assertIsNone(cache.get('c'))
        self.assertEqual(0, len(cache.entries))

    def test_idle_cache_cleanup(self):
        clock=Mock(return_value=0)
        cache=TTLCache(ttl=10,clock=clock)
        cache.put("key",{"value":"synthetic"})
        clock.return_value=11
        cache.expire()
        self.assertEqual(0,len(cache.entries))

    def test_rate_limit_and_expiry(self):
        clock = Mock(return_value=0)
        limiter = RequestLimiter(limit=2, window=10, max_clients=1, clock=clock)
        self.assertTrue(limiter.allow('one'))
        self.assertTrue(limiter.allow('one'))
        self.assertFalse(limiter.allow('one'))
        self.assertFalse(limiter.allow('two'))
        clock.return_value = 11
        self.assertTrue(limiter.allow('two'))
        self.assertEqual(1, len(limiter.clients))

    def test_geocoder_rejects_busy_without_waiting(self):
        with patch.object(app, '_geocode_lock') as lock, patch.object(app, '_geocode_cache', TTLCache()):
            lock.acquire.return_value = False
            with self.assertRaises(app.GeocoderBusy):
                app.geocode_address('synthetic address')
            lock.acquire.assert_called_once_with(blocking=False)


class ArchiveTests(unittest.TestCase):
    def test_bad_hash_rejected_before_extract_or_zip_processing(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'postgresql.zip'
            path.write_bytes(b'tampered archive')
            with patch.object(installer, 'extract') as extract, patch.object(installer.zipfile, 'ZipFile') as zipfile:
                with self.assertRaisesRegex(RuntimeError, 'SHA-256 mismatch'):
                    installer.prepare_runtime_archive(path, 'postgresql.zip', Path(td)/'runtime', Path(td))
                extract.assert_not_called()
                zipfile.assert_not_called()

    def test_good_hash_matches(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'fixture.zip';path.write_bytes(b'fixture')
            digest = hashlib.sha256(b'fixture').hexdigest()
            self.assertEqual(digest, installer.verify_archive(path, digest))

    def test_expected_hashes_match_registry(self):
        registry = json.loads((app.ROOT/'data/central/runtime-sources.json').read_text())
        self.assertEqual({r['file']:r['sha256'] for r in registry}, installer.SHA256)


class LoggingTests(unittest.TestCase):
    def test_logs_omit_query_and_unknown_path_text(self):
        handler = app.Handler.__new__(app.Handler)
        handler.command = 'GET'
        log = io.StringIO()
        with contextlib.redirect_stderr(log):
            for path in ['/api/geocode?q=PRIVATE_CANARY', '/PRIVATE_CANARY', '/assets/PRIVATE_CANARY']:
                handler.path = path
                handler.log_request(200)
            handler.log_message('PRIVATE_CANARY %s', 'PRIVATE_CANARY')
        self.assertNotIn('PRIVATE_CANARY', log.getvalue())
        self.assertIn('/api/geocode', log.getvalue())


class HTTPPrivacyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = BoundedHTTPServer(('127.0.0.1', 0), app.Handler)
        cls.base = 'http://127.0.0.1:'+str(cls.server.server_port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(2)

    def post(self, body, content_type='application/json'):
        return Request(self.base+'/api/geocode', data=body, headers={'Content-Type':content_type})

    def test_post_geocode_does_not_log_body(self):
        log = io.StringIO()
        with patch.object(app, 'geocode_address', return_value={'province':'Ontario'}), contextlib.redirect_stderr(log):
            with urlopen(self.post(b'{"q":"PRIVATE_CANARY"}'), timeout=3) as response:
                self.assertEqual(200, response.status)
        self.assertNotIn('PRIVATE_CANARY', log.getvalue())

    def test_legacy_get_disabled(self):
        with self.assertRaises(HTTPError) as ctx:
            urlopen(self.base+'/api/geocode?q=synthetic', timeout=3)
        self.assertEqual(405, ctx.exception.code)

    def test_invalid_body_and_oversize(self):
        for body, content_type, expected in [(b'[]','application/json',400),(b'bad','application/json',400),(b'{}','text/plain',415),(b'x'*2049,'application/json',413)]:
            with self.assertRaises(HTTPError) as ctx:
                urlopen(self.post(body,content_type), timeout=3)
            self.assertEqual(expected, ctx.exception.code)

    def test_busy_returns_retry_after(self):
        with patch.object(app, 'geocode_address', side_effect=app.GeocoderBusy('Busy')):
            with self.assertRaises(HTTPError) as ctx:
                urlopen(self.post(b'{"q":"synthetic"}'), timeout=3)
        self.assertEqual(429,ctx.exception.code)
        self.assertEqual('2',ctx.exception.headers['Retry-After'])

    def test_capacity_rejects_and_releases(self):
        request = Mock()
        # Hold all available slots; no thread is created for the excess connection.
        for _ in range(16):self.assertTrue(self.server.slots.acquire(False))
        try:
            self.server.process_request(request, ('192.0.2.1', 1234))
            self.assertIn(b'503', request.sendall.call_args.args[0])
            request.close.assert_called_once()
        finally:
            for _ in range(16):self.server.slots.release()

    def test_client_limit_rejects_before_worker(self):
        request=Mock()
        with patch.object(self.server.limiter, 'allow', return_value=False):
            self.server.process_request(request, ('192.0.2.1',1234))
        self.assertIn(b'429',request.sendall.call_args.args[0])

    def test_worker_failure_releases_slot(self):
        request=Mock()
        with patch('http.server.ThreadingHTTPServer.process_request_thread',side_effect=RuntimeError('synthetic')):
            self.server.slots.acquire()
            with self.assertRaises(RuntimeError):self.server.process_request_thread(request,('192.0.2.1',1234))
        for _ in range(16):self.assertTrue(self.server.slots.acquire(False))
        for _ in range(16):self.server.slots.release()

    def test_socket_timeout_is_set(self):
        request=Mock()
        with patch('http.server.ThreadingHTTPServer.get_request',return_value=(request,('192.0.2.1',1234))):
            self.server.get_request()
        request.settimeout.assert_called_with(15)


if __name__=='__main__':unittest.main()
