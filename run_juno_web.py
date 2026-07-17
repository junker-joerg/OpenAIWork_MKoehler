"""Start the compact local Hyperion web UI outside a notebook."""

from __future__ import annotations

import argparse

from juno_webapp import start_juno_webserver, stop_juno_webserver


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the Hyperion Juno web UI")
    parser.add_argument("--port", type=int, default=5006)
    parser.add_argument("--address", default="127.0.0.1")
    args = parser.parse_args()
    server, url = start_juno_webserver(port=args.port, address=args.address)
    print(f"Hyperion Web-UI: {url}")
    print("Zum Beenden Strg+C druecken.")
    try:
        server.thread.join()
    except KeyboardInterrupt:
        stop_juno_webserver(server)


if __name__ == "__main__":
    main()
