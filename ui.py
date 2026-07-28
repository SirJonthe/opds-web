"""HTML OPDS UI construction tools."""

from html import escape
from urllib.parse import quote, urlparse, parse_qs
import opds

class UI:
    """A UI singleton designed to generate navigable HTML for OPDS feeds."""

    @staticmethod
    def _tag(tag : str, param : str, content : str) -> str:
        """Starts and automatically closes a tag.

        Args:
            tag: The name of the HTML tag, e.g. "h1", "table", etc.
            param: The tag parameters as a string.
            content: The content between the tags.
        
        Returns:
            Generated HTML string.
        """
        if param is None or param == "":
            return f'<{tag}>{content}</{tag}>'
        return f'<{tag} {param}>{content}</{tag}>'


    @staticmethod
    def _page(content : str) -> str:
        """Generates basic boiler-plate HTML for a page
        
        Args:
            content: The content to be presented within the page body.
        
        Returns:
            Generated HTML string.
        """
        return f'<!DOCTYPE html>{UI._tag("html", "", UI._tag("head", "", '<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">' + UI._tag("title", "", "opds-web")) + UI._tag("body", "", content))}'


    @staticmethod
    def _render_link(path : str, text : str, url : str) -> str:
        """Generates a clickable link with a pre-defined formatting.

        Args:
            path: The path the link should point to.
            text: The presented text.
            url: The URL parameter passed to the path.
        
        Returns:
            Generated HTML string.
        """
        if url is None or url == "":
            return ""
        return f'<h2><a href="/{path}?url={quote(url)}">{escape(text)}</a></h2>'


    @staticmethod
    def _render_server_list(servers : dict[str, str], browse_path : str, remove_server_path : str) -> str:
        """Generates server list table entries with functioning remove server buttons.
        
        Args:
            servers: A dictionary of server URL:s by server ID key.
            browse_path: The internal path to trigger when clicking a server.
            remove_server_path: The internal path to trigger when clicking to remove a server.
        
        Returns:
            Generated HTML string.
        """
        out : str = ""
        for server_id, server_url in servers.items():
            out += UI._tag(
                "tr", "",
                UI._tag(
                    "td", "",
                    UI._render_link(browse_path, server_url, server_url)
                ) +
                UI._tag(
                    "td", "align=\"right\"",
                    UI._tag(
                        "form", f'action="{remove_server_path}" method="post"',
                        f'<input type="hidden" name="server" value="{server_id}">'
                        '<input type="submit" value="Remove">'
                    )
                )
            )
        return out


    @staticmethod
    def _render_servers(servers : dict[str, str], browse_path : str, remove_server_path : str) -> str:
        """Generates a server list table with functioning remove server buttons.
        
        Args:
            servers: A dictionary of server URL:s by server ID key.
            browse_path: The internal path to trigger when clicking a server.
            remove_server_path: The internal path to trigger when clicking to remove a server.
        
        Returns:
            Generated HTML string.
        """
        return UI._tag(
            "table", "width=\"100%\"",
            UI._render_server_list(servers, browse_path, remove_server_path)
        )


    @staticmethod
    def _render_nav_previous(links : dict[str, str], browse_path : str) -> str:
        """Generates the Previous button to navigate to a previous page.

        Args:
            links: A dictionary of links containing a "previous" key.
            browse_path: The internal path to trigger when clicking a directory.
        
        Returns:
            Generated HTML string.
        """
        if "previous" in links:
            return UI._tag("a", f'href=/{browse_path}?url={quote(links["previous"])}', "<   ")
        return "<   "


    @staticmethod
    def _render_nav_next(links : dict[str, str], browse_path : str) -> str:
        """Generates the Next button to navigate to a next page.

        Args:
            links: A dictionary of links containing a "next" key.
            browse_path: The internal path to trigger when clicking a directory.
        
        Returns:
            Generated HTML string.
        """
        if "next" in links:
            return UI._tag("a", f'href=/{browse_path}?url={quote(links["next"])}', "   >")
        return "   >"


    @staticmethod
    def _render_page(url : str) -> str:
        """Generates the page number from the "page" parameter in the input URL.

        Args:
            url: A URL containing a "page" parameter.
        
        Returns:
            Generated HTML string.
        """
        parsed_url = urlparse(url)
        url_params = parse_qs(parsed_url.query)
        page = url_params.get("page", ["0"])[0]
        return str(int(page) + 1)


    @staticmethod
    def _render_nav(links : dict[str, str], url : str, browse_path : str) -> str:
        """Generates Previous and Next navigation buttons. Grays them out when not available.

        Args:
            links: A dictionary of links containing a "next" key.
            url: A URL containing a "page" parameter.
            browse_path: The internal path to trigger when clicking a server.

        Returns:
            Generated HTML string.
        """
        if "previous" in links or "next" in links:
            return UI._render_nav_previous(links, browse_path) + " | " + UI._render_page(url) + " | " + UI._render_nav_next(links, browse_path)
        return ""


    @staticmethod
    def _render_entries(entries : dict[str, opds.Entry], url : str, browse_path : str, view_path : str) -> str:
        """Generates a list of directory or file entries.

        Args:
            entries: A dictionary of file/directory entries grouped by entry ID key.
            url: A URL containing a "page" parameter.
            browse_path: The internal path to trigger when clicking a directory.
            view_path: The internal path to trigger when clicking a file.

        Returns:
            Generated HTML string.
        """
        out : str = ""
        for entry_id in entries:
            entry : opds.Entry = entries[entry_id]
            if entry.is_file():
                out += UI._tag(
                    "h2", "",
                    UI._tag("a", f'href={view_path}?&entry={entry.id}&url={quote(url)}', escape(entry.title))
                )
            else:
                out += UI._tag(
                    "h2", "",
                    UI._tag("a", f'href={browse_path}?&url={quote(entry.subsection_url())}', escape(entry.title))
                )
        return out


    @staticmethod
    def _render_thumbnail(thumbnail_path : str, thumbnail_url : str):
        """Generates a thumbnail image.
        
        Args:
            thumbnail_path: The internal path to trigger when requesting a thumbnail.
            thumbnail_url: The URL of the thumbnail image.

        Returns:
            Generated HTML string.
        """
        return f'<img align="left" src="/{thumbnail_path}?url={quote(thumbnail_url)}">'


    @staticmethod
    def servers(servers : dict[str, str], browse_path : str, add_server_path : str, remove_server_path : str) -> str:
        """The main server browser page.

        Args:
            servers: A dictionary of server URL:s by server ID key.
            browse_path: The internal path to trigger when clicking a directory.
            add_server_path: The internal path to trigger when clicking "add server".
            remove_server_path: The internal path to trigger when clicking to remove a server.

        Returns:
            Generated HTML string.
        """
        return UI._page(
            UI._tag(
                "table", "width=\"100%\"",
                UI._tag(
                    "tr", "",
                    UI._tag(
                        "td", "valign=\"top\"",
                        UI._tag("h1", "", escape("Server Browser"))
                    ) +
                    UI._tag(
                        "td", "align=\"right\"",
                        UI._tag(
                            "h1", "",
                            UI._tag(
                                "details", "",
                                UI._tag(
                                    "summary", "",
                                    "(+)"
                                ) + UI._tag(
                                    "form", f'action="/{add_server_path}" method="post"',
                                    "<input type=\"text\" name=\"url\" placeholder=\"protocol://host:port/opds_path\">"
                                    "<input type=\"submit\" value=\"Add\">"
                                )
                            )
                        )
                    )
                )
            ) +
            UI._tag(
                "ul", "",
                UI._render_servers(servers, browse_path, remove_server_path)
            )
        )


    @staticmethod
    def browse(page_title : str, entries : dict[str, opds.Entry], links : dict[str, str], url : str, browse_path : str, view_path : str) -> str:
        """Directory browser page.
        
        Args:
            page_title: The heading of the page.
            entries: A dictionary of file/directory entries grouped by entry ID key.
            links: A dictionary of links for the entry.
            url: The URL of the current feed.
            browse_path: The internal path to trigger when clicking a directory.
            view_path: The internal path to trigger when clicking a file.

        Returns:
            Generated HTML string.
        """
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
                        UI._tag("h1", "", UI._render_nav(links, url, browse_path))
                    )
                )
            ) +
            UI._tag(
                "ul", "",
                UI._render_entries(entries, url, browse_path, view_path)
            ) +
            UI._tag(
                "h1", "align=\"right\"",
                UI._render_nav(links, url, browse_path)
            )
        )


    @staticmethod
    def entry(entry : opds.Entry, thumbnail_path : str, download_path : str) -> str:
        """File entry view page.

        Args:
            entry: The file entry to display.
            thumbnail_path: The internal path to trigger when requesting a thumbnail.
            download_path: The internal path to trigger when requesting a download.

        Returns:
            Generated HTML string.
        """
        return UI._page(
            UI._tag("h1", "", entry.title) +
            ", ".join(entry.authors) +
            UI._render_link(download_path, "Download", entry.download_url()) +
            UI._render_thumbnail(thumbnail_path, entry.thumbnail_url()) +
            entry.description
        )

    @staticmethod
    def login(url : str, store_auth_path : str, next_path : str) -> str:
        """A login page.

        Args:
            url: The URL to provide the login for.
            store_auth_path: The internal path to trigger when requesting to store credentials.
            next_path: The internal path to trigger after landing on the store_auth_path.
        
        Returns:
            Generated HTML string.
        """
        return UI._page(
            UI._tag(
                "h1", "",
                "Log In"
            ) +
            UI._tag(
                "form", f'action=/{store_auth_path} method="post"',
                '<input type="hidden" name="server" value="{escape(server)}">'
                f'<input type="hidden" name="next" value="/{next_path}?url={quote(url)}">' +
                UI._tag(
                    "p", "",
                    'Username:<br>'
                    '<input type="text" name="username">'
                ) +
                UI._tag(
                    "p", "",
                    'Password:<br>'
                    '<input type="password" name="password">'
                ) +
                '<input type="submit" value="Log in">'
            )
        )