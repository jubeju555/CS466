#!/usr/bin/env python3
"""
Extract the CTF flag from the 0-stack-unstripped binary
by decoding the hex values stored on the stack.
"""

import struct

def extract_flag():
    """Extract and decode the flag from hex values"""
    
    # These hex values are from the disassembly of main function
    # They represent the flag stored on the stack in little-endian format
    stack_values = [
        (0x8f, 0x63736f63),  # ebp-0x8f: "cosc"
        (0x8b, 0x2d363634),  # ebp-0x8b: "466-"
        (0x87, 0x67616c66),  # ebp-0x87: "flag"
        (0x83, 0x32727b2d),  # ebp-0x83: "-{r2"
        (0x7b, 0x71635070),  # ebp-0x7b: "Ppqc"  (note: gap in offsets)
        (0x77, 0x7d6532),    # ebp-0x77: "2e}"
    ]
    
    flag = ""
    
    for offset, hex_value in stack_values:
        # Determine the size of the value
        if hex_value <= 0xffffff:  # 3-byte value
            num_bytes = 3
        else:  # 4-byte value
            num_bytes = 4
        
        # Convert to little-endian bytes
        bytes_val = struct.pack("<I", hex_value)[:num_bytes]
        
        # Decode to ASCII and append to flag
        try:
            decoded = bytes_val.decode('ascii')
            flag += decoded
            print(f"  ebp-0x{offset:02x}: 0x{hex_value:08x} -> '{decoded}'")
        except UnicodeDecodeError:
            print(f"  ebp-0x{offset:02x}: 0x{hex_value:08x} -> [decode error]")
    
    return flag

if __name__ == "__main__":
    print("Extracting flag from stack values...\n")
    flag = extract_flag()
    print(f"\n🚩 FLAG: {flag}")
