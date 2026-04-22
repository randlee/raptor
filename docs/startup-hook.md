# Startup Hook

This repo now includes a project-level Claude `SessionStart` hook that injects
startup prompts based on startup mode and ATM identity.

The implementation follows the current `schook` Claude hook guidance first and
uses the older `synaptic-canvas` hook notes only as secondary background.

## Files

- `.claude/settings.json`
- `.claude/hooks/session_start_context.py`
- `.atm.toml`

## Hook Design

- Registration is in project `.claude/settings.json`, which is the documented
  Claude surface for project hooks.
- `SessionStart` is registered with four matcher groups:
  - `startup`
  - `resume`
  - `clear`
  - `compact`
- Each matcher calls the same script with `--mode <matcher>`.
- The hook command also passes `--atm-team "$ATM_TEAM"` and
  `--atm-identity "$ATM_IDENTITY"` explicitly.
- The script still treats the inbound payload `source` field as the source of
  truth and only uses the matcher argument as a cross-check.
- Output is structured JSON using
  `hookSpecificOutput.additionalContext`, which Claude adds to session context.
- The hook command is anchored to `"$CLAUDE_PROJECT_DIR"` so it still resolves
  correctly if the Claude session changes directories later.

## Prompt Storage

Prompt text is stored in `.atm.toml` under `startup`.

Current shape:

```toml
[startup]
all = ["..."]

[startup.team-lead]
"startup,resume" = ["..."]
clear = ["..."]
compact = ["..."]
```

Supported value types:

- a single string
- an array of strings
- strings starting with `@file:` to inject a repo-relative file's contents

The hook concatenates:

- optional global `startup.all`
- optional identity `startup.<identity>.all`
- any identity key whose comma-delimited mode list contains the active mode

`all` is injected first. Each configured string becomes one output line, and
the final injected context is joined with `\n`.

Example:

```toml
[startup.quality-mgr]
all = [
  "This is your directive:",
  "@file:.claude/agents/quality-mgr.md",
]
```

## Operational Notes

- The hook is intentionally strict for missing startup identity context.
- If `CLAUDE_PROJECT_DIR`, `ATM_TEAM`, or `ATM_IDENTITY` are missing, the
  script exits non-zero.
- If no prompt entries exist for the `(ATM_IDENTITY, mode)` pair, the script
  exits non-zero.
- No external dependencies are required; the script uses Python stdlib only.
- `SessionStart` can inject context, but it cannot force a mandatory tool call.
  In practice this means startup prompts should be written as strong procedural
  instructions, but occasional model drift is still possible.

## Local Verification

Example manual check:

```bash
printf '%s\n' \
  '{"hook_event_name":"SessionStart","session_id":"test","cwd":"'"$PWD"'","source":"startup","model":"claude-sonnet-4-6"}' \
  | CLAUDE_PROJECT_DIR="$PWD" python3 .claude/hooks/session_start_context.py \
      --mode startup \
      --atm-team raptor \
      --atm-identity team-lead
```

Expected result:

- stdout is valid JSON
- `hookSpecificOutput.hookEventName` is `SessionStart`
- `hookSpecificOutput.additionalContext` contains the concatenated prompt text
