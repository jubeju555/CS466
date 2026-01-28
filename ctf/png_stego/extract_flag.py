#!/usr/bin/env python3
from PIL import Image

# Open the fixed PNG
img = Image.open('fixed.png')
pixels = img.load()
width, height = img.size

# Extract LSBs from each RGB channel
bits = []
for y in range(height):
    for x in range(width):
        r, g, b = pixels[x, y][:3]  # Get RGB values (ignore alpha if present)
        bits.append(r & 1)  # LSB of red
        bits.append(g & 1)  # LSB of green
        bits.append(b & 1)  # LSB of blue

# Convert bits to bytes
bytes_data = []
for i in range(0, len(bits), 8):
    if i + 8 <= len(bits):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        bytes_data.append(byte)

# Convert to string and find printable content
result = bytes(bytes_data)

# Try to find the flag (usually starts with a known format like "flag{" or similar)
try:
    text = result.decode('ascii', errors='ignore')
    print("Extracted text:")
    print(text[:1000])  # Print first 1000 chars
    
    # Look for common flag patterns
    if 'flag{' in text.lower() or 'ctf{' in text.lower() or 'utk{' in text.lower():
        start = text.lower().find('flag{')
        if start == -1:
            start = text.lower().find('ctf{')
        if start == -1:
            start = text.lower().find('utk{')
        if start != -1:
            end = text.find('}', start) + 1
            print(f"\n\nFLAG FOUND: {text[start:end]}")
except Exception as e:
    print(f"Error decoding: {e}")
    print("Raw bytes (first 200):", result[:200])
