"""Servidor de preview para staging workspace — não interfere no site ativo."""
import gzip, hashlib, http.server, io, os, re, socketserver, sys
from urllib.parse import unquote

PORT = 5001
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MIME_TYPES = {
    '.html': 'text/html; charset=utf-8', '.css': 'text/css',
    '.js': 'application/javascript', '.json': 'application/json',
    '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon', '.woff': 'font/woff', '.woff2': 'font/woff2',
    '.ttf': 'font/ttf', '.eot': 'application/vnd.ms-fontobject',
    '.mp4': 'video/mp4', '.map': 'application/json',
}
GZIP_EXTS = {'.html', '.css', '.js', '.json', '.svg', '.map'}

def gzip_compress(data):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', compresslevel=6) as gz:
        gz.write(data)
    return buf.getvalue()

class StagingHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        decoded_path = unquote(self.path)
        path_no_qs = decoded_path.split('?')[0].rstrip('/')
        if path_no_qs in ('', '/v2', '/v1'):
            self.serve_file(os.path.join(BASE_DIR, 'index.html'))
            return
        fs_path = os.path.normpath(os.path.join(BASE_DIR, decoded_path.lstrip('/')))
        if os.path.isfile(fs_path) and os.path.normpath(fs_path).startswith(BASE_DIR):
            self.serve_file(fs_path)
        else:
            self.send_error(404, f'File not found: {decoded_path}')

    def serve_file(self, fs_path):
        try:
            ext_match = re.search(r'(\.[a-zA-Z0-9]+)$', os.path.basename(fs_path))
            ext = ext_match.group(1).lower() if ext_match else ''
            content_type = MIME_TYPES.get(ext, 'application/octet-stream')
            with open(fs_path, 'rb') as f:
                raw = f.read()
            etag = '"' + hashlib.md5(raw).hexdigest()[:16] + '"'
            if self.headers.get('If-None-Match') == etag:
                self.send_response(304); self.end_headers(); return
            accept_enc = self.headers.get('Accept-Encoding', '')
            use_gzip = 'gzip' in accept_enc and ext in GZIP_EXTS
            body = gzip_compress(raw) if use_gzip else raw
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('ETag', etag)
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            if use_gzip:
                self.send_header('Content-Encoding', 'gzip')
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_error(500, str(e))

    def log_message(self, format, *args):
        pass

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == '__main__':
    with ReusableTCPServer(('0.0.0.0', PORT), StagingHandler) as httpd:
        print(f'STAGING Server  —  Preview workspace on http://0.0.0.0:{PORT}')
        print('  Edite staging/index.html  |  Acesse localhost:5001 no preview')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nStaging server stopped.')
            sys.exit(0)
