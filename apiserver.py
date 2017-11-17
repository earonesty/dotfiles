import sys, json
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse as urlparse
import threading
import logging
log = logging.getLogger(__name__)

class ApiError(Exception):
    def __init__(self, code, msg=None, desc=None):
        self.code = code
        self.msg = msg
        self.desc = desc

    def __str__(self):
        return f"ApiError({self.code}, {self.msg})"

def ApiRoute(path):
    def outer(func):
        if not hasattr(func, "_routes"):
            setattr(func, "_routes", [])
        func._routes += [path]
        return func
    return outer

class ApiServer(HTTPServer):
    def __init__(self, addr, port):
        """
        Create a new server on address, port.  Port can be zero.

        from apiserver import ApiServer, ApiError, ApiRoute

        Create your handlers by inheriting from ApiServer and tagging them with @ApiRoute("/path").

        Alternately you can use the ApiServer() directly, and call add_handler("path", function)

        Raise errors by raising ApiError(code, message, description=None)

        Return responses by simply returning a dict() or str() object

        Parameter to handlers is a dict()

        Query arguments are shoved into the dict via urllib.parse_qs

        """
        server_address = (addr, port)
        self.__addr = addr

        # instead of attempting multiple inheritence

        # shim class that is an ApiHandler
        class handler_class(ApiHandler):
            pass

        self.handler_class = handler_class

        # routed methods map into handler
        for meth in type(self).__dict__.values():
            if hasattr(meth, "_routes"):
                for route in meth._routes:
                    self.add_route(route, meth)

        super().__init__(server_address, handler_class)

    def add_route(self, path, meth):
        self.handler_class._routes[path] = meth
        
    def port(self):
        "Get my port"
        sa = self.socket.getsockname()
        return sa[1]

    def address(self):
        "Get my ip address"
        sa = self.socket.getsockname()
        return sa[0]

    def uri(self, path):
        "Make a URI pointing at myself"
        if path[0] == "/":
            path = path[1:]
        return "http://"+self.__addr + ":"+ str(self.port()) + "/" + path

    def shutdown(self):
        super().shutdown()
        self.socket.close()

class ApiHandler(BaseHTTPRequestHandler):
    _routes={}


    def do_GET(self):
        self.do_XXX()

    def do_POST(self):
        content="{}"
        if self.headers["Content-Length"]:
            length = int(self.headers["Content-Length"])
            content=self.rfile.read(length)
        info=None
        if content:
            try:
                info = json.loads(content)
            except:
                raise ApiError(400, "Invalid JSON", content)
        self.do_XXX(info)

    def do_XXX(self, info={}):
        try:
            url=urlparse.urlparse(self.path)

            handler = self._routes.get(url.path)

            if url.query:
                params = urlparse.parse_qs(url.query)
            else:
                params = {}

            info.update(params)

            if handler:
                try:
                    response=handler(info)
                    self.send_response(200)
                    if response is None:
                        response = ""
                    if type(response) is dict:
                        response = json.dumps(response)
                    response = bytes(str(response),"utf-8")
                    self.send_header("Content-Length", len(response))
                    self.end_headers()
                    self.wfile.write(response)
                except ApiError:
                    raise
                except ConnectionAbortedError as e:
                    log.error(f"GET {self.path} : {e}")
                except Exception as e:
                    raise ApiError(500, str(e))
            else:
                raise ApiError(404)
        except ApiError as e:
            try:
                self.send_error(e.code, e.msg, e.desc)
            except ConnectionAbortedError as e:
                log.error(f"GET {self.path} : {e}")

import unittest

class TestRest(unittest.TestCase):
    def test_basic(self):
        class MyServer(ApiServer): 
            @ApiRoute("/popup")
            def popup(req):
                return "HERE"

            @ApiRoute("/json")
            def json(req):
                return {"obj":1}

        httpd = MyServer('127.0.0.1', 0)

        httpd.add_route("/foo", lambda x: "FOO" + x["x"][0])

        try:
            print("serving on ", httpd.address(), httpd.port())

            threading.Thread(target=httpd.serve_forever).start()

            import requests
            response = requests.post(httpd.uri("/popup"), data='{}')
            self.assertEqual(response.text, "HERE")

            response = requests.post(httpd.uri("/notfound"), data='{}')
            self.assertEqual(response.status_code, 404)

            response = requests.get(httpd.uri("/foo?x=4"))
            self.assertEqual(response.text, "FOO4")
        finally:
            httpd.shutdown()

    def test_error(self):
        class MyServer(ApiServer): 
            @ApiRoute("/popup")
            def popup(req):
                raise ApiError(501, "BLAH")

        httpd = MyServer('127.0.0.1', 0)

        try:
            print("serving on ", httpd.address(), httpd.port())

            threading.Thread(target=httpd.serve_forever).start()

            import requests
            response = requests.post(httpd.uri("/popup"), data='{}')
            self.assertEqual(response.status_code, 501)
        finally:
            httpd.shutdown()

if __name__ == "__main__":
    unittest.main()

