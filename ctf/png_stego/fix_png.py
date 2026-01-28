#!/usr/bin/env python3

# Read the corrupted PNG
with open('answer.png', 'rb') as f:
    data = bytearray(f.read())

# The correct PNG signature is: 89 50 4E 47 0D 0A 1A 0A
print("Original header:", ' '.join(f'{data[i]:02x}' for i in range(8)))

# Fix all four corrupted bytes
data[4] = 0x0D
data[5] = 0x0A
data[6] = 0x1A
data[7] = 0x0A

print("Fixed header:   ", ' '.join(f'{data[i]:02x}' for i in range(8)))

# Write the fixed file
with open('fixed.png', 'wb') as f:
    f.write(data)

print("\nPNG header fixed!")
