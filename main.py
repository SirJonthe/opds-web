"""OPDS web client entry point."""

from flask import Response, request
import requests
import app
import argparse
import ui


server = app.App()


@server.client.route("/")
def index():
    """The index page/server browser page.
    
    Returns:
        A string containing HTML.
    """
    return ui.UI.servers(server.servers, "login", "add_server") # TODO: change back to "browse"


@server.client.route("/browse")
def browse():
    """The directory browser page.
    
    Returns:
        A string containing HTML.
    """
    url : str = request.args["url"]
    reader = server.get_feed_reader(url)
    if isinstance(reader, Response):
        return reader
    return ui.UI.browse(reader.title, reader.entries, reader.links, url, "browse", "view")


@server.client.route("/view")
def entry():
    """The file entry page.
    
    Returns:
        A string containing HTML.
    """
    reader = server.get_feed_reader(request.args["url"])
    if isinstance(reader, Response):
        return reader
    entry = reader.entries[request.args["entry"]]
    return ui.UI.entry(entry, "thumbnail", "download")


@server.client.route("/download")
def download():
    """The download request.
    
    Returns:
        An HTTP response.
    """
    url : str = request.args["url"]
    credentials = server.get_credentials(url)
    if isinstance(credentials, Response):
        return credentials
    username, password = credentials
    r = requests.get(
        url,
        auth=(username, password),
        stream=True
    )
    r.raise_for_status()
    return Response(
        r.iter_content(chunk_size=8192),
        headers={
            "Content-Type": r.headers.get(
                "Content-Type",
                "application/octet-stream"
            ),
            "Content-Disposition": r.headers.get(
                "Content-Disposition",
                "attachment"
            )
        }
    )


@server.client.route("/thumbnail")
def thumbnail():
    """The thumbnail request.
    
    Returns:
        An HTTP reqiest.
    """
    url : str = request.args["url"]
    credentials = server.get_credentials(url)
    if isinstance(credentials, Response):
        return credentials
    username, password = credentials
    r = requests.get(
        url,
        auth=(username, password),
        stream=True
    )
    r.raise_for_status()
    return Response(
        r.iter_content(chunk_size=8192),
        content_type=r.headers.get("Content-Type", "image/jpeg")
    )


@server.client.route("/add_server", methods=["POST"])
def add_server():
    """Adds a server to the server list. Returns to the server browser page.
    
    Returns:
        A string containing HTML.
    """
    server.add_server(request.form["url"])
    return ui.UI.servers(server.servers, "browse", "add_server", "remove_server")


@server.client.route("/remove_server", methods=["POST"])
def remove_server():
    """Removes a server from the server list. Returns to the server browser page.
    
    Returns:
        A string containing HTML.
    """
    server.remove_server(request.form["server"])
    return ui.UI.servers(server.servers, "browse", "add_server", "remove_servers")


@server.client.route("/login")
def login():
    """Triggers a dedicated login page.
    Returns:
        A string containing HTML
    """
    url : str = request.args["url"]
    return ui.UI.login(url, "store_auth")


@server.client.route("/store_auth")
def store_auth():
    # TODO: Not sure how to store this...
    return browse()


argparser = argparse.ArgumentParser()
argparser.add_argument(
    "--host",
    default="0.0.0.0",
    help="Address to bind to"
)
argparser.add_argument(
    "--port",
    type=int,
    default=8080,
    help="Port to listen on"
)
args = argparser.parse_args()
server.client.run(host=args.host, port=args.port)