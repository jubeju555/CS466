#!/usr/bin/env python3
"""
Compare two images byte-by-byte to find hidden data.
The hint says "the line is broken" - looking for differences.
"""

import sys

def compare_images(file1, file2):
    """Compare two images byte by byte and extract differences."""
    with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
        data1 = f1.read()
        data2 = f2.read()
    
    print(f"File 1 size: {len(data1)} bytes")
    print(f"File 2 size: {len(data2)} bytes")
    
    # Find all differences
    differences = []
    max_len = max(len(data1), len(data2))
    
    for i in range(max_len):
        byte1 = data1[i] if i < len(data1) else None
        byte2 = data2[i] if i < len(data2) else None
        
        if byte1 != byte2:
            differences.append((i, byte1, byte2))
    
    print(f"\nFound {len(differences)} different bytes")
    
    if len(differences) > 0 and len(differences) <= 1000:
        print("\nDifferences (offset, byte1, byte2):")
        for i, (offset, b1, b2) in enumerate(differences[:100]):  # Show first 100
            print(f"  Offset {offset}: {b1 if b1 is not None else 'None'} -> {b2 if b2 is not None else 'None'} (0x{b1:02x} -> 0x{b2:02x})" if b1 is not None and b2 is not None else f"  Offset {offset}: {b1} -> {b2}")
            if i >= 99 and len(differences) > 100:
                print(f"  ... and {len(differences) - 100} more differences")
                break
    
    # Try to extract ASCII characters from differences
    print("\n--- Attempting to extract hidden message ---")
    
    # Method 1: XOR the different bytes
    print("\nMethod 1: XOR of different bytes:")
    xor_chars = []
    for offset, b1, b2 in differences:
        if b1 is not None and b2 is not None:
            xor_val = b1 ^ b2
            if 32 <= xor_val <= 126:  # Printable ASCII
                xor_chars.append(chr(xor_val))
            else:
                xor_chars.append('.')
    xor_result = ''.join(xor_chars)
    print(f"XOR result: {xor_result}")
    
    # Method 2: Just the different bytes from file2
    print("\nMethod 2: Different bytes from file 2:")
    diff_chars = []
    for offset, b1, b2 in differences:
        if b2 is not None:
            if 32 <= b2 <= 126:
                diff_chars.append(chr(b2))
            else:
                diff_chars.append('.')
    diff_result = ''.join(diff_chars)
    print(f"File2 diffs: {diff_result}")
    
    # Method 3: Different bytes from file1
    print("\nMethod 3: Different bytes from file 1:")
    diff_chars1 = []
    for offset, b1, b2 in differences:
        if b1 is not None:
            if 32 <= b1 <= 126:
                diff_chars1.append(chr(b1))
            else:
                diff_chars1.append('.')
    diff_result1 = ''.join(diff_chars1)
    print(f"File1 diffs: {diff_result1}")
    
    # Method 4: Look for pattern in LSBs
    print("\nMethod 4: LSB differences:")
    lsb_bits = []
    for offset, b1, b2 in differences:
        if b1 is not None and b2 is not None:
            lsb_bits.append(str(b2 & 1))
    
    # Convert bits to characters
    if len(lsb_bits) >= 8:
        lsb_chars = []
        for i in range(0, len(lsb_bits) - 7, 8):
            byte_str = ''.join(lsb_bits[i:i+8])
            byte_val = int(byte_str, 2)
            if 32 <= byte_val <= 126:
                lsb_chars.append(chr(byte_val))
            else:
                lsb_chars.append('.')
        print(f"LSB extraction: {''.join(lsb_chars)}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_images.py <image1> <image2>")
        sys.exit(1)
    
    compare_images(sys.argv[1], sys.argv[2])
