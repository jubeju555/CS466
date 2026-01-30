#!/usr/bin/env python3
from PIL import Image
import numpy as np
import sys

# Load the two images
# Image 1 is already saved, Image 2 needs to be created from attachment
img1_path = "min-kao-eecs-building-1024x640-1.jpeg"
img2_path = "min-kao-eecs-building-1024x640-2.jpeg"

try:
    img1 = Image.open(img1_path)
    img2 = Image.open(img2_path)
    
    print(f"Image 1: {img1.size} {img1.format}")
    print(f"Image 2: {img2.size} {img2.format}")
    
    # Convert to numpy arrays for comparison
    arr1 = np.array(img1)
    arr2 = np.array(img2)
    
    # Find differences
    diff = arr1.astype(int) - arr2.astype(int)
    
    # Get statistics about differences
    abs_diff = np.abs(diff)
    
    print(f"\nDifference Statistics:")
    print(f"Max difference: {np.max(abs_diff)}")
    print(f"Mean difference: {np.mean(abs_diff):.2f}")
    print(f"Pixels with any difference: {np.count_nonzero(abs_diff)}")
    
    # Find pixels with significant differences (threshold > 5)
    threshold = 5
    significant_diff = np.where(abs_diff > threshold)
    
    if len(significant_diff[0]) > 0:
        print(f"\nPixels with difference > {threshold}:")
        print(f"Found {len(significant_diff[0])} different pixels")
        
        # Get bounding box of differences
        y_coords = significant_diff[0]
        x_coords = significant_diff[1]
        
        print(f"Y range: {y_coords.min()} to {y_coords.max()}")
        print(f"X range: {x_coords.min()} to {x_coords.max()}")
        
        # Show some specific differences
        for i in range(min(10, len(y_coords))):
            y, x = y_coords[i], x_coords[i]
            print(f"  Pixel ({x}, {y}): {arr1[y,x]} vs {arr2[y,x]}")
    
    # Try to locate specific changes visually
    # Create a difference map
    diff_img = Image.fromarray((abs_diff[:,:,0:3].mean(axis=2)).astype(np.uint8))
    diff_img.save("difference_map.png")
    print("\nDifference map saved as difference_map.png")
    
    # Check if there's a line or specific feature difference
    # The "10 0 0" hint might refer to a line at pixel position 10 or similar
    
except FileNotFoundError as e:
    print(f"Error: {e}")
    print("Make sure both images are in the current directory")
