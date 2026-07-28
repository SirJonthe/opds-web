"""Web application server software for parsing, navigating, and presenting a UI for OPDS feeds."""

import hashlib
import opds
from flask import Response, Flask, request
import base64
import requests
from urllib.parse import urlparse


SERVER_FILE = "servers.txt"


class App:
    """The web server software for the navigating and generating HTML for OPDS.
    
    Attributes:
        client: The Flask web client.
        servers: A dictionary of server URL:s stored by server ID as key.
    """

    client: Flask
    servers: dict[str, str]


    @staticmethod
    def _server_id(url : str) -> str:
        """Extract a server ID from a server URL.
        
        Args:
            url: A URL.
        
        Returns:
            The server ID.
        """
        return hashlib.sha256(
            url.encode("utf-8")
        ).hexdigest()[:12]


    @staticmethod
    def _load_servers() -> dict[str, str]:
        """Loads the list of servers as stored in the main server file.
        
        Returns:
            A dictionary of server URL:s stored by server ID as key. Silently returns an empty dictionary if the file could not be loaded.
        """
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
        """Saves a server dictionary to the main server file by overwriting it.

        Args:
            servers: A dictionary of server URL:s stored by server ID as key.
        """
        with open(SERVER_FILE, "w") as f:
            f.write("#[protocol]://[hostname]:[port]/[opds_url]\n")
            for _, url in servers.items():
                f.write(f'{url}\n')


    def add_server(self, url : str):
        """Adds a new server URL to the existing server list and updates the main server file.

        Args:
            url: The server URL to store.
        """
        self.servers[App._server_id(url)] = url.strip().rstrip("/").lower()
        App._save_servers(self.servers)


    def remove_server(self, server_id : str):
        """Removes the server URL corresponding to the server ID key and updates the main server file.

        Args:
            server_id: The server ID key corresponding to the server URL to remove.
        """
        del self.servers[server_id]
        App._save_servers(self.servers)


    def __init__(self : App):
        self.client = Flask(__name__)
        self.servers = App._load_servers()


    @staticmethod
    def _get_base_server_url(url : str) -> str:
        """ Returns the base URL from a full URL.

        Args:
            url: The full URL. For instance http://homeserver:25600/opds/v1.2/libraries.

        Returns:
            The base URL. For instance http://homeserver:25600.
        """
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}"


    def get_credentials(self, url : str) -> tuple[str, str] | Response:
        # TODO: Check if stored credentials exist
        # TODO: Invalidate stored credentials if login fails
        """Requests the browser to prompt the user for credentials.

        Args:
            url: The URL to request credentials for (not really necessary).
        
        Returns:
            Either a tuple of username and password, or an HTTP response indicating an error.
        """
        server = App._get_base_server_url(url)
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Basic "):
            return Response(
                "Authentication required",
                status=401,
                headers={
                    "WWW-Authenticate": f'Basic realm="{server} OPDS"'
                }
            )
        encoded = auth.split(" ", 1)[1]
        decoded = base64.b64decode(encoded).decode("utf-8")
        username, password = decoded.split(":", 1)
        return username, password


    def get_feed_reader(self, path : str) -> opds.Reader | Response:
        """Retrieves a (presumably) OPDS feed and parses it inside an OPDS reader object which is then returned.

        Args:
            path: The path to retrieve a feed from.
        
        Returns:
            Either an OPDS reader object, or an HTTP response indicating an error.
        """
        credentials = self.get_credentials(path)
        if isinstance(credentials, Response):
            return credentials
        username, password = credentials
        r = requests.get(
            path,
            auth=(username, password)
        )
        r.raise_for_status()
        content_type = r.headers.get("Content-Type", "")
        if "atom" in content_type or "xml" in content_type:
            return opds.from_xml(r.text)
        elif "json" in content_type:
            return opds.from_json(r.text)
        return Response(
            "Unsupported format",
            status=415
        )