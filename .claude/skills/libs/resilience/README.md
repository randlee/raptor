# Library Resilience Reference Notes

## Don't Glob Re-Export Items (M-NO-GLOB-REEXPORTS) { #M-NO-GLOB-REEXPORTS }

Do not use wildcard re-exports as a public-surface shortcut.

Prefer explicit re-exports so:
- API surfaces stay intentional
- downstream users can see what is stable
- accidental exports do not leak through a convenience glob
