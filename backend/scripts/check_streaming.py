"""Check that assistant replies stream through a proxy (e.g. the Next.js /api rewrite)
instead of being buffered. Uses the REAL OpenRouter API (costs a fraction of a cent).

    uv run python -m scripts.check_streaming http://127.0.0.1:3000 [--email demo@example.com --password ...]

Prints when each server-sent event arrives. A buffered proxy delivers them all at the end.
"""

import argparse
import json
import sys
import time

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m scripts.check_streaming")
    parser.add_argument("base_url", help="frontend origin, e.g. http://127.0.0.1:3000")
    parser.add_argument("--email", default="demo@example.com")
    parser.add_argument("--password", default="demo-password-123")
    parser.add_argument(
        "--message", default="Give me three short tips to spend less on transport this month, using my data."
    )
    args = parser.parse_args()

    api = args.base_url.rstrip("/") + "/api/v1"
    with httpx.Client(timeout=120, headers={"Accept-Encoding": "gzip, deflate, br"}) as client:
        login = client.post(f"{api}/auth/login", json={"email": args.email, "password": args.password})
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        client.put(f"{api}/assistant/settings", json={"enabled": True}, headers=headers).raise_for_status()

        start = time.monotonic()
        arrivals: list[tuple[float, str]] = []
        with client.stream("POST", f"{api}/assistant/chat", json={"message": args.message}, headers=headers) as res:
            print(
                f"status {res.status_code} | content-type {res.headers.get('content-type')} | "
                f"content-encoding {res.headers.get('content-encoding')} | cache-control {res.headers.get('cache-control')}"
            )
            if res.status_code != 200:
                print(res.read().decode())
                return 1
            for line in res.iter_lines():
                if line.startswith("event: "):
                    arrivals.append((time.monotonic() - start, line[7:]))
                elif line.startswith("data: ") and arrivals and arrivals[-1][1] in ("status", "error", "done"):
                    data = json.loads(line[6:])
                    print(
                        f"  {arrivals[-1][0]:6.2f}s  {arrivals[-1][1]:<8} {json.dumps(data, ensure_ascii=False)[:90]}"
                    )

    tokens = [t for t, e in arrivals if e == "token"]
    if not tokens:
        print("no token events received")
        return 1
    spread = tokens[-1] - tokens[0]
    print(f"{len(tokens)} token events; first at {tokens[0]:.2f}s, last at {tokens[-1]:.2f}s (spread {spread:.2f}s)")
    streamed = len(tokens) > 3 and spread > 0.5
    print("RESULT:", "STREAMING (events arrive incrementally)" if streamed else "BUFFERED? (events arrived together)")
    return 0 if streamed else 1


if __name__ == "__main__":
    sys.exit(main())
