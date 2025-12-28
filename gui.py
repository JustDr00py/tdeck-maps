#!/usr/bin/env python3
"""Launch the Meshtastic Tile Generator GUI in a browser."""

import http.server
import socketserver
import webbrowser
import threading
import signal
import sys
from pathlib import Path

PORT = 8000

def main():
    os_dir = Path(__file__).parent
    
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(os_dir), **kwargs)
        
        def log_message(self, format, *args):
            pass  # Suppress request logging
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}/maps.html"
        print(f"🗺️  Meshtastic Tile Generator GUI")
        print(f"   Opening {url}")
        print(f"   Press Ctrl+C to stop\n")
        
        # Open browser after short delay
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        
        # Handle Ctrl+C gracefully
        signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
    
    print("\nServer stopped.")

if __name__ == "__main__":
    main()
