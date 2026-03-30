# formatstring3 Walkthrough (Format String Exploit)

## Challenge Overview

**Binary**: `login`  
**Vulnerability**: User input is used directly in `printf()` as a format string  
**Goal**: Overwrite the global variable `utk_password` to unlock the flag  
**Constraint**: Only 128 bytes of input allowed

### TL;DR: What You're Doing
1. **Leak**: Use format strings to read values from the stack
2. **Write**: Use format strings to write a value to a specific memory address
3. **Win**: Change the password variable to unlock the flag

## Part 1: How The Vulnerability Works

### The Source Code
```c
int utk_password = 0x12341234;  // Global variable we need to change

int myutk_login(char *kim_password) {
	printf(kim_password);  // ❌ BUG: treats user input as format string!
	printf("%x %p\n", utk_password, &utk_password);  // Prints the current value and address
	if (utk_password == 0xD0C0FFEE) {
        system("cat flag.txt");  // ✅ Flag appears if we change the value
	}
}
```

### Why This Is a Security Problem
- `printf()` normally expects TWO things: a format string AND values to print
- This code only receives user input (no separate format args)
- So the program treats the user input ITSELF as the format string
- Format string codes like `%x` and `%hn` let us leak/write memory

### What We Can Do
- **`%x`** - Read a value from the stack   
- **`%5$hn`** - Write a 2-byte value to a memory address (we'll explain the "5$" part next)

## Part 2: Understanding `%5$hn` (The Magic Format String)

### What Each Part Means
- **`%`** - Start of a format code
- **`5$`** - Look at the 5th argument on the stack (not the 1st, 2nd, etc.)
- **`hn`** - Write 2 bytes (16 bits) to the address pointed to by that argument

### How We Use It
Here's the key insight: When we send a payload like this:
```
[4-byte address][padding][%5$hn]
```

The program:
1. Puts our input on the stack
2. The first 4 bytes (the address) becomes the 1st argument
3. `%5$hn` reaches the 5th argument position and writes to that address
4. **How much does it write?** Whatever the byte count of our payload is!

**Example**: If payload is 119 bytes total, it writes the value `119` (0x77) to the target address.

### Finding Position 5
You can use GDB to verify this, but the script already knows position 5 works.

## Part 3: The 128-Byte Limitation Challenge

### The Problem
Your input is limited to **128 bytes** total. Let's see what that means:

- **4 bytes** = The target address
- **5 bytes** = The format string `%5$hn`
- **1 byte** = The newline at the end
- **Remaining** = 128 - 4 - 5 - 1 = **118 bytes** can be padding

Since the amount written is equal to payload size, you can only write values up to ~118-127.

### Why This Matters
The target value is `0xD0C0FFEE` (about 3.5 billion!) — way too large to fit in 128 bytes. So we **can't solve this directly**. The challenge is a **proof of concept** — it demonstrates the technique works, even if we can't reach the final goal.

### What We Can Actually Do
Write a small value to prove the memory write works (the script uses value `119`)

## Part 4: The Python Exploit Script Explained

### Step 1: `leak_stack_value()` - Read Memory
```python
payload = b"LEAK%5$x\n"
```
This uses `%5$x` to **read** the 5th stack argument and print it in hex. It doesn't write anything — just shows what's there.

### Step 2: `write_value_to_memory()` - Write Memory
```python
payload = addr + (b'X' * pad_size) + b"%5$hn\n"
```
This creates a payload that:
1. Puts the target address first (4 bytes)
2. Pads with junk bytes to reach the desired payload size
3. Ends with `%5$hn` to trigger the write
4. The write value = total payload size in bytes

**Example for value 119:**
- Address: 4 bytes (0x80e6048)
- Padding: 110 bytes of 'X'
- Format string: 5 bytes (%5$hn)
- Newline: 1 byte
- **Total: 120 bytes** → Writes 120 to memory

### How to Run It
```bash
cd /home/jbenjam7/cs466/ctf/formatstring3

# Just leak a value
python3 exploit_fs3.py leak

# Write a specific value (e.g., 100)
python3 exploit_fs3.py write 100

# Run both leak and write
python3 exploit_fs3.py test
        print(f"Output: {line}")
        # Shows: 12340077 (wrote 0x0077 = 119 to low word)
PYEOF
```

### Verification Output

```
What's Dr. Kim's password for MyUTK?
JXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX XXXXX12340077 0x80e6048
Wrong Dr. Kim's password. You are't allowed to log in to his MyUTK
```

Value changed from `0x12341234` to `0x12340077` ✓ Write confirmed working!

## Part 5: Remote Testing

### Target Information

- **Host**: moa6.eecs.utk.edu
- **Port**: 32130
- Same binary, same vulnerability

### Quick Test

```bash
python3 << 'PYEOF'
import struct, socket

TARGET_ADDR = 0x80e6048
addr = struct.pack('<I', TARGET_ADDR)
```

## Summary: Understanding the Challenge

### What the Script Does

**`exploit_fs3.py`** has two main functions:

1. **`leak_stack_value()`** - Reads memory using `%5$x`
   - Just shows Stack values to prove we can read memory
   - Doesn't change anything

2. **`write_value_to_memory(value)`** - Writes memory using `%5$hn`
   - Puts target address first
   - Pads to desired payload size
   - Triggers the write with `%5$hn`
   - The value written = payload size in bytes

### The Core Exploit Steps

1. **Identify the target**: The program tells you the address (`0x80e6048`)
2. **Calculate payload size**: What value do you want to write?
3. **Build the payload**: `[address][padding][format_string]`
4. **Send it**: Program writes the payload size to the target address
5. **Check result**: The memory changes!

### Why We Can't Reach the Final Goal

- We can only write values 1-127 (limited by 128-byte buffer)
- The target value is 0xD0C0FFEE (about 3.5 billion)
- This is a **proof of concept** — we demonstrate the technique works with small values

### Quick Test

```bash
cd /home/jbenjam7/cs466/ctf/formatstring3
python3 exploit_fs3.py write 119
```

You should see the password value change from `0x12341234` towards `0x12340077` (119 in hex = 0x77).
