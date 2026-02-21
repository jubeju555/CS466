#!/usr/bin/env python3
"""
Script to extract a hidden flag from two nearly identical PNG images.
The flag is encoded in horizontal colored lines that differ between the images.
"""

from PIL import Image
import numpy as np

# Step 1: Load both images
print("Step 1: Loading images...")
image1_path = "image1.jpg"  # Original image
image2_path = "image2.jpeg"  # Image with hidden lines

img1 = Image.open(image1_path).convert('RGB')
img2 = Image.open(image2_path).convert('RGB')

# Convert images to numpy arrays for easier pixel manipulation
arr1 = np.array(img1)
arr2 = np.array(img2)

print(f"Image dimensions: {arr1.shape}")

# Step 2: Compare images pixel by pixel to find differences
print("\nStep 2: Comparing images to find differing pixels...")

# Find all pixels that differ between the two images
diff_pixels = []
for y in range(arr1.shape[0]):
    for x in range(arr1.shape[1]):
        r1, g1, b1 = arr1[y, x]
        r2, g2, b2 = arr2[y, x]
        
        # Check if pixels differ (allowing small tolerance for compression artifacts)
        if abs(int(r1) - int(r2)) > 10 or abs(int(g1) - int(g2)) > 10 or abs(int(b1) - int(b2)) > 10:
            diff_pixels.append((y, x, r2, g2, b2))

print(f"Found {len(diff_pixels)} differing pixels")

# Step 3: Identify rows containing horizontal lines
print("\nStep 3: Identifying rows with horizontal lines...")

# Count pixels per row to find which rows have significant differences
row_counts = {}
for y, x, r, g, b in diff_pixels:
    row_counts[y] = row_counts.get(y, 0) + 1

# Find rows with many differing pixels (indicating horizontal lines)
significant_rows = [(y, count) for y, count in row_counts.items() if count > 50]
significant_rows.sort(key=lambda x: x[0])  # Sort by row number

print(f"Found {len(significant_rows)} rows with horizontal lines:")
for y, count in significant_rows:
    print(f"  Row {y}: {count} pixels")

# Step 4: Analyze colors and determine bit mapping
print("\nStep 4: Analyzing colors and determining bit mapping...")

# Get all differing pixels from significant rows, sorted left-to-right, top-to-bottom
line_pixels = [(y, x, r, g, b) for y, x, r, g, b in diff_pixels if y in [row[0] for row in significant_rows]]
line_pixels.sort(key=lambda p: (p[0], p[1]))  # Sort by row, then column

# Analyze the colors present
colors = {}
for y, x, r, g, b in line_pixels:
    color_key = (r, g, b)
    colors[color_key] = colors.get(color_key, 0) + 1

print(f"Found {len(colors)} distinct colors in the lines:")
for color, count in sorted(colors.items(), key=lambda x: x[1], reverse=True)[:10]:
    r, g, b = color
    print(f"  RGB({r:3d}, {g:3d}, {b:3d}): {count:4d} pixels")

# Determine which color represents 0 and which represents 1
# Strategy: Use color channel dominance
# Blue-dominant (B > G and B > R) = 0
# Green-dominant (G > B and G > R) = 1
def color_to_bit(r, g, b):
    """Convert RGB color to binary bit based on dominant channel."""
    if b > g and b > r:
        return 0  # Blue = 0
    elif g > b and g > r:
        return 1  # Green = 1
    else:
        # Fallback: use G vs B comparison
        return 1 if g > b else 0

print("\nColor-to-bit mapping:")
print("  Blue-dominant (B > G and B > R) -> 0")
print("  Green-dominant (G > B and G > R) -> 1")

# Step 5: Convert pixels to bits (left-to-right, top-to-bottom)
print("\nStep 5: Converting pixels to bits...")

bits = []
for y, x, r, g, b in line_pixels:
    bit = color_to_bit(r, g, b)
    bits.append(bit)

print(f"Extracted {len(bits)} bits from the colored lines")
print(f"First 64 bits: {''.join(map(str, bits[:64]))}")

# Step 6: Convert every 8 bits to ASCII characters
print("\nStep 6: Converting bits to ASCII characters...")

def bits_to_text(bit_array, msb_first=True):
    """Convert array of bits to ASCII text."""
    chars = []
    for i in range(0, len(bit_array) - 7, 8):
        if msb_first:
            # MSB first (left bit is most significant)
            byte_value = 0
            for j in range(8):
                byte_value = (byte_value << 1) | bit_array[i + j]
        else:
            # LSB first (right bit is most significant)
            byte_value = 0
            for j in range(8):
                byte_value = byte_value | (bit_array[i + j] << j)
        
        # Convert to ASCII character if printable
        if 32 <= byte_value <= 126:
            chars.append(chr(byte_value))
        elif byte_value == 0:  # Null terminator
            break
        else:
            chars.append('?')  # Non-printable character
    
    return ''.join(chars)

# Try MSB-first (standard)
flag_text_msb = bits_to_text(bits, msb_first=True)
print(f"\nMSB-first extraction ({len(flag_text_msb)} chars):")
print(flag_text_msb[:200])

# Try LSB-first (alternative)
flag_text_lsb = bits_to_text(bits, msb_first=False)
print(f"\nLSB-first extraction ({len(flag_text_lsb)} chars):")
print(flag_text_lsb[:200])

# Step 7: Find and print the flag
print("\n" + "="*70)
print("Step 7: SEARCHING FOR FLAG")
print("="*70)

def extract_flag(text):
    """Extract flag{...} pattern from text."""
    text_lower = text.lower()
    if 'flag{' in text_lower:
        start_idx = text_lower.index('flag{')
        end_idx = text.find('}', start_idx)
        if end_idx != -1:
            return text[start_idx:end_idx+1]
    return None

# Check MSB-first
flag_msb = extract_flag(flag_text_msb)
if flag_msb:
    print("\n🎉 FLAG FOUND (MSB-first):")
    print(flag_msb)
else:
    print("No flag pattern found in MSB-first extraction")

# Check LSB-first
flag_lsb = extract_flag(flag_text_lsb)
if flag_lsb:
    print("\n🎉 FLAG FOUND (LSB-first):")
    print(flag_lsb)
else:
    print("No flag pattern found in LSB-first extraction")

# If no flag found, print more context
if not flag_msb and not flag_lsb:
    print("\n⚠️ No 'flag{' pattern found. Full extracted text:")
    print("\nMSB-first (first 500 chars):")
    print(flag_text_msb[:500])
    print("\nLSB-first (first 500 chars):")
    print(flag_text_lsb[:500])
