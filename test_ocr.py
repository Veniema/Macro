import mss
from PIL import Image
import pytesseract
import re
import tkinter as tk
from tkinter import messagebox
import pyperclip

def test_ocr_region():
    """Test OCR on a manually defined screen region"""
    # You'll need to adjust these coordinates to match your target area
    # Example: top-left (100, 100) to bottom-right (400, 200)
    x1, y1, x2, y2 = 100, 100, 400, 200
    
    left, top = min(x1, x2), min(y1, y2)
    width, height = abs(x2 - x1), abs(y2 - y1)
    
    print(f"Capturing region: left={left}, top={top}, width={width}, height={height}")
    
    try:
        with mss.mss() as sct:
            monitor = {'top': top, 'left': left, 'width': width, 'height': height}
            sct_img = sct.grab(monitor)
            img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)
        
        # Save for debugging
        img.save("test_ocr_capture.png")
        print("Screenshot saved as 'test_ocr_capture.png'")
        
        # Try different OCR configurations
        configs = [
            '--psm 6',  # Uniform block of text
            '--psm 7',  # Single text line
            '--psm 8',  # Single word
            '--psm 13', # Raw line. Treat the image as a single text line
        ]
        
        for config in configs:
            print(f"\nTrying OCR config: {config}")
            text = pytesseract.image_to_string(img, config=config)
            print(f"Raw OCR text: '{text}'")
            
            # Look for 9-digit numbers
            matches = re.findall(r'\b(\d{9})\b', text)
            if matches:
                print(f"Found 9-digit numbers: {matches}")
                # Copy first match to clipboard
                pyperclip.copy(matches[0])
                print(f"Copied to clipboard: {matches[0]}")
                return matches[0]
            else:
                print("No 9-digit numbers found")
        
        print("\nNo 9-digit numbers found with any configuration")
        return None
        
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    print("OCR Test - Make sure you have a 9-digit number visible on screen")
    print("Adjust the coordinates in the script (x1, y1, x2, y2) to match your target area")
    input("Press Enter to start OCR test...")
    
    result = test_ocr_region()
    if result:
        print(f"SUCCESS: Found and copied 9-digit code: {result}")
    else:
        print("FAILED: No 9-digit code found")
