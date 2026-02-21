#!/usr/bin/env python3
"""
Detect and extract flag from cyan lines in Image 2
"""
from PIL import Image
import numpy as np

img2 = Image.open("min-kao-eecs-building-1024x640-2.jpeg")
arr2 = np.array(img2.convert('RGB'))

# Find bright cyan pixels (high G and B, lower R)
# Pure cyan: (0, 255, 255) but might have variations
cyan_pixels = []

for y in range(arr2.shape[0]):
    for x in range(arr2.shape[1]):
        r, g, b = arr2[y, x]
        # Check for cyan: high G and B, low R
        if r < 150 and g > 200 and b > 200:
            cyan_pixels.append((x, y, r, g, b))

print(f"Found {len(cyan_pixels)} cyan pixels")

# Group by Y coordinate
from collections import defaultdict
lines = defaultdict(list)
for x, y, r, g, b in cyan_pixels:
    lines[y].append((x, r, g, b))

print(f"\nCyan pixels found at {len(lines)} different Y coordinates")

# Extract flag from each line
for y in sorted(lines.keys()):
    pixels = sorted(lines[y], key=lambda p: p[0])  # Sort by X
    print(f"\nLine at Y={y}: {len(pixels)} pixels")
    
    # Try different decoding methods
    # Method 1: R values as ASCII
    flag_chars = []
    for x, r, g, b in pixels:
        if 32 <= r <= 126:  # Printable ASCII
            flag_chars.append(chr(r))
    if flag_chars:
        print(f"  R-channel ASCII: {''.join(flag_chars[:50])}")
    
    # Method 2: All channels as ASCII
    all_chars = []
    for x, r, g, b in pixels:
        for val in [r, g, b]:
            if 32 <= val <= 126:
                all_chars.append(chr(val))
    if all_chars:
        print(f"  All channels: {''.join(all_chars[:50])}")
