# CTF Challenge: 0-stack-stripped Walkthrough

## Overview
This is a stripped binary challenge where the flag is constructed on the stack, but unlike the unstripped version, this binary has had its symbol table removed, making it more challenging to analyze.

## Step 1: Identify the Binary Type

```bash
file 0-stack-stripped
```
Output: `ELF 32-bit LSB executable, Intel 80386, version 1 (SYSV), dynamically linked, interpreter /lib/ld-linux.so.2, for GNU/Linux 3.2.0, stripped`

**Key difference**: Notice it says **"stripped"** - this means no debugging symbols or function names.

## Step 2: Find the Main Function

In a stripped binary, you need to manually find where main is located.

### Method 1: Using readelf and objdump

```bash
# Find the entry point address
readelf -h 0-stack-stripped | grep Entry
```
Output: `Entry point address: 0x8049190`

```bash
# Disassemble from entry point
objdump -d -M intel 0-stack-stripped | grep -A 30 "8049190"
```

Look for the `call __libc_start_main@plt` instruction. Just before this call, the address of main is pushed onto the stack. In this binary:

```assembly
80491ac:  lea    eax,[ebx-0x2e37]
80491b2:  push   eax                    # This pushes main's address
80491b3:  call   8049040 <__libc_start_main@plt>
```

### Method 2: Look for the jump at the end of _start

Near the entry point, look for a jump instruction:
```assembly
80491bd:  jmp    8049090
```

This jumps to **0x8049090**, which is main!

## Step 3: Disassemble Main Function

```bash
objdump -d -M intel 0-stack-stripped | grep -A 80 "^08049090"
```

### Key Assembly Instructions

The flag is being constructed on the stack:

```assembly
80490cb:  mov    DWORD PTR [ebp-0x8f],0x63736f63
80490d5:  mov    DWORD PTR [ebp-0x8b],0x2d363634
80490df:  mov    DWORD PTR [ebp-0x87],0x67616c66
80490e9:  mov    DWORD PTR [ebp-0x83],0x31527b2d
80490f3:  mov    DWORD PTR [ebp-0x7b],0x70705050
80490fa:  mov    DWORD PTR [ebp-0x77],0x7d6550
```

## Step 4: Decode the Flag

Remember: x86 is **little-endian**, so bytes are stored in reverse order!

### Decoding Each DWORD:

**Address ebp-0x8f:** `0x63736f63`
- Bytes: `63 73 6f 63`
- Little-endian reversal: `63 6f 73 63`
- ASCII: **"cosc"**

**Address ebp-0x8b:** `0x2d363634`
- Bytes: `2d 36 36 34`
- Little-endian reversal: `34 36 36 2d`
- ASCII: **"466-"**

**Address ebp-0x87:** `0x67616c66`
- Bytes: `67 61 6c 66`
- Little-endian reversal: `66 6c 61 67`
- ASCII: **"flag"**

**Address ebp-0x83:** `0x31527b2d`
- Bytes: `31 52 7b 2d`
- Little-endian reversal: `2d 7b 52 31`
- ASCII: **"-{R1"**

**Address ebp-0x7b:** `0x70705050`
- Bytes: `70 70 50 50`
- Little-endian reversal: `50 50 70 70`
- ASCII: **"PPpp"**

**Address ebp-0x77:** `0x7d6550`
- Bytes: `7d 65 50` (only 3 bytes)
- Little-endian reversal: `50 65 7d`
- ASCII: **"Pe}"**

### Assembling the Flag:

Reading from lowest address to highest:
- ebp-0x8f: "cosc"
- ebp-0x8b: "466-"
- ebp-0x87: "flag"
- ebp-0x83: "-{R1"
- ebp-0x7b: "PPpp"
- ebp-0x77: "Pe}"

## The Flag

```
cosc466-flag-{R1PPppPe}
```

## Step 5: Using GDB (Alternative Method)

Even though the binary is stripped, you can still use GDB with addresses:

```bash
gdb -batch -ex "set disassembly-flavor intel" -ex "x/50i 0x8049090" 0-stack-stripped
```

This will disassemble 50 instructions starting at main's address (0x8049090).

## Key Takeaways

1. **Finding Main**: In stripped binaries, follow the entry point → find `__libc_start_main` call → identify main address
2. **objdump vs GDB**: objdump works well for static analysis of stripped binaries
3. **Same Technique**: The flag extraction method is identical to unstripped binaries
4. **Different Flag**: Each challenge has a unique flag hardcoded in the binary
5. **Little-Endian**: Always remember to reverse the byte order when decoding hex values on x86

## Comparison with Unstripped Binary

| Feature | Unstripped | Stripped |
|---------|-----------|----------|
| Symbol Table | ✅ Present | ❌ Removed |
| Function Names | ✅ Visible | ❌ Hidden |
| Finding Main | Easy (`disassemble main`) | Manual (follow entry point) |
| Debugging | Easier | Harder |
| Flag Extraction | Same technique | Same technique |
| Flag Value | `cosc466-flag-{r2Ppqc2e}` | `cosc466-flag-{R1PPppPe}` |

## Python Decoder Script

```python
#!/usr/bin/env python3
import struct

# Hex values from the stripped binary
stack_values = [
    (0x8f, 0x63736f63),  # "cosc"
    (0x8b, 0x2d363634),  # "466-"
    (0x87, 0x67616c66),  # "flag"
    (0x83, 0x31527b2d),  # "-{R1"
    (0x7b, 0x70705050),  # "PPpp"
    (0x77, 0x7d6550),    # "Pe}"
]

flag = ""
for offset, hex_value in stack_values:
    if hex_value <= 0xffffff:
        num_bytes = 3
    else:
        num_bytes = 4
    
    bytes_val = struct.pack("<I", hex_value)[:num_bytes]
    decoded = bytes_val.decode('ascii')
    flag += decoded
    print(f"  ebp-0x{offset:02x}: 0x{hex_value:08x} -> '{decoded}'")

print(f"\n🚩 FLAG: {flag}")
```
