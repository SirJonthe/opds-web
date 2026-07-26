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


NS = {
    "atom": "http://www.w3.org/2005/Atom"
}


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


def get_feed(path : str, server_id : str) -> str:
    credentials = get_credentials(server_id)
    if isinstance(credentials, Response):
        return credentials
    username, password = credentials
    r = requests.get(
        urljoin(app.servers[server_id], path),
        auth=(username, password)
    )
    r.raise_for_status()
    print(r.headers.get("Content-Type", ""))
    return r.text


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


def render_nav_small(navigation : dict[str, str], url : str, server_id : str) -> str:
    html = list[str] = []
    if "previous" in navigation or "next" in navigation:
        if "previous" in navigation:
            html.append(
                f'<a href="/browse?server={server_id}&url={quote(navigation["previous"])}">'
                "< Previous</a>"
            )
        else:
            html.append("< Previous")
        html.append(" | ")
        parsed_url = urlparse(url)
        url_params = parse_qs(parsed_url.query)
        page = url_params.get("page", ["0"])[0]
        html.append(str(int(page) + 1))
        html.append(" | ")
        if "next" in navigation:
            html.append(
                f'<a href="/browse?server={server_id}&url={quote(navigation["next"])}">'
                "Next ></a>"
            )
        else:
            html.append("Next >")
    return "\n".join(html)


def render_nav(navigation : dict[str, str], url : str, server_id : str) -> str:
    html : list[str] = []
    if "previous" in navigation or "next" in navigation:
        if "previous" in navigation:
            html.append(
                f'<a href="/browse?server={server_id}&url={quote(navigation["previous"])}">'
                "<   </a>"
            )
        else:
            html.append("<   ")
        html.append(" | ")
        parsed_url = urlparse(url)
        url_params = parse_qs(parsed_url.query)
        page = url_params.get("page", ["0"])[0]
        html.append(str(int(page) + 1))
        html.append(" | ")
        if "next" in navigation:
            html.append(
                f'<a href="/browse?server={server_id}&url={quote(navigation["next"])}">'
                "   ></a>"
            )
        else:
            html.append("   >")
    return "\n".join(html)


def render_link(mode : str, html : list[str], text : str, url : str, server_id : str):
    html.append(
        f'<h2><a href="/{mode}?server={server_id}&url={url}">'
        f'{escape(text)}</a></h2>'
    )


def render_browse_link(html : list[str], text : str, url : str, server_id : str):
    render_link("browse", html, text, url, server_id)


def render_download_link(html : list[str], text : str, url : str, server_id : str):
    render_link("download", html, text, url, server_id)


def render_view_link(html : list[str], text : str, url : str, server_id : str, entry_id : str):
    html.append(
            f'<h2><a href="/view?server={server_id}&entry={entry_id}&url={url}">'
            f'{escape(text)}</a></h2>'
        )


def render_entry(xml : str, server_id : str, entry_id : str):
    root = ET.fromstring(xml)
    for entry in root.findall("atom:entry", NS):
        eid : str = entry.find("atom:id", NS).text
        if eid == None or eid != entry_id:
            continue
        name = entry.find("atom:title", NS).text

        html = [
            "<html>",
            "<body>",
            f"<h1>{escape(name)}</h1>",
            "<ul>"
        ]

        
        links : dict[str, str] = {}
        for link in entry.findall("atom:link", NS):
            links[link.attrib.get("rel")] = link.attrib.get("href")

        html += [ "<p>" ]
        num_names : int = 0
        html += [""]
        for author in entry.findall("atom:author", NS):
            for name in author.findall("atom:name", NS):
                if num_names > 0:
                    html[-1] += "; "
                html[-1] += name.text
                num_names = num_names + 1
        html += [ "</p>" ]

        html += [ "<p>" ]
        for rel, href in links.items():
            if "acquisition" in rel:
                render_download_link(html, "Download", urljoin(app.servers[server_id], href), server_id)
                break

        for rel, href in links.items():
            if "thumbnail" in rel:
                html += [
                    f'<img align="left" src="/thumbnail?server={server_id}&url={quote(href)}">'
                ]
                break

        description = entry.find("atom:content", NS).text
        html += [
            description,
            "</p>",
            "</ul>",
            "</body>",
            "</html>"
        ]
        return "\n".join(html)
    return "<p>Title missing</p>"


def render_opds(xml : str, url : str, server_id : str) -> str:
    root = ET.fromstring(xml)
    navigation = {}
    for link in root.findall("atom:link", NS):
        rel = link.attrib.get("rel")
        href = link.attrib.get("href")
        if rel:
            navigation[rel] = href
    title = root.find("atom:title", NS).text
    nav_html = render_nav(navigation, url, server_id)
    html = [
        "<html>",
        "<body>",
        "<table width=\"100%\">",
        "<tr>",
        "<td valign=\"top\">",
        f"<h1>{escape(title)}</h1>",
        "</td>",
        "<td align=\"right\">"
        f"<h1>{nav_html}</h1>",
        "</td>",
        "</tr>",
        "</table>",
        "<ul>"
    ]
    for entry in root.findall("atom:entry", NS):
        name = entry.find("atom:title", NS).text
        for link in entry.findall("atom:link", NS):
            rel = link.attrib.get("rel")
            href = link.attrib.get("href")
            if rel == "subsection":
                render_browse_link(html, name, href, server_id)
            elif rel and "acquisition" in rel:
                entry_id : str = entry.find("atom:id", NS).text
                render_view_link(html, name, url, server_id, entry_id)
    html += [
        f'<h1 align="right">{nav_html}</h1>',
        "</ul>",
        "</body>",
        "</html>"
    ]
    return "\n".join(html)


def render_server_browser(servers : dict[str, str]):
    html : list[str] = [
        "<html>",
        "<body>",
        "<table width=\"100%\">",
        "<tr>",
        "<td valign=\"top\">",
        f"<h1>{escape("Server browser")}</h1>",
        "</td>",
        "<td align=\"right\">",
        "<details>",
        "<summary><h1>(+)</h1></summary>",
        "<form action=\"/add_server\" method=\"post\">",
            "<input ",
                "type=\"text\"",
                "name=\"url\"",
                "placeholder=\"http://host:port\">",
            "<input type=\"submit\" value=\"Add\">",
        "</form>",
        "</details>",
        "</td>",
        "<tr>",
        "</table>",
        "<ul>"
    ]
    for (server_id, server_url) in servers.items():
        render_browse_link(html, server_url, "/opds/v1.2/libraries", server_id)
    html += [
        "</ul>",
        "</body>",
        "</html>"
    ]
    return "\n".join(html)


def browse_servers(servers : dict[str, str]) -> str:
    return render_server_browser(servers)


def browse_url(url : str, server_id : str) -> str:
    xml = get_feed(url, server_id)
    if isinstance(xml, Response):
        return xml
    return render_opds(xml, url, server_id)


def view_entry(url : str, server_id : str, entry_id : str):
    xml = get_feed(url, server_id)
    if isinstance(xml, Response):
        return xml
    return render_entry(xml, server_id, entry_id)


@app.client.route("/")
def index():
    return browse_servers(app.servers)


@app.client.route("/browse")
def browse():
    return browse_url(request.args["url"], request.args["server"])


@app.client.route("/view")
def view():
    return view_entry(request.args["url"], request.args["server"], request.args["entry"])


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