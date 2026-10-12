"""Static file server with HTTP Range support. usage: serve.py ROOT PORT"""
import sys, os, re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ROOT, PORT = os.path.abspath(sys.argv[1]), int(sys.argv[2])
TYPES = {'.webm': 'video/webm', '.mkv': 'video/x-matroska', '.html': 'text/html', '.js': 'text/javascript'}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        p = os.path.normpath(os.path.join(ROOT, self.path.split('?')[0].lstrip('/')))
        if not p.startswith(ROOT) or not os.path.isfile(p):
            self.send_response(404); self.end_headers(); return
        size = os.path.getsize(p)
        ctype = TYPES.get(os.path.splitext(p)[1], 'application/octet-stream')
        if 'opus_only' in p and p.endswith('.webm'):
            ctype = 'audio/webm'
        rng = self.headers.get('Range')
        start, end = 0, size - 1
        if rng:
            m = re.match(r'bytes=(\d*)-(\d*)', rng)
            if m.group(1):
                start = int(m.group(1)); end = int(m.group(2)) if m.group(2) else size - 1
            else:
                start = size - int(m.group(2))
            end = min(end, size - 1)
            if start >= size:
                self.send_response(416); self.send_header('Content-Range', 'bytes */%d' % size); self.end_headers(); return
            self.send_response(206); self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, size))
        else:
            self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        with open(p, 'rb') as f:
            f.seek(start)
            try:
                self.wfile.write(f.read(end - start + 1))
            except (BrokenPipeError, ConnectionResetError):
                pass


ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
