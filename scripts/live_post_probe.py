#!/usr/bin/env python3
"""Probe every Revenue Cloud action with an intentionally incomplete POST.

This validates the MCP -> Salesforce POST path for each action without providing
business record IDs that could create or mutate Revenue Cloud data.
"""

import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from revenuecloud_mcp.actions import action_names


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


def is_expected_validation_response(body):
    if not isinstance(body, list):
        return False
    if not body:
        return False
    first = body[0]
    if not isinstance(first, dict):
        return False
    if first.get("isSuccess") is False and first.get("errors") is not None:
        return True
    if first.get("errorCode") or first.get("message"):
        return True
    return False


def main():
    target_org = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SALESFORCE_TARGET_ORG") or os.environ.get("SF_TARGET_ORG")
    api_version = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("SALESFORCE_API_VERSION")
    if not target_org:
        raise SystemExit("Usage: live_post_probe.py <target-org> [api-version] or set SALESFORCE_TARGET_ORG.")
    proc = subprocess.Popen(
        [sys.executable, "-m", "revenuecloud_mcp.server"],
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        rpc(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        results = []
        next_id = 2
        for name in action_names():
            res = rpc(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": next_id,
                    "method": "tools/call",
                    "params": {
                        "name": name,
                        "arguments": {
                            key: value
                            for key, value in {
                                "target_org": target_org,
                                "api_version": api_version,
                                "inputs": [{}],
                            }.items()
                            if value is not None
                        },
                    },
                },
            )
            next_id += 1
            response = json.loads(res["content"][0]["text"])
            body = response.get("body")
            expected_validation = response.get("status") in (200, 400) and is_expected_validation_response(body)
            results.append(
                {
                    "tool": name,
                    "http_status": response.get("status"),
                    "ok": response.get("ok"),
                    "expected_validation_error": expected_validation,
                }
            )

        unexpected = [item for item in results if not item["expected_validation_error"]]
        report = {
            "target_org": target_org,
            "api_version": api_version or "target org default",
            "probed_action_tools": len(results),
            "expected_validation_errors": len([item for item in results if item["expected_validation_error"]]),
            "unexpected": unexpected,
            "results": results,
        }
        print(json.dumps(report, indent=2))
        if unexpected:
            sys.exit(2)
    finally:
        proc.kill()
        proc.wait()


if __name__ == "__main__":
    main()
