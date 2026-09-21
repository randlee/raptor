# Runtime preflight (guideline v0.7)

```bash
which python3 && python3 --version
```

If `python3` is absent from PATH, run the v0.7 common-location fallback:

```bash
for p in "$HOME/.local/bin/python3" "$HOME/.venvs/python3/bin/python3" \
  "$(python3 -m site --user-base 2>/dev/null)/bin/python3" \
  "/opt/homebrew/bin/python3"; do
  [ -x "$p" ] && echo "Found at: $p" && break
done
```

Use the discovered full path for every command, or export its directory for this session (for example, `export PATH="$HOME/.local/bin:$PATH"`). Require Python 3.11+.

Then run `<python> -c 'import pydantic; print(pydantic.__version__)'` and require Pydantic `>=2.10,<3`. Stop and read `references/installation-and-troubleshooting.md` if either dependency is unavailable or incompatible.
