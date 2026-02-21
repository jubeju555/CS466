# bof-water walkthrough (moa6.eecs.utk.edu:8005)

## Goal
Trigger the program to print the flag by changing the stack variable `desk` from its initial value.

## What matters in the code
- `gets(water)` reads until newline and does **not** check length.
- `water` is a 30‑byte stack buffer.
- `desk` is nearby on the stack.
- If `desk` changes, the flag prints.

## Why this works (buffer overflow)
Any input longer than 30 bytes overflows past `water` and overwrites adjacent stack data. One of those values is `desk`. We only need `desk != 0x18181818`, so any overflow that flips it is enough.

## Step‑by‑step solution (no GDB needed)
1. Connect to the service.
2. Send more than 30 bytes so the overflow flips `desk`.
3. Read the flag from the response.

## Minimal exploit (example)
Send 40 `A` characters and a newline:

```
printf 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n' | nc moa6.eecs.utk.edu 8005
```

## Optional: verify locally (only if asked)
If you are required to verify with GDB:
1. Compile with symbols: `gcc -g bof-water.c -o bof-water`
2. Run: `gdb ./bof-water`
3. Break after `gets`, then check `desk` to confirm it changed.

## Result
Using a 40‑byte payload flips `desk`, which causes the program to print the flag.
