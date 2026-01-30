# CTF Challenge: 0-stack-unstripped Walkthrough

## Overview
This is a stack-based CTF challenge where the flag is constructed on the stack and you need to use GDB to extract it.

## Step 1: Analyze the Binary

First, let's check what type of file we're dealing with:
```bash
file 0-stack-unstripped
# Output: ELF 32-bit LSB executable, Intel 80386
```

## Step 2: Understand the Code Flow

Using GDB, we can disassemble the main function:
```bash
gdb -batch -ex "set disassembly-flavor intel" -ex "disassemble main" 0-stack-unstripped
```

### Key Assembly Instructions

Looking at the disassembly, we see the flag being built on the stack:

```assembly
0x080490c4 <+52>:    mov    DWORD PTR [ebp-0x7f],0x71635070  ; "Pcq" (in reverse)
0x080490cb <+59>:    mov    DWORD PTR [ebp-0x8f],0x63736f63  ; "cosc"
0x080490d5 <+69>:    mov    DWORD PTR [ebp-0x8b],0x2d363634  ; "466-"
0x080490df <+79>:    mov    DWORD PTR [ebp-0x87],0x67616c66  ; "flag"
0x080490e9 <+89>:    mov    DWORD PTR [ebp-0x83],0x32727b2d  ; "-{r2"
0x080490f3 <+99>:    mov    DWORD PTR [ebp-0x7b],0x63715070  ; "Ppqc"
0x080490fa <+106>:   mov    DWORD PTR [ebp-0x77],0x7d6532    ; "2e}"
```

## Step 3: Extract the Flag Using GDB

### Method 1: Set a breakpoint and examine memory

```bash
gdb -q 0-stack-unstripped
```

Inside GDB:
```gdb
# Set a breakpoint after the stack is set up but before scanf
break *main+127

# Run the program
run

# Examine the memory where the flag is stored
x/s $ebp-0x8f

# Or examine as a string starting from the beginning
x/30c $ebp-0x8f
```

### Method 2: Use Python in GDB to decode

```bash
gdb -q 0-stack-unstripped
```

Inside GDB:
```gdb
break *main+127
run

# Print the values
x/7wx $ebp-0x8f
```

## Step 4: Decode the Flag Manually

The values are stored in little-endian format (x86 architecture). Let's decode each DWORD:

- `0x63736f63` → bytes: 63 73 6f 63 → ASCII: "cosc"
- `0x2d363634` → bytes: 2d 36 36 34 → ASCII: "466-"
- `0x67616c66` → bytes: 67 61 6c 66 → ASCII: "flag"
- `0x32727b2d` → bytes: 32 72 7b 2d → ASCII: "-{r2"
- `0x71635070` → bytes: 71 63 50 70 → ASCII: "Ppqc"
- `0x7d6532` → bytes: 7d 65 32 → ASCII: "2e}"

Reading these in order from the stack addresses (ebp-0x8f to ebp-0x77):

**cosc466-flag-{r2Ppqc2e}**

## The Flag

```
cosc466-flag-{r2Ppqc2e}
```

## Alternative: Quick Python Script

You can also extract this with a Python script:

```python
import struct

# The hex values from the assembly
values = [
    0x63736f63,  # ebp-0x8f
    0x2d363634,  # ebp-0x8b
    0x67616c66,  # ebp-0x87
    0x32727b2d,  # ebp-0x83
    0x71635070,  # ebp-0x7b (note: gap in addresses)
    0x7d6532,    # ebp-0x77
]

flag = ""
for val in values:
    # Convert to little-endian bytes and decode
    if val <= 0xffffff:  # 3-byte value
        bytes_val = struct.pack("<I", val)[:3]
    else:  # 4-byte value
        bytes_val = struct.pack("<I", val)
    flag += bytes_val.decode('ascii')

print(f"Flag: {flag}")
```

## Key Takeaways

1. **Stack Analysis**: The flag was stored on the stack as multiple DWORD values
2. **Little-Endian**: x86 architecture stores values in little-endian format, so bytes are reversed
3. **Memory Layout**: Understanding memory offsets (ebp-0x8f, ebp-0x8b, etc.) helps reconstruct the string
4. **GDB Breakpoints**: Setting breakpoints before user input allows inspection of hardcoded values
