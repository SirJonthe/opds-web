"""HTML OPDS UI construction tools."""

from html import escape
from urllib.parse import quote, urlparse, parse_qs, urlencode
import opds
import os
import mimetypes
import hashlib
import json

class UI:
    """A UI singleton designed to generate navigable HTML for OPDS feeds."""

    class Extension:
        ext : str
        url : str | None

        def __init__(self, ext : str, url : str | None):
            self.ext = ext
            self.url = url

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
        return f'<h2><a href="/{path}?{urlencode({"url":url})}">{escape(text)}</a></h2>'


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
    def _render_nav_previous(links : dict[str, list[opds.Link]], browse_path : str) -> str:
        """Generates the Previous button to navigate to a previous page.

        Args:
            links: A dictionary of links containing a "previous" key.
            browse_path: The internal path to trigger when clicking a directory.
        
        Returns:
            Generated HTML string.
        """
        if "previous" in links:
            return UI._tag("a", f'href=/{browse_path}?{urlencode({"url":links["previous"][0].url})}', "<   ")
        return "<   "


    @staticmethod
    def _render_nav_next(links : dict[str, list[opds.Link]], browse_path : str) -> str:
        """Generates the Next button to navigate to a next page.

        Args:
            links: A dictionary of links containing a "next" key.
            browse_path: The internal path to trigger when clicking a directory.
        
        Returns:
            Generated HTML string.
        """
        if "next" in links:
            return UI._tag("a", f'href=/{browse_path}?{urlencode({"url":links["next"][0].url})}', "   >")
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
    def _render_nav(links : dict[str, list[opds.Link]], url : str, browse_path : str) -> str:
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
            entry : opds.Entry | opds.Reader = entries[entry_id]

            if isinstance(entry, opds.Entry):
                if entry.is_file():
                    out += UI._tag(
                        "h2", "",
                        UI._tag("a", f'href={view_path}?{urlencode({"entry":entry.id, "url":url})}', escape(entry.title))
                    )
                else:
                    out += UI._tag(
                        "h2", "",
                        UI._tag("a", f'href={browse_path}?{urlencode({"url":entry.subsection_url().url})}', escape(entry.title))
                    )
            elif isinstance(entry, opds.Reader):
                out += UI._tag("h2", "", entry.title) + UI._render_entries(entry.entries, url, browse_path, view_path)
        return out


    @staticmethod
    def _generate_download_filename(entry : opds.Entry) -> str:
        """Generates a relatively unique download name based off of the authors and title.

        Args:
            entry: The file entry to display.
        
        Returns:
            Generated HTML string.
        """
        base = ", ".join(entry.authors) + " - " + entry.title
        return hashlib.sha256(
            base.encode("utf-8")
        ).hexdigest()[:12]

    @staticmethod
    def _render_native_format_options(formats : list[Extension]) -> str:
        """Adds source formats to a drop-down list.

        Args:
            formats: A list of source formats to display in a drop-down list.
        
        Returns:
            Generated HTML string.
        """
        out : str = ""
        i : int = 0
        for fmt in formats:
            if fmt.url is not None:
                value = json.dumps(
                    {
                        "url": fmt.url,
                        "ext": fmt.ext.lower()
                    }
                )
                if i > 0:
                    out += UI._tag(
                        "option", f'value="{escape(value)}"',
                        fmt.ext.upper()
                    )
                else:
                    out += UI._tag(
                        "option", f'value="{escape(value)}" selected',
                        fmt.ext.upper()
                    )
                i += 1
        return out


    @staticmethod
    def _render_conversion_format_options(formats : list[Extension]) -> str:
        """Adds destination formats to a drop-down list.
        
        Args:
            formats: A list of destination formats to display in a drop-down list.
        
        Returns:
            Generated HTML string.
        """
        out : str = UI._tag("option", f'value="" selected', "No conversion")
        for format in formats:
            if format.url is None:
                out += UI._tag(
                    "option", f'value="{format.ext}"',
                    format.ext.upper()
                )
        return out


    @staticmethod
    def _render_download(entry : opds.Entry, download_path : str, format_picker : bool) -> str:
        """Renders the download link and/or the download format picker.

        Args:
            download_path: The internal path to trigger when requesting a download.
            download_url: The URL of the content to download.
            format_picker: Show the format picker for transcoding.
        
        Returns:
            Generated HTML string.
        """
        download_urls : opds.Link = entry.download_urls()
        formats : dict[str, UI.Extension] = {}
        if format_picker:
            formats["epub"]  = UI.Extension("epub",  None)
            formats["mobi"]  = UI.Extension("mobi",  None)
            formats["azw"]   = UI.Extension("azw",   None)
            formats["azw3"]  = UI.Extension("azw3",  None)
            formats["kepub"] = UI.Extension("kepub", None) # TODO: Kobo devices require .kepub files to be named FILE.kepub.epub
        for dl in download_urls:
            ext : str = ""
            if dl.mime == None:
                path : str = urlparse(dl.url).path
                ext = os.path.splitext(path)[1].lstrip(".").lower()
            else:
                ext = (mimetypes.guess_extension(dl.mime) or "").lstrip(".").lower()
            formats[ext] = UI.Extension(ext, dl.url)
        return UI._tag(
            "form", f'action="/{download_path}" method="post"',
            f'<input type="hidden" name="file" value="{UI._generate_download_filename(entry)}">' +
            (
                UI._tag(
                    "select", 'name="src"',
                    UI._render_native_format_options(formats.values())
                ) +
                " " +
                (
                    UI._tag(
                    "select", 'name="dst"',
                    UI._render_conversion_format_options(formats.values())
                ) if format_picker else "") +
                ' <input type="submit" value="Download">'
            ) if download_urls is not None else ""
        )


    @staticmethod
    def _render_thumbnail(thumbnail_path : str, thumbnail_url : str):
        """Generates a thumbnail image.
        
        Args:
            thumbnail_path: The internal path to trigger when requesting a thumbnail.
            thumbnail_url: The URL of the thumbnail image.

        Returns:
            Generated HTML string.
        """
        return f'<img align="left" width="200" src="/{thumbnail_path}?{urlencode({"url":thumbnail_url})}">'


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
    def browse(page_title : str, entries : dict[str, opds.Entry], links : dict[str, list[opds.Link]], url : str, browse_path : str, view_path : str) -> str:
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
    def entry(entry : opds.Entry, thumbnail_path : str, download_path : str, format_picker : bool) -> str:
        """File entry view page.

        Args:
            entry: The file entry to display.
            thumbnail_path: The internal path to trigger when requesting a thumbnail.
            download_path: The internal path to trigger when requesting a download.
            format_picker: Show the format picker for transcoding.

        Returns:
            Generated HTML string.
        """
        thumb = entry.thumbnail_urls()
        return UI._page(
            UI._tag("h1", "", entry.title) +
            ", ".join(entry.authors) +
            UI._render_download(entry, download_path, format_picker) +
            UI._render_thumbnail(thumbnail_path, thumb[0].url if thumb is not None else "") +
            entry.description
        )

    @staticmethod
    def login(url : str, resume_url : str, store_auth_path : str) -> str:
        """A login page.

        Args:
            url: The URL to provide the login for.
            resume_url: The internal path to trigger after landing on the store_auth_path.
            store_auth_path: The internal path to trigger when requesting to store credentials.
        
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
                f'<input type="hidden" name="url" value="{escape(url)}">'
                f'<input type="hidden" name="next" value="{escape(resume_url)}">' +
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