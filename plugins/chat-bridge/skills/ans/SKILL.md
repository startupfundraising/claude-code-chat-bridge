---
name: ans
description: |
  Enter answer mode — wait for another terminal to ask questions, answer from your context.
  Use /ans when another Claude Code terminal needs to ask this one questions about its context.
---

# Answer Mode

Another Claude Code terminal is going to ask you questions and you will answer them from YOUR conversation context. All communication happens via the bundled CLI at `${CLAUDE_PLUGIN_ROOT}/bin/chat-bridge`.

## Setup

1. Pick up the phone:
   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/chat-bridge" pick-up
   ```
   - If it returns `{"status": "picked_up"}`, proceed.
   - If it returns `{"status": "error", "reason": "in_use"}`, tell the user: *"Another terminal is already in answer mode. Close that one first."* Stop.

2. Tell the user: *"Answer mode active. Waiting for questions…"*

## Conversation loop

3. Wait for a question:
   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/chat-bridge" receive --as answerer
   ```
   Handle the result based on `status`:
   - `"message"` — read the question. Answer it thoroughly using your own conversation history and knowledge of this project. Then send your answer:
     ```bash
     "${CLAUDE_PLUGIN_ROOT}/bin/chat-bridge" send --as answerer "YOUR ANSWER HERE"
     ```
     Then go back to step 3 (receive again).
   - `"waiting"` — nothing arrived in 50 seconds. Call `receive` again immediately. Say nothing to the user.
   - `"hung_up"` — the other side ended the call. Tell the user: *"Call ended."* Stop.

## Rules

- **Answer from YOUR context.** The whole point of this mode is that you have knowledge the other terminal lacks. Use your conversation history, files you've read, decisions you've made in this session. Don't deflect questions back to the user — you have the answers.
- **Be thorough and specific.** The other terminal will act on your answer, so include file paths, function names, exact error strings, and whatever concrete details will actually help.
- **On `"waiting"` status, retry `receive` silently** — do not output anything.
- **When answering, you may briefly show the user what was asked and how you're answering** — a one-liner is enough. They might want to correct you if you're about to mislead the other terminal.
- **Do not use `hang-up`.** The questioner controls when the call ends.
