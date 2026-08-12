"""Web application server software for parsing, navigating, and presenting a UI for OPDS feeds."""

import hashlib
from typing import Any
import opds
from flask import Response, Flask, session, request
import base64
import requests
from urllib.parse import urlparse
import secrets
from cryptography.fernet import Fernet
import shutil


SERVER_FILE = "conf/servers.txt"
SECRET_FILE = "conf/secret.key"
CRYPT_FILE = "conf/crypt.key"


class App:
    """The web server software for the navigating and generating HTML for OPDS.
    
    Attributes:
        client: The Flask web client.
        servers: A dictionary of server URL:s stored by server ID as key.
        cipher: Encryption and decryption.
        calibre: A string denoting the availability of Calibre tools which can be used for transcoding books.
    """

    client: Flask
    servers: dict[str, str]
    cipher : Fernet
    calibre : str | None


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
                    line = line.strip().lower()
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


    @staticmethod
    def _gen_secret() -> str:
        """Loads a secret key from the main secret key file, or generates a new one and stores it in the main secret key file.

        Returns:
            The key.
        """
        key : str
        try:
            with open(SECRET_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    key = line.strip()
                    break
        except FileNotFoundError:
            key = secrets.token_hex(32)
            try:
                with open(SECRET_FILE, "w") as f:
                    f.write(key)
            except:
                pass
        return key


    @staticmethod
    def _gen_cipher() -> Fernet:
        """Loads a cryptographic key from the main cryptographic key file, or generates a new one and stores it in the main cryptographic key file, and returns the cipher.

        Returns:
            The cipher.
        """
        key : str
        try:
            with open(CRYPT_FILE, "rb") as f:
                for line in f:
                    key = line.strip()
                    break
        except FileNotFoundError:
            key = Fernet.generate_key()
            try:
                with open(CRYPT_FILE, "wb") as f:
                    f.write(key)
            except:
                pass
        return Fernet(key)


    def add_server(self, url : str):
        """Adds a new server URL to the existing server list and updates the main server file.

        Args:
            url: The server URL to store.
        """
        self.servers[App._server_id(url)] = url.strip().lower()
        App._save_servers(self.servers)


    def remove_server(self, server_id : str):
        """Removes the server URL corresponding to the server ID key and updates the main server file.

        Args:
            server_id: The server ID key corresponding to the server URL to remove.
        """
        del self.servers[server_id]
        App._save_servers(self.servers)


    def __init__(self):
        self.client = Flask(__name__)
        self.client.secret_key = App._gen_secret()
        self.servers = App._load_servers()
        self.cipher = App._gen_cipher()
        self.refresh_convert_tools()


    def refresh_convert_tools(self):
        self.calibre = shutil.which("ebook-convert")


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


    def unauthorized_response(self, url : str, fail_html : str) -> Response:
        """Returns the response for when we want to request authentication.

        Args:
            url: The URL to request authentication for.
            fail_html: The HTML presented when we request authentication.
        
        Returns:
            The response.
        """
        server = App._get_base_server_url(url)
        return Response(
            fail_html,
            status=401,
            headers={
                "WWW-Authenticate": f'Basic realm="{server} OPDS"'
            },
            content_type="text/html; charset=utf-8"
        )

    def store_in_session(self, key : str, val : str):
        """Stores an encrypted value in the session cookie.

        Args:
            key: The key.
            val: The value.
        """
        encrypted = self.cipher.encrypt(val.encode("utf-8"))
        session[key] = encrypted.decode("utf-8")


    def get_from_session(self, key : str) -> Any | None:
        """Retrieves a decrypted value from the session cookie.

        Args:
            key: The key.
        
        Returns:
            The value.
        """
        if key not in session:
            return None
        encrypted = session[key].encode("utf-8")
        return self.cipher.decrypt(encrypted).decode("utf-8")


    def clear_credentials(self, url : str):
        """Removes current credentials for a given URL.

        Args:
            url: The URL for which to clear credentials.
        """
        server = App._get_base_server_url(url)
        session.pop(f'{server}:username', None)
        session.pop(f'{server}:password', None)


    def get_credentials(self, url : str, fail_html : str) -> tuple[str, str] | Response:
        """Requests the browser to prompt the user for credentials.

        Args:
            url: The URL to request credentials for (not really necessary).
            fail_html: An HTML string returned in a response 
        
        Returns:
            Either a tuple of username and password, or an HTTP response indicating an error.
        """
        server = App._get_base_server_url(url)
        username = self.get_from_session(f'{server}:username')
        password = self.get_from_session(f'{server}:password')
        if username is not None and password is not None:
            return username, password

        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Basic "):
            return self.unauthorized_response(url, fail_html)
        encoded = auth.split(" ", 1)[1]
        decoded = base64.b64decode(encoded).decode("utf-8")
        username, password = decoded.split(":", 1)
        return username, password


    def get_feed_reader(self, path : str, fail_html : str, page : int) -> opds.Reader | Response:
        """Retrieves a (presumably) OPDS feed and parses it inside an OPDS reader object which is then returned.

        Args:
            path: The path to retrieve a feed from.
            fail_html: An HTML string that is returned inside a response if the browser fails to authenticate.
            page: The page integer
        
        Returns:
            Either an OPDS reader object, or an HTTP response indicating an error.
        """
        credentials = self.get_credentials(path, fail_html)
        if isinstance(credentials, Response):
            return credentials
        username, password = credentials
        r = requests.get(
            path,
            auth=(username, password)
        )
        if r.status_code == 401:
            self.clear_credentials(path)
            return self.unauthorized_response(path, fail_html)
        else:
            r.raise_for_status()
        base_url : str = App._get_base_server_url(path)
        content_type : str = r.headers.get("Content-Type", "")
        if "atom" in content_type or "xml" in content_type:
            reader : opds.Reader = opds.from_xml(r.text, base_url, page)
            if "search" in reader.links and len(reader.links["search"]) > 0:
                s = requests.get(
                    reader.links["search"][0].url,
                    auth=(username, password)
                )
                if s.status_code == 401:
                    self.clear_credentials(reader.links["search"][0].url)
                    return self.unauthorized_response(reader.links["search"][0].url, fail_html)
                else:
                    s.raise_for_status()
                reader.search = opds.search_from_xml(s.text, base_url)
            return reader
        elif "json" in content_type:
            return opds.from_json(r.text, base_url, page)
        print(r.text)
        return Response(
            "Unsupported format",
            status=415
        )