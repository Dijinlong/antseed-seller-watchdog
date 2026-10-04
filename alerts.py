#!/usr/bin/env python3
"""
alerts.py - send a short alert somewhere you will actually see it.

A watchdog that only prints to a terminal nobody is watching is not a watchdog.
This sends the message to a webhook (Slack, Discord, or your own endpoint) and
always echoes it to stdout so it shows up in cron mail too.

Usage
-----
    python alerts.py --webhook https://hooks.example/xxx --text "seller node is invisible"
    python alerts.py --text "just print it"

    # read the message from stdin
    python watchdog.py --metadata-url ... | python alerts.py --webhook https://...

Environment
-----------
    ALERT_WEBHOOK_URL   used when --webhook is omitted

Exit codes
----------
    0  delivered (or printed)
    2  delivery failed
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def post_json(url, payload, timeout=15):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST"
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "antseed-alerts")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:200]
    except Exception as e:
        return 0, str(e)


def build_payload(url, text):
    """Slack and Discord both accept a plain {"text": ...} body."""
    if "discord" in url:
        return {"content": text}
    return {"text": text}


def main():
    ap = argparse.ArgumentParser(description="Send an alert to a webhook.")
    ap.add_argument("--webhook", default=os.environ.get("ALERT_WEBHOOK_URL", ""))
    ap.add_argument("--text", default=None, help="message; reads stdin when omitted")
    ap.add_argument("--prefix", default="[antseed]", help="prefix added to the message")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    text = args.text if args.text is not None else sys.stdin.read().strip()
    if not text:
        print("nothing to send", file=sys.stderr)
        return 2

    message = "%s %s" % (args.prefix, text)
    if not args.quiet:
        print(message)

    if not args.webhook:
        return 0

    status, body = post_json(args.webhook, build_payload(args.webhook, message))
    if status and 200 <= status < 300:
        return 0

    print("webhook delivery failed (status=%s): %s" % (status, body), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
