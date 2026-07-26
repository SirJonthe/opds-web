from html import escape
from urllib.parse import urljoin, quote, urlparse, parse_qs
import opds

class HTMLWriter:

    @staticmethod
    def _render_link(path : str, text : str, url : str, server_id : str) -> str:
        return f'<h2><a href="/{path}?server={server_id}&url={url}">{escape(text)}</a></h2>'


    @staticmethod
    def _render_nav(navigation : dict[str, str], url : str, server_id : str) -> str:
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


    @staticmethod
    def servers(servers : dict[str, str], browse_path : str) -> str:
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
            html += [ HTMLWriter._render_link(browse_path, server_url, "/opds/v1.2/libraries", server_id) ]
        html += [
            "</ul>",
            "</body>",
            "</html>"
        ]
        return "\n".join(html)


    @staticmethod
    def browse(entries : list[opds.Entry], browse_path : str, view_path : str) -> str:
        pass


    @staticmethod
    def entry() -> str:
        pass