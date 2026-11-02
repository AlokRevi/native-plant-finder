"""Bounded request handling and expiring in-memory storage."""
from collections import OrderedDict
from http.server import ThreadingHTTPServer
import sys
import threading
import time


class TTLCache:
    def __init__(self, max_entries=256, ttl=900, clock=time.monotonic):
        self.max_entries = max_entries
        self.ttl = ttl
        self.clock = clock
        self.entries = OrderedDict()
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            self._expire()
            item = self.entries.get(key)
            return item[1] if item else None

    def put(self, key, value):
        with self.lock:
            self._expire()
            self.entries.pop(key, None)
            self.entries[key] = (self.clock() + self.ttl, value)
            while len(self.entries) > self.max_entries:
                self.entries.popitem(last=False)

    def expire(self):
        with self.lock:
            self._expire()

    def _expire(self):
        now = self.clock()
        for key in list(self.entries):
            if self.entries[key][0] <= now:
                del self.entries[key]


class RequestLimiter:
    def __init__(self, limit=120, window=60, max_clients=2048, clock=time.monotonic):
        self.limit, self.window, self.max_clients = limit, window, max_clients
        self.clock = clock
        self.clients = OrderedDict()
        self.lock = threading.Lock()

    def allow(self, client):
        with self.lock:
            now = self.clock()
            for key in list(self.clients):
                if self.clients[key][0] + self.window <= now:
                    del self.clients[key]
            if client not in self.clients:
                # Fail closed instead of evicting an active client's rate limit.
                if len(self.clients) >= self.max_clients:
                    return False
                self.clients[client] = (now, 0)
            started, count = self.clients[client]
            if count >= self.limit:
                return False
            self.clients[client] = (started, count + 1)
            return True


class BoundedHTTPServer(ThreadingHTTPServer):
    request_queue_size = 32
    daemon_threads = True

    def __init__(self, address, handler, max_workers=16, request_timeout=15, limiter=None, housekeeping=None):
        self.housekeeping = housekeeping
        self.slots = threading.BoundedSemaphore(max_workers)
        self.request_timeout = request_timeout
        self.limiter = limiter if limiter is not None else RequestLimiter()
        super().__init__(address, handler)

    def service_actions(self):
        if self.housekeeping is not None:
            self.housekeeping()

    def get_request(self):
        request, address = super().get_request()
        request.settimeout(self.request_timeout)
        return request, address

    def process_request(self, request, address):
        if not self.limiter.allow(address[0]):
            self._reject(request, 429, b'Too many requests')
            return
        if not self.slots.acquire(blocking=False):
            self._reject(request, 503, b'Server busy')
            return
        try:
            super().process_request(request, address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()

    def _reject(self, request, status, body):
        try:
            request.settimeout(0.2)
            request.sendall(
                f'HTTP/1.0 {status} Limited\r\nContent-Type: text/plain\r\n'
                f'Content-Length: {len(body)}\r\nRetry-After: 60\r\nConnection: close\r\n\r\n'.encode('ascii') + body
            )
        except OSError:
            pass
        finally:
            self.shutdown_request(request)

    def handle_error(self, request, client_address):
        # Do not log request targets, bodies or external exception details.
        sys.stderr.write('HTTP request failed\n')
