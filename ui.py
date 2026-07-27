from html import escape
from urllib.parse import urljoin, quote, urlparse, parse_qs
import opds

class UI:


    @staticmethod
    def _tag(tag : str, param : str, content : str) -> str:
        if param is None or param == "":
            return f'<{tag}>{content}</{tag}>'
        return f'<{tag} {param}>{content}</{tag}>'


    @staticmethod
    def _page(content : str) -> str:
        return f'<!DOCTYPE html>{UI._tag("html", "", UI._tag("head", "", UI._tag("title", "", "opds-web")) + UI._tag("body", "", content))}'


    @staticmethod
    def _render_link(path : str, text : str, url : str, server_id : str) -> str:
        return f'<h2><a href="/{path}?server={server_id}&url={url}">{escape(text)}</a></h2>'


    @staticmethod
    def _render_authors(authors : list[str]) -> str:
        out : str = ""
        i : int = 0
        for author in authors:
            if i > 0:
                out += ", "
            out += author
            i = i + 1
        return out


    @staticmethod
    def _render_server_list(servers : dict[str, str], browse_path : str) -> str:
        out : str = ""
        for server_id, server_url in servers.items():
            out += UI._tag(
                "td", "",
                UI._render_link(browse_path, server_url, "/opds/v1.2/libraries", server_id)
            )
            out += UI._tag(
                "td", "align=\"right\"",
                UI._tag(
                    "form", "action=\"remove_server\" method=\"post\"",
                    f'<input type="hidden" name="server" value="{server_id}">'
                    '<input type="submit" value="Remove">'
                )
            )
        return out


    @staticmethod
    def _render_servers(servers : dict[str, str], browse_path : str) -> str:
        return UI._tag(
            "table", "width=\"100%\"",
            UI._tag(
                "tr", "",
                UI._render_server_list(servers, browse_path)
            )
        )


#    @staticmethod
#    def _render_nav(navigation : dict[str, str], url : str, server_id : str, browse_path : str) -> str:
#        html : list[str] = []
#        if "previous" in navigation or "next" in navigation:
#            if "previous" in navigation:
#                html.append(
#                    f'<a href="/{browse_path}?server={server_id}&url={quote(navigation["previous"])}">'
#                    "<   </a>"
#                )
#            else:
#                html.append("<   ")
#            html.append(" | ")
#            parsed_url = urlparse(url)
#            url_params = parse_qs(parsed_url.query)
#            page = url_params.get("page", ["0"])[0]
#            html.append(str(int(page) + 1))
#            html.append(" | ")
#            if "next" in navigation:
#                html.append(
#                    f'<a href="/{browse_path}?server={server_id}&url={quote(navigation["next"])}">'
#                    "   ></a>"
#                )
#            else:
#                html.append("   >")
#        return "\n".join(html)


    @staticmethod
    def _render_nav_previous(links : dict[str, str]) -> str:
        if "previous" in links:
            return UI._tag("a", "href=", "<   ")
        return "<   "


    @staticmethod
    def _render_nav_next(links : dict[str, str]) -> str:
        if "next" in links:
            return UI._tag("a", "href=", "   >")
        return "   >"
    

    @staticmethod
    def _render_nav(links : dict[str, str]) -> str:
        if "previous" in links or "next" in links:
            return UI._render_nav_previous(links) + " | " + " | " + UI._render_nav_next(links)
        return ""


    @staticmethod
    def _render_entries(entries : dict[str, opds.Entry], browse_path : str, view_path : str) -> str:
        out : str = ""
        for entry_id in entries:
            entry : opds.Entry = entries[entry_id]
            if entry.is_file():
                out += UI._tag(
                    "h2", "",
                    UI._tag("a", f'href={view_path}?url={entry.links["http://opds-spec.org/acquisition"]}', escape(entry.title))
                )
            else:
                out += UI._tag(
                    "h2", "",
                    UI._tag("a", f'href={browse_path}?url={entry.links["subsection"]}', escape(entry.title))
                )
        return out


    @staticmethod
    def servers(servers : dict[str, str], browse_path : str, add_server_path : str) -> str:
        return UI._page(
            UI._tag(
                "table", "width=\"100%\"",
                UI._tag(
                    "tr", "",
                    UI._tag(
                        "td", "valign=\"top\"",
                        UI._tag("h1", "", escape("Server browser"))
                    ) +
                    UI._tag(
                        "td", "align=\"right\"",
                        UI._tag(
                            "details", "",
                            UI._tag(
                                "summary", "",
                                UI._tag("h1", "", "(+)")
                            ) + UI._tag(
                                "form", f'action="/{add_server_path}" method="post"',
                                "<input type=\"text\" name=\"url\" placeholder=\"protocol://host:port/opds_path\">"
                                "<input type=\"submit\" value=\"Add\">"
                                )
                        )
                    )
                )
            ) +
            UI._tag(
                "ul", "",
                UI._render_servers(servers, browse_path)
            )
        )


    @staticmethod
    def browse(page_title : str, entries : dict[str, opds.Entry], links : dict[str, str], browse_path : str, view_path : str) -> str:
        return UI._page(
            UI._tag(
                "table", "width=\"100%\"",
                UI._tag(
                    "tr", "",
                    UI._tag(
                        "td", "valign=\"top\"",
                        UI._tag("h1", "", escape(page_title))
                    ) + UI._tag(
                        "td", "align=\"right\"",
                        UI._tag("h1", "", UI._render_nav(links))
                    )
                )
            ) +
            UI._tag(
                "ul", "",
                UI._render_entries(entries, browse_path, view_path)
            )
        )


    @staticmethod
    def entry(entry : opds.Entry, thumbnail_path : str, download_path : str) -> str:
        return UI._page(
            UI._tag("h1", "", entry.title) +
            UI._render_authors(entry.authors) +
            UI._render_link(download_path, "Download", entry.links["http://opds-spec.org/acquisition"], "") +
            UI._render_thumbnail(thumbnail_path, entry.links["http://opds-spec.org/image/thumbnail"]) +
            entry.description
        )