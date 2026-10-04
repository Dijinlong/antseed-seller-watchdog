# antseed-seller-watchdog

A small watchdog for [antseed](https://antseed.com) seller nodes.

## Why this exists

An antseed seller can look perfectly healthy and still be **invisible to buyers**.
Every conventional health check passes while the node is quietly not advertising:

| What you check | What it tells you |
|---|---|
| `systemctl is-active` | the process is alive, and nothing else |
| TCP port 6882 listening | it is still listening, but maybe not reachable |
| `/metadata` returns HTTP 200 | `providers` may be an **empty array** |
| seller status `SEEDING` | advertising may have silently paused |

The most common silent failure is a **gas-starved wallet**: antseed pauses advertising
below `0.00005 ETH`, while the process keeps running and every "is it up?" check
still passes.

## What it checks

1. `/metadata` — is `providers[0].services` non-empty?
2. Wallet balance — below the gas floor?
3. `seller status` — still `SEEDING`?
4. Advertised endpoint — reachable from the public internet, not just from localhost?

## Status

Early. Extracted from a production seller deployment where all four failure modes
above were hit in practice.

## Contributing

Issues and PRs welcome — especially reports of failure modes that look healthy
from the outside.
