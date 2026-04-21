# Universal Reference Notes

## Panic Means 'Stop the Program' (M-PANIC-IS-STOP) { #M-PANIC-IS-STOP }

Panics are not a normal user-facing error-handling strategy.

Use panics only for unrecoverable programming errors or invariant failures where continuing would be incorrect. User input, I/O failures, and normal operational problems should not rely on panic paths.
