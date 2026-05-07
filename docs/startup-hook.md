# Startup Hook

This repo uses the global Claude `SessionStart` hook to inject startup prompts
based on startup mode and ATM identity.

The implementation follows the current `schook` Claude hook guidance first and
uses the older `synaptic-canvas` hook notes only as secondary background.

## Files

- global Claude hook settings under `~/.claude/settings.json`
- global startup hook implementation at `~/.claude/scripts/session-start.py`
- repo-local startup prompt config in `.atm.toml`

## Hook Design

- Registration lives in the global Claude settings.
- The global SessionStart hook reads repo `.atm.toml` when present.
- Startup prompt content remains repo-authored under `[startup]`.
- Output is structured JSON using `hookSpecificOutput.additionalContext`,
  which Claude adds to session context.
- Missing `.atm.toml`, missing `[startup]`, missing identity startup entries,
  and missing mode fragments are all treated as no-op cases rather than errors.

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

- The repo does not need a project-local `SessionStart` hook script anymore.
- Startup context is now fail-open:
  - missing `.atm.toml` -> no startup prompt injection
  - missing `[startup]` -> no startup prompt injection
  - missing `ATM_IDENTITY` entry -> no startup prompt injection
  - no matching fragments for the current mode -> no startup prompt injection
- No external dependencies are required; the global script uses Python stdlib only.
- `SessionStart` can inject context, but it cannot force a mandatory tool call.
  In practice this means startup prompts should be written as strong procedural
  instructions, but occasional model drift is still possible.

## Local Verification

Example manual check:

```bash
printf '%s\n' \
  '{"hook_event_name":"SessionStart","session_id":"test","cwd":"'"$PWD"'","source":"startup","model":"claude-sonnet-4-6"}' \
  | CLAUDE_PROJECT_DIR="$PWD" ATM_TEAM=raptor ATM_IDENTITY=team-lead \
      python3 /Users/randlee/.claude/scripts/session-start.py
```

Expected result:

- stdout is valid JSON
- `hookSpecificOutput.hookEventName` is `SessionStart`
- `hookSpecificOutput.additionalContext` contains the concatenated prompt text
  plus the standard session/team/identity startup lines
