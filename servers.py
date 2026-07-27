import hashlib


SERVER_FILE = "servers.txt"


def server_id(url : str):
    return hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()[:12]


def load_servers() -> dict[str, str]:
    srv = {}
    try:
        with open(SERVER_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip().rstrip("/").lower()
                if not line or line.startswith("#"):
                    continue
                srv[server_id(line)] = line
    except FileNotFoundError:
        pass
    return srv


def save_servers(servers : dict[str, str]):
    with open(SERVER_FILE, "w") as f:
        f.write("#[protocol]://[hostname]:[port]/[opds_url]\n")
        for _, url in servers.items():
            f.write(f'{url}\n')


def add_server(url : str, servers : dict[str, str]):
    servers[server_id(url)] = url.strip().rstrip("/").lower()
    save_servers(servers)


def remove_server(server_id : str, servers : dict[str, str]):
    del servers[server_id]
    save_servers(servers)