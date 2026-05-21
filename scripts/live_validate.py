#!/usr/bin/env python3
"""Non-mutating live validation against Salesforce action describe endpoints."""

import json
import os
import subprocess
import sys


def rpc(proc, req):
    proc.stdin.write(json.dumps(req) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        err = proc.stderr.read()
        raise AssertionError("server closed stdout: %s" % err)
    msg = json.loads(line)
    if "error" in msg:
        raise AssertionError(msg["error"])
    return msg["result"]


def main():
    target_org = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SALESFORCE_TARGET_ORG") or os.environ.get("SF_TARGET_ORG")
    api_version = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("SALESFORCE_API_VERSION")
    if not target_org:
        raise SystemExit("Usage: live_validate.py <target-org> [api-version] or set SALESFORCE_TARGET_ORG.")
    proc = subprocess.Popen(
        [sys.executable, "-m", "revenuecloud_mcp.server"],
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        rpc(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        result = rpc(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "validate_revenue_cloud_actions",
                    "arguments": {
                        key: value
                        for key, value in {"target_org": target_org, "api_version": api_version}.items()
                        if value
                    },
                },
            },
        )
        rows = json.loads(result["content"][0]["text"])
        ok = [r for r in rows if r["ok"]]
        unsupported = [
            r
            for r in rows
            if not r["ok"]
            and r.get("status") == 400
            and "Unsupported action type" in json.dumps(r.get("body"))
        ]
        failed = [r for r in rows if not r["ok"] and r not in unsupported]
        print(
            json.dumps(
                {
                    "target_org": target_org,
                    "api_version": api_version or "target org default",
                    "described": len(ok),
                    "unsupported_by_org": len(unsupported),
                    "failed": len(failed),
                    "results": rows,
                },
                indent=2,
            )
        )
        if failed:
            sys.exit(2)
    finally:
        proc.kill()
        proc.wait()


if __name__ == "__main__":
    main()
