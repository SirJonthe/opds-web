from flask import Response, Flask, request, abort
import base64
import requests
import xml.etree.ElementTree as ET
from html import escape
from urllib.parse import urljoin, quote, urlparse, parse_qs
import servers
import argparse
import opds1
import opds2
import html_writer


class App:
    client: Flask
    servers: dict[str, str]

    def __init__(self : App):
        self.client = Flask(__name__)
        self.servers = servers.load_servers()


app = App()


def get_credentials(server_id : str) -> tuple[str, str]:
    server = app.servers[server_id]
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


def get_feed_reader(path : str, server_id : str):
    credentials = get_credentials(server_id)
    if isinstance(credentials, Response):
        return credentials
    username, password = credentials
    r = requests.get(
        urljoin(app.servers[server_id], path),
        auth=(username, password)
    )
    r.raise_for_status()
    content_type = r.headers.get("Content-Type", "")
    if "atom" in content_type or "xml" in content_type:
        return opds1.ReaderV1(r.text)
    elif "json" in content_type:
        return opds2.ReaderV2(r.text)
    return None


@app.client.route("/")
def index():
   return html_writer.HTMLWriter.servers(app.servers, "browse")


@app.client.route("/browse")
def browse():
    return html_writer.HTMLWriter.browse()


@app.client.route("/entry")
def entry():
    return html_writer.HTMLWriter.entry()


@app.client.route("/download")
def download():
    url : str = request.args["url"]
    server_id : str = request.args["server"]
    credentials = get_credentials(server_id)
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


@app.client.route("/thumbnail")
def thumbnail():
    url : str = request.args["url"]
    server_id : str = request.args["server"]
    credentials = get_credentials(server_id)
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
app.client.run(host=args.host, port=args.port)