#!/usr/bin/env python3
"""Tests for the chat-bridge CLI.

Runs the CLI as a subprocess against an isolated state dir.
Usage: python3 test.py
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

TEST_DIR = Path("/tmp/chat-bridge-test")
# Default to the CLI bundled alongside this test file; override with CHAT_BRIDGE_CLI.
_DEFAULT_CLI = Path(__file__).resolve().parent.parent / "bin" / "chat-bridge"
CLI = os.environ.get("CHAT_BRIDGE_CLI", str(_DEFAULT_CLI))

# Fast timeouts for testing
TEST_ENV = {
    **os.environ,
    "CHAT_BRIDGE_DIR": str(TEST_DIR),
    "CHAT_BRIDGE_STALE_SECONDS": "5",
    "CHAT_BRIDGE_DIAL_WAIT_SECONDS": "3",
    "CHAT_BRIDGE_RECEIVE_BLOCK_SECONDS": "2",
}


def run(*args, check=False, env_overrides=None):
    """Run the CLI; return (exit_code, parsed_json)."""
    env = dict(TEST_ENV)
    if env_overrides:
        env.update(env_overrides)
    result = subprocess.run(
        [CLI, *args],
        capture_output=True, text=True, env=env, timeout=30,
    )
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        parsed = {"_raw_stdout": result.stdout, "_stderr": result.stderr}
    if check and result.returncode != 0:
        raise RuntimeError(f"CLI failed: {parsed}")
    return result.returncode, parsed


def reset():
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)


passed = failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  ✓  {name}")
        passed += 1
    else:
        print(f"  ✗  {name}" + (f"  [{detail}]" if detail else ""))
        failed += 1


# ── tests ─────────────────────────────────────────────────────────────────────

print("\n═══ chat-bridge CLI tests ═══\n")

# 1. status on empty state
reset()
print("1. status on empty state")
code, out = run("status")
check("exit 0", code == 0)
check("answerer not active", out["roles"]["answerer"]["active"] is False)
check("questioner not active", out["roles"]["questioner"]["active"] is False)

# 2. pick-up registers answerer
reset()
print("\n2. pick-up")
code, out = run("pick-up")
check("exit 0", code == 0, f"got {code}, out={out}")
check("status picked_up", out.get("status") == "picked_up")
check("role answerer", out.get("role") == "answerer")
code, out = run("status")
check("answerer now active", out["roles"]["answerer"]["active"] is True)

# 3. pick-up blocks when answerer already fresh
reset()
print("\n3. pick-up blocked if already active")
run("pick-up")
code, out = run("pick-up")
check("exit non-zero", code != 0)
check("reason in_use", out.get("reason") == "in_use")

# 4. dial fails when no answerer (after wait)
reset()
print("\n4. dial with no answerer")
start = time.time()
code, out = run("dial")
elapsed = time.time() - start
check("exit non-zero", code != 0)
check("reason no_answerer", out.get("reason") == "no_answerer")
check(f"waited roughly DIAL_WAIT_SECONDS (got {elapsed:.1f}s)", 2.5 <= elapsed <= 5)

# 5. dial succeeds when answerer is present
reset()
print("\n5. dial succeeds with answerer")
run("pick-up")
code, out = run("dial")
check("exit 0", code == 0)
check("status connected", out.get("status") == "connected")

# 6. either-order: run dial first, pick-up mid-wait
reset()
print("\n6. either-order — dial waits, pick-up arrives")
# Start dial in background
dial_proc = subprocess.Popen(
    [CLI, "dial"], env=TEST_ENV,
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
)
time.sleep(1)  # let dial start waiting
run("pick-up")  # answerer picks up while dial is waiting
stdout, _ = dial_proc.communicate(timeout=5)
dial_out = json.loads(stdout)
check("dial succeeded after pick-up arrived", dial_out.get("status") == "connected")

# 7. send + receive round trip
reset()
print("\n7. send + receive round trip")
run("pick-up")
run("dial")
run("send", "--as", "questioner", "hello answerer")
code, out = run("receive", "--as", "answerer")
check("answerer received message", out.get("status") == "message")
check("correct content", out.get("message") == "hello answerer")
# Reverse direction
run("send", "--as", "answerer", "hi questioner")
code, out = run("receive", "--as", "questioner")
check("questioner received reply", out.get("status") == "message")
check("correct reply content", out.get("message") == "hi questioner")

# 8. receive times out with "waiting"
reset()
print("\n8. receive blocks then returns waiting")
run("pick-up")
run("dial")
start = time.time()
code, out = run("receive", "--as", "answerer")
elapsed = time.time() - start
check("status waiting", out.get("status") == "waiting")
check(f"blocked roughly RECEIVE_BLOCK_SECONDS (got {elapsed:.1f}s)", 1.5 <= elapsed <= 4)

# 9. FIFO message order
reset()
print("\n9. FIFO ordering")
run("pick-up")
run("dial")
for msg in ("first", "second", "third"):
    run("send", "--as", "questioner", msg)
for expected in ("first", "second", "third"):
    code, out = run("receive", "--as", "answerer")
    check(f"got {expected}", out.get("message") == expected)

# 10. send without being on a call fails
reset()
print("\n10. send without being on a call")
code, out = run("send", "--as", "answerer", "x")
check("exit non-zero", code != 0)
check("reason not_on_call", out.get("reason") == "not_on_call")

# 11. hang-up from questioner notifies answerer via __END__
reset()
print("\n11. hang-up sends __END__ to the other side")
run("pick-up")
run("dial")
run("hang-up", "--as", "questioner")
code, out = run("receive", "--as", "answerer")
check("answerer sees hung_up", out.get("status") == "hung_up")

# 12. hang-up cleans up state
reset()
print("\n12. hang-up cleans up")
run("pick-up")
run("hang-up", "--as", "answerer")
code, out = run("status")
check("answerer inactive after hang-up", out["roles"]["answerer"]["active"] is False)

# 13. stale other side triggers hung_up during receive
reset()
print("\n13. stale other side → hung_up")
# Use extra-short stale threshold for this test
env_override = {"CHAT_BRIDGE_STALE_SECONDS": "1", "CHAT_BRIDGE_RECEIVE_BLOCK_SECONDS": "3"}
run("pick-up", env_overrides=env_override)
run("dial", env_overrides=env_override)
# Age the questioner's .active file beyond threshold by touching with old time
qa = TEST_DIR / "questioner.active"
past = time.time() - 10
os.utime(qa, (past, past))
code, out = run("receive", "--as", "answerer", env_overrides=env_override)
check("status hung_up", out.get("status") == "hung_up")
check("reason other_side_gone", out.get("reason") == "other_side_gone")

# 14. pick-up after other side went stale allows fresh call
reset()
print("\n14. stale answerer → new pick-up works")
run("pick-up")
af = TEST_DIR / "answerer.active"
past = time.time() - 10
os.utime(af, (past, past))
code, out = run("pick-up")
check("new pick-up succeeds", code == 0 and out.get("status") == "picked_up")

# 15. status shows inbox count
reset()
print("\n15. status shows inbox counts")
run("pick-up")
run("dial")
run("send", "--as", "questioner", "a")
run("send", "--as", "questioner", "b")
code, out = run("status")
check("answerer inbox has 2", out["roles"]["answerer"]["inbox_count"] == 2)
check("questioner inbox has 0", out["roles"]["questioner"]["inbox_count"] == 0)

# 16. invalid --as rejected
reset()
print("\n16. invalid --as rejected")
code, out = run("send", "--as", "martian", "x")
check("exit non-zero", code != 0)

# 17. missing required --as rejected
reset()
print("\n17. missing required --as")
code, out = run("send", "hello")
check("exit non-zero", code != 0)

# ── summary ───────────────────────────────────────────────────────────────────

print(f"\n═══ {passed} passed  {failed} failed ═══\n")

if TEST_DIR.exists():
    shutil.rmtree(TEST_DIR)

sys.exit(0 if failed == 0 else 1)
