from flask import Response, request
import requests
import app
import argparse
import ui


server = app.App()


@server.client.route("/")
def index():
   return ui.UI.servers(server.servers, "browse", "add_server")


@server.client.route("/browse")
def browse():
    url : str = request.args["url"]
    reader = server.get_feed_reader(url)
    if isinstance(reader, Response):
        return reader
    return ui.UI.browse(reader.title, reader.entries, reader.links, url, "browse", "view")


@server.client.route("/view")
def entry():
    reader = server.get_feed_reader(request.args["url"])
    if isinstance(reader, Response):
        return reader
    entry = reader.entries[request.args["entry"]]
    return ui.UI.entry(entry, "thumbnail", "download")


@server.client.route("/download")
def download():
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
    server.add_server(request.form["url"])
    return ui.UI.servers(server.servers, "browse", "add_server")


@server.client.route("/remove_server", methods=["POST"])
def remove_server():
    server.remove_server(request.form["server"])
    return ui.UI.servers(server.servers, "browse", "add_server")


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