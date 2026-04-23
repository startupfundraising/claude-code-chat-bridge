# chat-bridge

**A phone call between two Claude Code terminals.** One terminal asks questions, the other answers from its context. No copy-paste, no text files, no MCP server running in the background.

```
Terminal A: /ans        ← picks up the phone
Terminal B: /qu         ← describes a problem, dials, Claude does the rest
```

Claude in Terminal B figures out what to ask from your conversation, chats with Terminal A's Claude, gets the answers, hangs up, and reports back. You just set up the call.

## Why

If you run multiple Claude Code sessions, you often hit: *"the other terminal knows X and I need it here."* Options:
- Copy-paste between terminals (slow, loses formatting, breaks on long context).
- Re-prompt and hope the second session re-derives the context (unreliable).
- Use this.

## Design principles

- **Phone call metaphor.** One line, two parties. Not a multi-peer messaging fabric.
- **Zero RAM at rest.** The CLI spawns per command and exits. No always-on server. (About 30 MB briefly while `send`/`receive` runs, 0 MB otherwise.)
- **No persistence.** State lives in `/tmp/chat-bridge/` — gone on reboot, clean by design. If something breaks, `rm -rf /tmp/chat-bridge` and redial.
- **Either order.** Run `/qu` first or `/ans` first — whichever is second waits up to 30 seconds.
- **No identity, no UUIDs, no multi-peer.** If you want those, use [claude-code-session-bridge](https://github.com/PatilShreyas/claude-code-session-bridge) — different tradeoff.

## Install

```bash
claude plugin marketplace add alexanderjarvis/claude-code-chat-bridge
claude plugin install chat-bridge
```

That's it. The CLI and two skills (`/qu`, `/ans`) are installed.

### Requirements

- Python 3.9+ (stdlib only — no extra packages)
- POSIX filesystem (Linux, macOS, WSL)

## Usage

**Terminal A** (the one with knowledge you need):
```
/ans
```
Claude picks up and waits silently for questions.

**Terminal B** (the one with a problem):
1. Describe your problem normally to Claude.
2. When Claude needs info the other terminal has, type:
   ```
   /qu
   ```
3. Claude formulates questions based on the conversation, asks them, gets answers, and reports back.

When done, the questioner hangs up. Both terminals return to normal.

## Troubleshooting

**"No terminal is in answer mode after 30s"** — You didn't run `/ans` in the other terminal in time. Start `/ans` and retry `/qu`.

**"Phone line already in use"** — Another pair is mid-call on this machine. Wait or clear state:
```bash
rm -rf /tmp/chat-bridge
```

**Stuck / weird state** — Same fix. A call is 15 seconds to set up; just redial.

## Configuration

All tunable via environment variables (optional):

| Variable | Default | What |
|---|---|---|
| `CHAT_BRIDGE_DIR` | `/tmp/chat-bridge` | State directory |
| `CHAT_BRIDGE_STALE_SECONDS` | `300` | When a silent side is considered gone (5 min) |
| `CHAT_BRIDGE_DIAL_WAIT_SECONDS` | `30` | How long `dial` waits for an answerer |
| `CHAT_BRIDGE_RECEIVE_BLOCK_SECONDS` | `50` | How long `receive` blocks per call |

## Tests

```bash
python3 plugins/chat-bridge/tests/test_cli.py
```

35 tests, no live terminals required.

## CLI reference (for the curious)

The skills invoke these; you won't normally run them by hand.

```
chat-bridge pick-up                       # answerer picks up
chat-bridge dial                          # questioner dials (waits up to 30s)
chat-bridge send --as ROLE "message"      # send
chat-bridge receive --as ROLE             # block up to 50s for a message
chat-bridge hang-up --as ROLE             # end the call
chat-bridge status                        # debug: show current state
```

`ROLE` is `answerer` or `questioner`. All commands print JSON.

## License

MIT — see [LICENSE](LICENSE).
