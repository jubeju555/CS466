# bof-water18 walkthrough (moa6.eecs.utk.edu:8009)

## Goal
Overwrite `desk` so the program prints the flag.

## What matters in the code
- `water` is a 24‑byte stack buffer.
- `gets(water)` allows writing past 24 bytes.
- If `desk == 0x18181818`, the flag prints.

## Key observation
The stack layout places `desk` next to `water`, so 24 bytes of padding plus 4 bytes for the new `desk` value should overwrite it. The system is little‑endian, so `0x18181818` is written as `\x18\x18\x18\x18`.

## Exploit plan (simple steps)
1. Send 24 filler bytes to fill `water`.
2. Send 4 bytes `\x18\x18\x18\x18` to overwrite `desk`.
3. Read the flag from the response.

## Non‑Python payload (buffer overflow)
Use `printf` to generate raw bytes and pipe into `nc`.

```
printf 'AAAAAAAAAAAAAAAAAAAAAAAA\x18\x18\x18\x18\n' | nc moa6.eecs.utk.edu 8009
```

That is 24 `A` characters, then four `0x18` bytes, then a newline.

## Python helper (separate folder)
If you want a reusable script with comments, see:
- [ctf/bof-water18/README.md](ctf/bof-water18/README.md)
- [ctf/bof-water18/exploit.py](ctf/bof-water18/exploit.py)

## Flag
cosc466-flag-{099gV4OY7aGm}
