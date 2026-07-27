import hashlib
import opds
from flask import Response, Flask, request
import base64
import requests
from urllib.parse import urljoin


SERVER_FILE = "servers.txt"


class App:
    client: Flask
    servers: dict[str, str]


    @staticmethod
    def _server_id(url : str):
        return hashlib.sha256(
            url.encode("utf-8")
        ).hexdigest()[:12]


    @staticmethod
    def _load_servers() -> dict[str, str]:
        srv = {}
        try:
            with open(SERVER_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip().rstrip("/").lower()
                    if not line or line.startswith("#"):
                        continue
                    srv[App._server_id(line)] = line
        except FileNotFoundError:
            pass
        return srv


    @staticmethod
    def _save_servers(servers : dict[str, str]):
        with open(SERVER_FILE, "w") as f:
            f.write("#[protocol]://[hostname]:[port]/[opds_url]\n")
            for _, url in servers.items():
                f.write(f'{url}\n')


    def add_server(self, url : str):
        self.servers[App._server_id(url)] = url.strip().rstrip("/").lower()
        App._save_servers(self.servers)


    def remove_server(self, server_id : str):
        del self.servers[server_id]
        App._save_servers(self.servers)


    def __init__(self : App):
        self.client = Flask(__name__)
        self.servers = App._load_servers()


    def get_credentials(self, server_id : str) -> tuple[str, str]:
        server = self.servers[server_id]
        if server == None:
            return Response(
                "No server",
                status=500
            )
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Basic "):
            return Response(
                "Authentication required",
                status=401,
                headers={
                    "WWW-Authenticate": 'Basic realm="${server} OPDS"'
                }
            )
        encoded = auth.split(" ", 1)[1]
        decoded = base64.b64decode(encoded).decode("utf-8")
        username, password = decoded.split(":", 1)
        return username, password


    def get_feed_reader(self, path : str, server_id : str) -> opds.Reader | Response | None:
        credentials = self.get_credentials(server_id)
        if isinstance(credentials, Response):
            return credentials
        username, password = credentials
        r = requests.get(
            urljoin(self.servers[server_id], path),
            auth=(username, password)
        )
        r.raise_for_status()
        content_type = r.headers.get("Content-Type", "")
        if "atom" in content_type or "xml" in content_type:
            return opds.from_xml(r.text)
        elif "json" in content_type:
            return opds.from_json(r.text)
        return None