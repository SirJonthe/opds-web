"""OPDS web client entry point."""

from flask import Response, request, redirect
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
    return ui.UI.servers(server.servers, "browse", "add_server", "remove_server")


@server.client.route("/browse")
def browse():
    """The directory browser page.
    
    Returns:
        A string containing HTML.
    """
    url : str = request.args["url"]
    reader = server.get_feed_reader(url, ui.UI.login(url, request.url, "store_auth"))
    if isinstance(reader, Response):
        return reader
    return ui.UI.browse(reader.title, reader.entries, reader.links, url, "browse", "view")


@server.client.route("/view")
def entry():
    """The file entry page.
    
    Returns:
        A string containing HTML.
    """
    url : str = request.args["url"]
    reader = server.get_feed_reader(url, ui.UI.login(url, request.url, "store_auth"))
    if isinstance(reader, Response):
        return reader
    entry = reader.entries[request.args["entry"]]
    return ui.UI.entry(entry, "thumbnail", "download", False)


@server.client.route("/download")
def download():
    """The download request.
    
    Returns:
        An HTTP response.
    """
    url : str = request.args["url"]
    credentials = server.get_credentials(url, ui.UI.login(url, request.url, "store_auth"))
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
    credentials = server.get_credentials(url, ui.UI.login(url, request.url, "store_auth"))
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


@server.client.route("/store_auth", methods=["POST"])
def store_auth():
    """Triggers storage of manually input user credentials then goes to the next specified URL.

    Returns:
        A string containing HTML.
    """
    url : str = request.form["url"]
    next_url : str = request.form["next"]
    base_url : str = app.App._get_base_server_url(url)
    server.store_in_session(f'{base_url}:username', request.form["username"] if "username" in request.form else None)
    server.store_in_session(f'{base_url}:password', request.form["password"] if "password" in request.form else None)
    return redirect(next_url)


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