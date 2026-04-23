---
name: qu
description: |
  Enter question mode — connect to a terminal in answer mode and ask it questions until you have what you need.
  Use /qu to ask another Claude Code terminal questions about its context.
---

# Question Mode

You are about to talk to a Claude Code session in another terminal that has context you are missing. Your job is to extract the information the user needs from that other terminal, then hang up and report back.

All communication happens via the bundled CLI at `${CLAUDE_PLUGIN_ROOT}/bin/chat-bridge`. All commands print JSON to stdout.

## Setup

1. Look at the recent conversation in this terminal. What problem is the user trying to solve? What would the other terminal plausibly know that would help? Formulate your first question.

2. Dial the other terminal:
   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/chat-bridge" dial
   ```
   - This waits up to 30 seconds for `/ans` to be running in the other terminal. Either order works — the user can run `/qu` first or `/ans` first.
   - If it returns `{"status": "connected"}`, proceed.
   - If it returns `{"status": "error", "reason": "no_answerer"}`, tell the user: *"No terminal is in answer mode. Run `/ans` in the other terminal, then try `/qu` again."* Stop.
   - If it returns `{"status": "error", "reason": "busy"}`, tell the user: *"Another questioner is already on a call."* Stop.

3. Tell the user briefly: *"Connected. Asking: &lt;your first question&gt;"* — then immediately send it (step 4). Don't wait for confirmation. If they want to redirect, they'll interrupt.

## Conversation loop

4. Send your question:
   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/chat-bridge" send --as questioner "YOUR QUESTION HERE"
   ```

5. Wait for the answer:
   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/chat-bridge" receive --as questioner
   ```
   Handle the result based on `status`:
   - `"message"` — show the answer to the user (briefly), then decide: do you have what you need, or do you need a follow-up? If follow-up, go to step 4. If done, go to step 6.
   - `"waiting"` — the other side hasn't replied in 50 seconds. Call `receive` again immediately. Say nothing to the user.
   - `"hung_up"` — the other side ended the call. Tell the user: *"The other terminal disconnected."* Stop.

6. When you have the information the user needs (or the user says they're done):
   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/chat-bridge" hang-up --as questioner
   ```
   Then summarize what you learned for the user and proceed with whatever task they originally had.

## Rules

- **Drive the conversation yourself.** The user set up the call because they trust you to extract what's needed. Formulate clear questions from the recent conversation context. Don't stop to ask the user what to ask unless you genuinely have no context.
- **Multi-turn is fine.** Ask follow-ups if the first answer is incomplete. You control when to hang up.
- **On `"waiting"` status, retry `receive` silently** — do not output anything.
- **Show your questions before sending.** One line: *"Asking: '...'"*. This lets the user redirect if you're off-track, without adding a confirmation step.
- **After hang-up, do the user's actual task** using what you learned. That's the point — the phone call was a means, not the end.
