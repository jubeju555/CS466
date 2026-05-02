# Ret2Libc Practice Walkthrough

## Overview
**Vulnerability:** Stack buffer overflow via `gets()` in a 32-bit binary  
**Goal:** Leak one libc address, compute `system()`, and use the overflow to run a command  
**Style:** Same exploit class as the exam challenge, but with one extra leak step so you practice the full ret2libc workflow

---

## What The Binary Gives You

The challenge binary has:

- a 12-byte stack buffer
- a `gets(buffer)` call with no bounds checking
- a writable global buffer named `staging`
- a helper `popret()` gadget to clean one stack slot between chained calls
- imported PLT entries for `puts`, `gets`, and `exit`
- no direct `system()` PLT entry, so you must compute `system()` inside libc

That last point is the whole lesson: this is a real ret2libc exploit, not just a ret2plt shortcut.

---

## Key Offsets And Symbols

| Item | Value |
|------|-------|
| Buffer size | 12 bytes |
| Offset to saved return address | 24 bytes |
| `puts@plt` | resolved by `exploit.py` |
| `gets@plt` | resolved by `exploit.py` |
| `exit@plt` | resolved by `exploit.py` |
| `puts@got` | resolved by `exploit.py` |
| `popret` | resolved by `exploit.py` |
| `service` | resolved by `exploit.py` |
| `staging` | resolved by `exploit.py` |

---

## How The Exploit Works

The attack has two stages:

1. Call `puts(puts@got)` to leak the runtime address of `puts` from libc.
2. Compute `libc_base = leaked_puts - puts_offset`, then `system_addr = libc_base + system_offset`.
3. Return to the vulnerable function, overflow it again, call `gets(staging)`, then call the computed `system_addr(staging)`.
4. Send `cat flag.txt` or another command as the second line so `gets()` writes it into `staging`.

---

## Why The Leak Works

The GOT entry for `puts` holds the real libc address of `puts` after relocation.
When `puts(puts@got)` runs, the program prints the raw bytes stored at that GOT entry.
That gives you the actual libc pointer value in little-endian form.

Once you know one libc function address, the rest is arithmetic:

$$
\text{libc\_base} = \text{leaked\_puts} - \text{puts\_offset}
$$

$$
\text{system\_addr} = \text{libc\_base} + \text{system\_offset}
$$

---

## Payload Shapes

### Stage 1: Leak `puts`

```
[24 bytes padding]
[puts@plt]
[popret]
[puts@got]
[service]
```

This calls `puts(puts@got)` and then returns to `service` so you get a second chance to send input.

### Stage 2: Stage Command And Execute It

```
[24 bytes padding]
[gets@plt]
[popret]
[staging]
[system_addr]
[exit@plt]
[staging]
```

After the ROP chain starts, the next line of input becomes the command string stored in `staging`.

---

## Using The Script

### Compile The Binary

```bash
cd /home/jbenjam7/cs466/ctf/14-ret2libc-practice
gcc challenge.c -o challenge -fno-stack-protector -no-pie -m32
```

### Run The Exploit

```bash
python3 exploit.py
```

### Run A Different Command

```bash
python3 exploit.py --command "ls -la"
```

---

## Manual Reasoning Checklist

If you want to solve it by hand, verify these steps in order:

1. Confirm the overflow reaches the return address after 24 bytes.
2. Confirm `puts@plt`, `puts@got`, `gets@plt`, and `exit@plt` exist in the binary.
3. Leak `puts` from the GOT and compute the libc base.
4. Resolve `system()` from that libc base.
5. Re-enter the vulnerable function and run the second ROP chain.
6. Send the command string as the next line so `gets()` writes it into `staging`.

---

## Common Mistakes

- Forgetting that the first leak is a raw libc pointer, not a string.
- Using the wrong libc offsets for the installed environment.
- Skipping the stack-cleanup gadget between chained calls.
- Forgetting that the command string must arrive after the second `gets()` begins.
- Assuming the same addresses will work if the binary is rebuilt differently.

---

## One-Line Takeaway

Ret2libc is just stack control plus libc math: leak one function pointer, compute the base, then call `system()` with a string you staged yourself.
