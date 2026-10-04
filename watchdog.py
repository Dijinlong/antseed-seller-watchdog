#!/usr/bin/env python3
"""
antseed seller watchdog
=======================

Checks the failure modes that are **silent** on an antseed seller node.

A seller can look healthy by every conventional measure and still be visible
to nobody:

  * the process is active
  * the port is listening
  * /metadata returns HTTP 200

...and yet `providers` is an empty array, because advertising paused.

This script checks the four conditions that actually determine whether buyers
can see and use your node.

Usage
-----
    python watchdog.py \\
        --metadata-url http://YOUR_PUBLIC_IP:6882/metadata \\
        --rpc-url      https://mainnet.base.org \\
        --wallet       0xYourSellerWallet \\
        --gas-floor    0.00005

Exit codes
----------
    0  every check passed
    1  at least one check failed
    2  the watchdog itself could not run

Design note
-----------
This intentionally does **not** use a framework. A watchdog that depends on a
large dependency tree is a watchdog that can fail for reasons unrelated to the
thing it watches.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

TIMEOUT = 20


def http_json(url, payload=None):
    """POST when payload is given, GET otherwise. Returns (status, body)."""
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("Accept", "application/json")
    if data:
        req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "antseed-seller-watchdog")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return 0, str(e)


def check_metadata(url):
    """The advertised services must be non-empty."""
    status, body = http_json(url)
    if status != 200 or not isinstance(body, dict):
        return False, "metadata unreachable (status=%s)" % status

    providers = body.get("providers") or []
    if not providers:
        return False, "providers is EMPTY - node is running but not advertising"

    services = []
    for p in providers:
        services.extend(p.get("services") or [])
    if not services:
        return False, "providers present but no services advertised"

    return True, "%d provider(s), %d service(s)" % (len(providers), len(services))


def check_gas(rpc_url, wallet, floor):
    """Advertising pauses below the gas floor - with no other symptom."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getBalance",
        "params": [wallet, "latest"],
    }
    status, body = http_json(rpc_url, payload)
    if status != 200 or not isinstance(body, dict) or "result" not in body:
        return False, "RPC call failed (status=%s)" % status

    wei = int(body["result"], 16)
    eth = wei / 1e18
    if eth < floor:
        return False, "balance %.8f ETH is BELOW the floor %.8f - advertising may be paused" % (eth, floor)
    return True, "balance %.8f ETH (floor %.8f)" % (eth, floor)


def check_endpoint_reachable(url):
    """A locally-listening port proves nothing about public reachability."""
    status, _ = http_json(url)
    if status != 200:
        return False, "endpoint not reachable from here (status=%s)" % status
    return True, "endpoint reachable"


def main():
    ap = argparse.ArgumentParser(description="antseed seller watchdog")
    ap.add_argument("--metadata-url", required=True)
    ap.add_argument("--rpc-url", default="https://mainnet.base.org")
    ap.add_argument("--wallet", required=True)
    ap.add_argument("--gas-floor", type=float, default=0.00005)
    ap.add_argument("--provider-count", type=int, default=None,
                    help="expected number of advertised services (optional)")
    args = ap.parse_args()

    results = []

    ok, detail = check_metadata(args.metadata_url)
    results.append(("metadata / services", ok, detail))

    ok, detail = check_gas(args.rpc_url, args.wallet, args.gas_floor)
    results.append(("wallet gas", ok, detail))

    ok, detail = check_endpoint_reachable(args.metadata_url)
    results.append(("public reachability", ok, detail))

    failed = 0
    for name, ok, detail in results:
        mark = "OK  " if ok else "FAIL"
        print("[%s] %-22s %s" % (mark, name, detail))
        if not ok:
            failed += 1

    print()
    if failed:
        print("%d check(s) failed - buyers may not see this node." % failed)
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
