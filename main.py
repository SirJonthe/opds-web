"""OPDS web client entry point."""

from flask import Response, request, redirect, send_file, after_this_request
import os
import tempfile
import subprocess
import requests
import app
import argparse
import ui
from urllib.parse import urlencode
import json


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
    entry = reader.entries.get(request.args["entry"], None) or reader.entries["Publications"].entries[request.args["entry"]]
    server.refresh_convert_tools()
    return ui.UI.entry(entry, "thumbnail", "download", server.calibre is not None)


@server.client.route("/download", methods=["GET", "POST"])
def download():
    """The download request.
    
    Returns:
        An HTTP response.
    """
    if request.method == "GET":
        filename : str = request.args["file"]
        data = json.loads(request.args["src"])
        url : str = data["url"]
        ext : str = data["ext"]
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
                "Content-Disposition": f'attachment, filename="{filename}.{ext}"'
            }
        )
    else:
        # POST: conversion download
        data = json.loads(request.form["src"])
        print(data)
        url : str = data["url"]
        native_format : str = data["ext"]
        print(url)
        print(native_format)
        filename : str = request.form["file"]
        output_format : str = request.form.get("dst", None)
        if output_format in [None, ""]:
            return redirect(f"/download?{urlencode({"src" : request.form["src"], "file" : filename})}")
        else:
            output_format = output_format.lower()

        credentials = server.get_credentials(
            url,
            ui.UI.login(url, request.url, "store_auth")
        )
        if isinstance(credentials, Response):
            return credentials

        username, password = credentials

        # Download original file
        with tempfile.NamedTemporaryFile(
            suffix=f".{native_format}",
            delete=False
        ) as input_file:
            input_path = input_file.name

            r = requests.get(
                url,
                auth=(username, password),
                stream=True
            )
            r.raise_for_status()

            for chunk in r.iter_content(chunk_size=8192):
                input_file.write(chunk)

        if server.calibre is None:
            return Response(
                "Conversion unavailable",
                status=503
            )
        else:
            output_file = tempfile.NamedTemporaryFile(
                suffix=f".{output_format}",
                delete=False
            )
            output_path = output_file.name
            output_file.close()

            subprocess.run(
                [
                    server.calibre,
                    input_path,
                    output_path
                ],
                check=True
            )

        @after_this_request
        def cleanup(response):
            try:
                os.remove(input_path)
            except FileNotFoundError:
                pass

            if output_path != input_path:
                try:
                    os.remove(output_path)
                except FileNotFoundError:
                    pass

            return response

        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"{filename}.{output_format}"
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