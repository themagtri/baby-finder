"""Local preview server (development only). Python's default http.server connection handling resets
responses over ~64KB in the desktop preview on this machine, so we send each file in one write with
HTTP/1.1 and an explicit Content-Length.
Usage: python -I scripts/serve.py [port]      (run from repo root)
"""
import http.server, sys, functools, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def copyfile(self, source, outputfile):
        outputfile.write(source.read())
        outputfile.flush()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8791
    h = functools.partial(Handler, directory=str(ROOT))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), h) as s:
        s.serve_forever()
