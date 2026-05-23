from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Hello from Docker!")

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")

print("Server starting on port 8080...")
HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
