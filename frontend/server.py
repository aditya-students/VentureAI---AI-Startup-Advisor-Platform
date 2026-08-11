"""
Simple static file server with clean URL support (.html fallback).

If a requested path like `/login` or `/register` does not exist directly,
it checks if `path + '.html'` exists and serves it.
"""

import http.server
import socketserver
import os
import sys

PORT = 5500
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class CleanURLHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        # Resolve clean URLs (e.g. /login -> /login.html)
        path = self.translate_path(self.path)
        if not os.path.exists(path) and not path.endswith('.html'):
            html_path = path + '.html'
            if os.path.exists(html_path):
                self.path = self.path + '.html'
        return super().do_GET()


if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('127.0.0.1', PORT), CleanURLHandler) as httpd:
        print(f"Frontend server running on http://127.0.0.1:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            sys.exit(0)
