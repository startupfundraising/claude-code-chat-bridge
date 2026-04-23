# chat-bridge

**A phone call between two Claude Code terminals.** One asks, the other answers from its context. No copy-paste. No IDs to remember. No files to clean up.

```
Terminal A: /ans        ← picks up the phone
Terminal B: /qu         ← describes a problem, Claude does the rest
```

## TL;DR

Super simple way to let Claude Code "phone a friend" between sessions and sort out your issues. You need a session with a problem and a session with the answers. You write one prompt in each terminal and let them do their thing. No IDs to remember, no files to clean up.

You need:
- Claude Code
- Two terminals, two sessions
- `/qu` and `/ans` memorised

## Install

```bash
claude plugin marketplace add startupfundraising/claude-code-chat-bridge
claude plugin install chat-bridge
```

Requirements: Python 3.9+ (stdlib only — no extra packages), POSIX filesystem (Linux, macOS, WSL).

## How to use it (pragmatically)

> Note: I find repos painful because no one explains how they actually work in practice. Here's the human version.

Concrete example — you're setting up Redis on a new WordPress site, and you know you did exactly this on another site a month ago. Instead of parsing through an old Claude Code session manually, you just get the old session to tell the new one what to do.

1. **New-setup terminal:** you're working with Claude Code. You hit the Redis step. You tell Claude *"I set this up before in another session, let me open that one so we can ask it."*
2. **Old-setup terminal:** resume the old Claude Code session that has the Redis setup history. Confirm it's the right one — ask Claude to summarise what it did with Redis.
3. **Old-setup terminal, type:** `/ans`. It picks up and waits.
4. **New-setup terminal, type:** `/qu`. It dials. Either order works — whichever is second waits up to 30 seconds for the first.
5. **Leave them alone. Touch some grass.** The `/qu` session reads the recent conversation, figures out what to ask, chats with the `/ans` session, asks follow-ups if needed, hangs up, and reports back.
6. **You come back to a summary.** Usually something like *"The other session confirmed the approach — here's what to do next."* Approve the plan and move on.

Nothing to clean up. If anything breaks mid-call — WSL dies, a session crashes, whatever — tough. Your sessions are broken anyway and need restoring. Just redial once you're back. It's 15 seconds.

### What a call actually looks like

```
# Old-setup terminal (answerer)
> /ans
Answer mode active. Waiting for questions…

Received: "How did you install the object cache plugin, and what variables
did you set in wp-config.php for Redis auth?"
[answering from context]
Sent.

Received: "Did you set a password, or rely on bind to 127.0.0.1?"
[answering from context]
Sent.

Call ended.

# New-setup terminal (questioner)
> /qu
Dialling… Connected.

Asking: "How did you install the object cache plugin, and what variables
did you set in wp-config.php for Redis auth?"
[received answer]

Asking: "Did you set a password, or rely on bind to 127.0.0.1?"
[received answer]

Call ended. Summary: Object Cache Pro installed via composer; WP_REDIS_HOST
= 127.0.0.1 in wp-config.php; no password, relying on 127.0.0.1 bind.
Ready to apply the same setup here — want me to proceed?
```

## When this works (and when it doesn't)

**Works when:**
- `/qu` session has a real problem and understands its context.
- `/ans` session has actual knowledge — files read, steps taken, decisions made in its own conversation history.

**Doesn't work when:**
- Both sessions are fresh and empty. `/qu` has nothing to ask about, `/ans` has nothing to say.
- The `/ans` session isn't actually about the right topic. It can only share what it's actually done.

**Use it if** you run multiple Claude Code sessions, restore old ones, or want to pull context from a past session without copy-pasting. Basically anyone who uses Claude Code seriously.

**Skip it if** you only run one session at a time and never resume old ones. No downside to having it installed — it just won't do anything for you.

## Why I made this

I run a lot of Claude Code sessions. I also save old ones, because pulling context from a session I've already done is way easier than re-deriving it from scratch.

The problem: parsing through a month-old session to find what you did is not fun. But if you already solved it, why not just get the old session to tell your new session directly?

Remembering specific commands is a pain. Building log files and edge-case handling is a pain. I can barely remember functionality I built last week, let alone how it works. So I made something with two principles:

1. **Sessions should talk to each other so I don't have to think.**
2. **All I want to remember is `/qu` and `/ans`.**

I deliberately avoided edge cases and complexity. If something breaks mid-call, redial. The tool stays small because recovery is a you-problem, not a tool-problem.

## Design principles

- **Phone call metaphor.** One line, two parties. Not a multi-peer messaging fabric.
- **Zero RAM at rest.** The CLI spawns per command and exits. About 30 MB briefly during send/receive, 0 MB otherwise.
- **No persistence.** State lives in `/tmp/chat-bridge/` — gone on reboot, clean by design.
- **Either order.** Run `/qu` first or `/ans` first — whichever is second waits.
- **No identity, no UUIDs, no multi-peer.** If you want those, see [claude-code-session-bridge](https://github.com/PatilShreyas/claude-code-session-bridge) — different trade-off.

## Configuration

All optional — defaults are sensible.

| Variable | Default | What |
|---|---|---|
| `CHAT_BRIDGE_DIR` | `/tmp/chat-bridge` | State directory |
| `CHAT_BRIDGE_STALE_SECONDS` | `300` | When a silent side is considered gone (5 min) |
| `CHAT_BRIDGE_DIAL_WAIT_SECONDS` | `30` | How long `dial` waits for an answerer |
| `CHAT_BRIDGE_RECEIVE_BLOCK_SECONDS` | `50` | How long `receive` blocks per call |

## Troubleshooting

**"No terminal is in answer mode after 30s"** — Run `/ans` in the other terminal and retry `/qu`.

**"Phone line already in use"** — Another pair is mid-call on this machine. Wait, or clear state:
```bash
rm -rf /tmp/chat-bridge
```

**Stuck, weird state, anything else** — Same fix. `rm -rf /tmp/chat-bridge` and redial.

## Testing

```bash
python3 plugins/chat-bridge/tests/test_cli.py
```

35 tests, no live terminals required.

**Not tested with** Codex, OpenRouter models via Claudish, or other non-Claude models running inside Claude Code. The CLI itself is model-agnostic — it's just a shell tool — so it should work with any model that can follow a skill and shell out. Let me know if you try it.

## CLI reference

The skills invoke these. You won't normally run them by hand — included for the curious.

```
chat-bridge pick-up                       # answerer picks up
chat-bridge dial                          # questioner dials (waits up to 30s)
chat-bridge send --as ROLE "message"      # send
chat-bridge receive --as ROLE             # block up to 50s for a message
chat-bridge hang-up --as ROLE             # end the call
chat-bridge status                        # debug: show current state
```

`ROLE` is `answerer` or `questioner`. All commands print JSON.

## Roadmap

Intentionally minimal. Things that could be added (probably won't be soon):
- tmux integration for one-command pane setup.
- One-shot `/qu ask "..."` for single-turn lookups.
- CI via GitHub Actions.

The whole point is simplicity. Feature requests welcome if they fit the phone-call metaphor.

## License

MIT — see [LICENSE](LICENSE).
