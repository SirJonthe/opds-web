# opds-web

## About

A minimal web client for OPDS servers.

## Background

OPDS (Open Publication Distribution System) is an open standard which allows clients to browse catalogs of electronic publications hosted by OPDS servers. Many native reading applications for desktop and mobile have support for connecting to OPDS, but many e-ink devices such as Kindle and Kobo do not (presumably in order to lock users into their own preferred ecosystem for publications). For such devices, the only solutions have either been to jailbreak them and install third party software, or utilize some kind of web solution for the devices that offer a browser. Another complicating factor is older e-ink devices which do not offer much in the way of modern web browsers meaning that many web pages will fail to work - Even sleek self-hosted solutions like Komga.

`opds-web` is a deliberately minimal web client written in Python designed to connect to OPDS servers in order to download electronic publications. Most of the heavy-lifting happens server-side while the rendering is client-side. It does not offer any styling in order to maintain the absolute maximum level of compatibility with older devices and browsers. That means no CSS, and no Javascript!

`opds-web` helps you download content locally. The actual reading itself is meant to be done offline using the native reader software.

## Features

- OPDS 1.2 and 2.0 client
- Pure HTML (no CSS)
- No JavaScript
- Designed for maximum compatibility with older browsers and e-ink devices
- Minimal server-side implementation in Python

## Usage

`opds-web` needs to be deployed to a server - Probably a home server. It has a small set of requirements such as `python3` and the libraries as defined in `requirements.txt`. You must decide for yourself how you want this software to boot and what ports to listen to. If you intend to access the application from another device on your network you must also ensure that the chosen port is reachable.

Installing the requirements for the server includes installing the `python3` package (>= 3.9) by whatever means you deem fit. Then you can install the requirements using `pip3` (if available and if this is your preference) using:

```
pip3 install -r requirements.txt
```

Finally, you can boot the software using:
```
python3 main.py --host=0.0.0.0 --port=8080
```

Once deployed, you can boot your browser-enabled client device and browse to the URL given by the specified host and port. The first page allows you to add OPDS servers or browse already added OPDS servers. Clicking a server will prompt you for credentials for accessing the server when applicable. Once you have access you will be able to browse the digital OPDS catalog.

The page displaying individual titles for download also supports converting the currently offered format to a list of other formats if `calibre` (or more specifically `ebook-convert`) is installed. This may be necessary for old e-ink devices which may limit the formats that can be downloaded if the OPDS catalogs browsed are not already offering one of those formats.

# Future

- [ ] Debug against Project Gutenberg: https://www.gutenberg.org/ebooks/search.opds/ (uses relative URL:s so look into passing "server" parameter and use urljoin() again)
- [ ] Implement search
- [ ] Save files as [Author]-[Title].[Format] instead of however they are named on the server (take care that KEPUB files need the extension .kepub.epub).