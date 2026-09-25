#!/usr/bin/env python3
"""
RoboAssistant 1.0.0-GA Web Interface Local Preview Server
Serves /roboassistant/web/ directory locally.
"""

import http.server
import socketserver
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def run():
    print(f"[*] RoboAssistant Web UI Preview Server running at:")
    print(f"    http://localhost:{PORT}")
    print(f"    Direct File URI: file://{DIRECTORY}/index.html")
    print(f"[*] Serving files from: {DIRECTORY}")
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Server stopped.")

if __name__ == "__main__":
    run()
