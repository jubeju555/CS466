#!/usr/bin/env python3
from PIL import Image
import re

img = Image.open('fixed3.png')
pixels = img.load()
width, height = img.size

print(f'Image size: {width}x{height}')

# Try different LSB extraction methods
methods = [
    ("RGB, MSB first", lambda r,g,b: [(r&1), (g&1), (b&1)]),
    ("RGB, LSB last", lambda r,g,b: [(r>>7)&1, (g>>7)&1, (b>>7)&1]),
    ("Red channel only", lambda r,g,b: [(r&1)]),
    ("Green channel only", lambda r,g,b: [(g&1)]),  
    ("Blue channel only", lambda r,g,b: [(b&1)]),
    ("Reverse RGB", lambda r,g,b: [(b&1), (g&1), (r&1)]),
]

for method_name, extractor in methods:
    bits = []
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y][:3]
            bits.extend(extractor(r, g, b))
    
    # Convert to bytes
    bytes_data = []
    for i in range(0, len(bits)-8, 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        bytes_data.append(byte)
    
    result = bytes(bytes_data)
    text = result.decode('ascii', errors='ignore')
    
    # Look for readable content or flags
    flags = re.findall(r'[a-zA-Z_]{3,}\{[^}]+\}', text)
    if flags or len([c for c in text[:100] if c.isprintable() and c != '\x00']) > 50:
        print(f"\n{'='*60}")
        print(f"METHOD: {method_name}")
        print(f"{'='*60}")
        print(f"First 200 chars: {text[:200]}")
        if flags:
            print(f"\nFLAGS FOUND:")
            for flag in flags[:5]:
                print(f"  {flag}")
