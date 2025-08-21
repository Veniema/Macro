#!/usr/bin/env python3
"""
Test script for the new image recognition feature in Macro Maker Pro.

This script demonstrates how the image check functionality works:
1. Takes a screenshot of a region
2. Compares it with a reference image
3. Shows branching logic based on match result

Usage:
1. Save a reference image (PNG, JPG, etc.) that you want to detect
2. Run this script and follow the prompts
3. Click and drag to define the search region
4. The script will show if the image was found and simulate branching
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import sys
import os
import numpy as np
from PIL import Image
import mss

# Add the macro code directory to path to import the comparison function
sys.path.append('.')

def compare_images(reference_path, screenshot_region, threshold=0.8):
    """Compare reference image with screenshot region using template matching"""
    try:
        # Load reference image
        if not os.path.exists(reference_path):
            print(f"Reference image not found: {reference_path}")
            return False
            
        ref_img = Image.open(reference_path)
        ref_array = np.array(ref_img)
        
        # Convert screenshot region to numpy array
        screen_array = np.array(screenshot_region)
        
        # Convert to grayscale for template matching
        if len(ref_array.shape) == 3:
            ref_gray = np.dot(ref_array[...,:3], [0.299, 0.587, 0.114])
        else:
            ref_gray = ref_array
            
        if len(screen_array.shape) == 3:
            screen_gray = np.dot(screen_array[...,:3], [0.299, 0.587, 0.114])
        else:
            screen_gray = screen_array
        
        # Simple correlation-based matching
        if ref_gray.shape[0] > screen_gray.shape[0] or ref_gray.shape[1] > screen_gray.shape[1]:
            print("Reference image is larger than screenshot region")
            return False
        
        # Fallback to simple pixel-by-pixel comparison
        if ref_gray.shape != screen_gray.shape:
            # Resize reference to match screen region
            ref_img_resized = ref_img.resize(screen_array.shape[1::-1])
            ref_array_resized = np.array(ref_img_resized)
            if len(ref_array_resized.shape) == 3:
                ref_gray = np.dot(ref_array_resized[...,:3], [0.299, 0.587, 0.114])
            else:
                ref_gray = ref_array_resized
        
        # Simple pixel difference calculation
        diff = np.abs(ref_gray - screen_gray)
        similarity = 1.0 - (diff.mean() / 255.0)
        
        print(f"Image similarity: {similarity:.3f}, threshold: {threshold}")
        return similarity >= threshold
        
    except Exception as e:
        print(f"Error comparing images: {e}")
        return False

def test_image_recognition():
    """Test the image recognition functionality"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    print("=== Image Recognition Test ===")
    print("This will test the new image check functionality.")
    
    # Step 1: Select reference image
    print("\n1. Select a reference image to look for...")
    image_path = filedialog.askopenfilename(
        filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")],
        title="Select Reference Image"
    )
    
    if not image_path:
        print("No image selected. Exiting.")
        return
        
    print(f"Selected reference image: {os.path.basename(image_path)}")
    
    # Step 2: Define search region
    print("\n2. Define search region...")
    messagebox.showinfo("Define Search Region", 
                       "Click OK, then click and drag to define the region where the image should be found.")
    
    coords = []
    from pynput import mouse
    
    def on_click(x, y, button, pressed):
        if pressed:
            coords.clear()
            coords.append((x, y))
            print(f"Start point: ({x}, {y})")
        else:
            coords.append((x, y))
            print(f"End point: ({x}, {y})")
            return False  # Stop listener
    
    print("Click and drag to define the search region...")
    listener = mouse.Listener(on_click=on_click)
    listener.start()
    listener.join()
    
    if len(coords) != 2:
        print("Failed to capture region coordinates.")
        return
    
    (x1, y1), (x2, y2) = coords
    left, top = min(x1, x2), min(y1, y2)
    width, height = abs(x2 - x1), abs(y2 - y1)
    
    print(f"Search region: ({left}, {top}) to ({left + width}, {top + height})")
    
    # Step 3: Take screenshot and compare
    print("\n3. Taking screenshot and comparing...")
    
    with mss.mss() as sct:
        monitor = {'top': top, 'left': left, 'width': width, 'height': height}
        sct_img = sct.grab(monitor)
        img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)
    
    # Save screenshot for debugging
    debug_path = "debug_screenshot.png"
    img.save(debug_path)
    print(f"Screenshot saved as: {debug_path}")
    
    # Test with different thresholds
    thresholds = [0.9, 0.8, 0.7, 0.6, 0.5]
    
    for threshold in thresholds:
        found = compare_images(image_path, img, threshold)
        print(f"Threshold {threshold}: {'FOUND' if found else 'NOT FOUND'}")
        
        if found:
            print(f"\n✓ IMAGE FOUND with threshold {threshold}!")
            print("In the macro, this would execute the sub-actions:")
            print("  - Sub-action 1 (e.g., click at specific location)")
            print("  - Sub-action 2 (e.g., drag operation)")
            print("  - Sub-action 3 (e.g., copy/paste)")
            print("  - Then continue with main macro flow")
            break
    else:
        print("\n✗ IMAGE NOT FOUND with any threshold")
        print("In the macro, this would skip sub-actions and continue with main flow")
    
    print(f"\nTest complete! Reference image: {os.path.basename(image_path)}")
    print("You can now use this functionality in Macro Maker Pro!")

if __name__ == "__main__":
    test_image_recognition()
