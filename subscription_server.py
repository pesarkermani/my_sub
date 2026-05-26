#!/usr/bin/env python3
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

SUBSCRIPTION_FILE = '/home/ali/vps/my_sub/sub.txt'

class SubscriptionHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/sub' or self.path == '/subscription':
            try:
                with open(SUBSCRIPTION_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Content-Disposition', 'attachment; filename="subscription.txt"')
                self.send_header('Profile-Update-Interval', '24')
                self.send_header('Subscription-Userinfo', 'upload=0; download=0; total=10737418240; expire=0')
                self.end_headers()
                self.wfile.write(encoded.encode('utf-8'))
                
                print(f"✓ Subscription served to {self.client_address[0]}")
            except Exception as e:
                self.send_error(500, f"Error: {str(e)}")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404 - Not Found')
    
    def log_message(self, format, *args):
        print(f"{self.client_address[0]} - {format % args}")

if __name__ == '__main__':
    PORT = 8765
    server = HTTPServer(('0.0.0.0', PORT), SubscriptionHandler)
    print(f"🚀 Subscription server running on port {PORT}")
    print(f"📡 Subscription URL: http://YOUR_SERVER_IP:{PORT}/sub")
    server.serve_forever()
