import gzip
import hashlib
import http.server
import io
import json
import os
import re
import socketserver
import sys
import threading
import time
import urllib.request
from urllib.parse import unquote

PORT = int(os.environ.get('PORT', 5000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

META_PIXEL_ID    = '1002705989178676'
META_CAPI_TOKEN  = os.environ.get('META_PIXEL_ACCESS_TOKEN', '')
META_CAPI_URL    = f'https://graph.facebook.com/v21.0/{META_PIXEL_ID}/events'
ALLOWED_EVENTS   = {'PageView'}

_capi_semaphore  = threading.BoundedSemaphore(16)
_rate_lock       = threading.Lock()
_rate_buckets: dict = {}
RATE_MAX_PER_MIN = 20


def host_allowed(host: str) -> bool:
    """Aceita apenas hosts do próprio site (produção, Railway e dev)."""
    if not host:
        return False
    host = host.lower().split(':')[0]
    if host in ('localhost', '127.0.0.1'):
        return True
    if host == 'overshotz.com.br' or host.endswith('.overshotz.com.br'):
        return True
    if host.endswith('.up.railway.app'):
        return True
    if host.endswith('.replit.dev') or host.endswith('.repl.co'):
        return True
    return False


def rate_ok(ip: str) -> bool:
    now = time.time()
    with _rate_lock:
        if len(_rate_buckets) > 10000:
            _rate_buckets.clear()
        bucket = _rate_buckets.get(ip)
        if not bucket or now - bucket[0] > 60:
            _rate_buckets[ip] = [now, 1]
            return True
        if bucket[1] >= RATE_MAX_PER_MIN:
            return False
        bucket[1] += 1
        return True


def send_capi_event(event_name, event_id, source_url, client_ip, user_agent, fbp, fbc):
    """Envia evento à API de Conversões do Meta em background (não bloqueia resposta)."""
    if not META_CAPI_TOKEN:
        return
    user_data = {
        'client_ip_address': client_ip,
        'client_user_agent': user_agent,
    }
    if fbp:
        user_data['fbp'] = fbp
    if fbc:
        user_data['fbc'] = fbc
    payload = {
        'data': [{
            'event_name':       event_name,
            'event_time':       int(time.time()),
            'event_id':         event_id,
            'event_source_url': source_url,
            'action_source':    'website',
            'user_data':        user_data,
        }],
        'access_token': META_CAPI_TOKEN,
    }
    try:
        req = urllib.request.Request(
            META_CAPI_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode('utf-8'))
            received = body.get('events_received', 0)
            print(f'[CAPI] {event_name} enviado (events_received={received})')
    except Exception as e:
        detail = ''
        if hasattr(e, 'read'):
            try:
                detail = e.read().decode('utf-8')[:200]
            except Exception:
                pass
        print(f'[CAPI] ERRO ao enviar {event_name}: {e} {detail}')

MIME_TYPES = {
    '.html':  'text/html; charset=utf-8',
    '.css':   'text/css',
    '.js':    'application/javascript',
    '.json':  'application/json',
    '.webp':  'image/webp',
    '.png':   'image/png',
    '.jpg':   'image/jpeg',
    '.jpeg':  'image/jpeg',
    '.gif':   'image/gif',
    '.svg':   'image/svg+xml',
    '.ico':   'image/x-icon',
    '.woff':  'font/woff',
    '.woff2': 'font/woff2',
    '.ttf':   'font/ttf',
    '.eot':   'application/vnd.ms-fontobject',
    '.mp4':   'video/mp4',
    '.webm':  'video/webm',
    '.map':   'application/json',
}

GZIP_EXTS = {'.html', '.css', '.js', '.json', '.svg', '.map'}
CACHE_LONG = 'public, max-age=31536000, immutable'
CACHE_DAY  = 'public, max-age=86400'
CACHE_NONE = 'no-cache, no-store, must-revalidate'

_gzip_cache: dict = {}


def gzip_compress(data: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', compresslevel=6) as gz:
        gz.write(data)
    return buf.getvalue()


def resolve_path(decoded_path):
    if '?' in decoded_path:
        qs_part   = decoded_path.split('?', 1)[1]
        decoded_path = decoded_path.split('?', 1)[0]
    else:
        qs_part = ''

    fs_path = os.path.normpath(os.path.join(BASE_DIR, decoded_path.lstrip('/')))

    if os.path.isfile(fs_path):
        return fs_path

    decoded2 = unquote(fs_path)
    if os.path.isfile(decoded2):
        return decoded2

    if qs_part and qs_part.startswith('ver='):
        ver_val   = qs_part.split('ver=', 1)[1].split('&')[0]
        ext_match = re.match(r'^(.*)(\.css|\.js)$', fs_path, re.IGNORECASE)
        if ext_match:
            base_no_ext = ext_match.group(1)
            ext = ext_match.group(2)
            for candidate in (
                f"{base_no_ext}_ver={ver_val}{ext}",
                f"{base_no_ext}_ver={ver_val}{ext}".replace('=', '-'),
                f"{base_no_ext}_ver%3D{ver_val}{ext}",
            ):
                if os.path.isfile(candidate):
                    return candidate

    dirpath  = os.path.dirname(fs_path)
    basename = os.path.basename(fs_path)
    if os.path.isdir(dirpath):
        name_no_ext, ext = os.path.splitext(basename)
        for candidate in os.listdir(dirpath):
            cand_path = os.path.join(dirpath, candidate)
            if os.path.isfile(cand_path):
                cand_base, cand_ext = os.path.splitext(candidate)
                if cand_ext.lower() == ext.lower() and cand_base.startswith(name_no_ext):
                    return cand_path

    return None


class OvershotzHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        decoded_path = unquote(self.path)
        path_no_qs   = decoded_path.split('?')[0].rstrip('/')

        # Staging workspace preview (isolated from production routes)
        if path_no_qs == '/__staging' or path_no_qs.startswith('/__staging/'):
            staging_dir = os.path.join(BASE_DIR, 'staging')
            staging_path = path_no_qs.replace('/__staging', '', 1)
            if staging_path in ('', '/'):
                self.serve_file(os.path.join(staging_dir, 'index.html'))
                return
            fs_path = os.path.normpath(os.path.join(staging_dir, staging_path.lstrip('/')))
            if os.path.isfile(fs_path) and os.path.normpath(fs_path).startswith(staging_dir):
                self.serve_file(fs_path)
            else:
                self.send_error(404, f'Staging file not found: {staging_path}')
            return

        if path_no_qs in ('', '/v2'):
            self.serve_file(os.path.join(BASE_DIR, 'v2', 'index.html'))
            return

        if path_no_qs == '/v1':
            self.serve_file(os.path.join(BASE_DIR, 'v1', 'index.html'))
            return

        if path_no_qs.startswith('/v1/') or path_no_qs.startswith('/v2/'):
            suffix       = re.sub(r'^/v[12]', '', decoded_path)
            decoded_path = suffix

        fs_path = resolve_path(decoded_path)

        if fs_path and os.path.isfile(fs_path):
            if not os.path.normpath(fs_path).startswith(BASE_DIR):
                self.send_error(403)
                return
            self.serve_file(fs_path)
        else:
            self.send_error(404, f'File not found: {decoded_path}')

    def do_POST(self):
        path_no_qs = unquote(self.path).split('?')[0].rstrip('/')
        if path_no_qs != '/capi':
            self.send_error(404)
            return
        try:
            origin = self.headers.get('Origin', '') or self.headers.get('Referer', '')
            origin_host = re.sub(r'^https?://', '', origin).split('/')[0]
            if not host_allowed(origin_host):
                self.send_error(403)
                return

            xff = self.headers.get('X-Forwarded-For', '')
            client_ip = xff.split(',')[0].strip() if xff else self.client_address[0]
            if not rate_ok(client_ip):
                self.send_error(429)
                return

            length = int(self.headers.get('Content-Length', 0))
            if length <= 0 or length > 4096:
                self.send_error(400)
                return
            data = json.loads(self.rfile.read(length).decode('utf-8'))
            event_name = data.get('event_name', '')
            event_id   = str(data.get('event_id', ''))[:80]
            source_url = str(data.get('event_source_url', ''))[:500]
            fbp        = str(data.get('fbp', ''))[:100]
            fbc        = str(data.get('fbc', ''))[:200]
            if event_name not in ALLOWED_EVENTS or not event_id:
                self.send_error(400)
                return
            src_host = re.sub(r'^https?://', '', source_url).split('/')[0]
            if not host_allowed(src_host):
                self.send_error(400)
                return

            user_agent = self.headers.get('User-Agent', '')
            if _capi_semaphore.acquire(blocking=False):
                def _send_and_release():
                    try:
                        send_capi_event(event_name, event_id, source_url,
                                        client_ip, user_agent, fbp, fbc)
                    finally:
                        _capi_semaphore.release()
                threading.Thread(target=_send_and_release, daemon=True).start()

            self.send_response(204)
            self.send_header('Cache-Control', CACHE_NONE)
            self.end_headers()
        except Exception:
            self.send_error(400)

    def serve_file(self, fs_path):
        try:
            ext_match    = re.search(r'(\.[a-zA-Z0-9]+)$', os.path.basename(fs_path))
            ext          = ext_match.group(1).lower() if ext_match else ''
            content_type = MIME_TYPES.get(ext, 'application/octet-stream')

            with open(fs_path, 'rb') as f:
                raw = f.read()

            etag = '"' + hashlib.md5(raw).hexdigest()[:16] + '"'
            if self.headers.get('If-None-Match') == etag:
                self.send_response(304)
                self.end_headers()
                return

            if ext in ('.css', '.js', '.woff', '.woff2', '.ttf', '.eot'):
                cache = CACHE_LONG
            elif ext in ('.webp', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico'):
                cache = CACHE_DAY
            else:
                cache = CACHE_NONE

            accept_enc = self.headers.get('Accept-Encoding', '')
            use_gzip   = 'gzip' in accept_enc and ext in GZIP_EXTS

            if use_gzip:
                if fs_path not in _gzip_cache or _gzip_cache[fs_path][0] != etag:
                    _gzip_cache[fs_path] = (etag, gzip_compress(raw))
                body = _gzip_cache[fs_path][1]
            else:
                body = raw

            self.send_response(200)
            self.send_header('Content-Type',                content_type)
            self.send_header('Content-Length',              str(len(body)))
            self.send_header('Cache-Control',               cache)
            self.send_header('ETag',                        etag)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Vary',                        'Accept-Encoding')
            if use_gzip:
                self.send_header('Content-Encoding', 'gzip')
            self.end_headers()
            self.wfile.write(body)

        except Exception as e:
            self.send_error(500, str(e))

    def log_message(self, format, *args):
        try:
            if args and isinstance(args[0], str) and ' ' in args[0]:
                path   = args[0].split()[1]
                status = args[1] if len(args) > 1 else '?'
                if str(status) not in ('200', '304'):
                    print(f'[{status}] {path}')
        except Exception:
            pass


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


if __name__ == '__main__':
    with ReusableTCPServer(('0.0.0.0', PORT), OvershotzHandler) as httpd:
        print(f'OverShotz LP  —  A/B Test Server on http://0.0.0.0:{PORT}')
        print(f'  /     → V2 (nova seção de oferta)')
        print(f'  /v1   → V1 (seção de oferta original)')
        print(f'  /v2   → V2 (nova seção de oferta)')
        print(f'  Gzip: ON  |  ETag: ON  |  Cache: imutable CSS/JS, 1d imgs, no-cache HTML')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nServer stopped.')
            sys.exit(0)
