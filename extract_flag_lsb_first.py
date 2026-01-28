#!/usr/bin/env python3
from PIL import Image
import re

img = Image.open('fixed3.png')
pixels = img.load()
width, height = img.size

print(f'Image size: {width}x{height}')

# Extract LSBs and try different byte orderings
bits = []
for y in range(height):
    for x in range(width):
        r, g, b, a = pixels[x, y]
        bits.append(r & 1)
        bits.append(g & 1)
        bits.append(b & 1)

print(f"Total bits extracted: {len(bits)}")

# Try LSB-last bit ordering (reverse each byte)
bytes_data = []
for i in range(0, len(bits)-8, 8):
    byte = 0
    for j in range(8):
        byte = byte | (bits[i+j] << j)  # LSB-first ordering
    bytes_data.append(byte)

result = bytes(bytes_data)

# Try to find printable ASCII
print("\nFirst 100 bytes (as hex):")
print(' '.join(f'{b:02x}' for b in result[:100]))

print("\nFirst 300 chars (with replacements for non-printable):")
text = result.decode('latin-1')
display = ''.join(c if c.isprintable() else '.' for c in text[:300])
print(display)

# Look for common flag formats
patterns = [r'flag\{[^}]+\}', r'FLAG\{[^}]+\}', r'UTK\{[^}]+\}', r'utk\{[^}]+\}', r'CTF\{[^}]+\}']
for pattern in patterns:
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        print(f"\n*** FOUND with pattern {pattern}: ***")
        for m in matches:
            print(f"  {m}")
