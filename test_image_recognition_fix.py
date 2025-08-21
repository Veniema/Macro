#!/usr/bin/env python3
"""
Test script to verify the image recognition threading fixes
"""
import tkinter as tk
from tkinter import messagebox
import sys
import os

def test_image_recognition():
    """Test the fixed image recognition functionality"""
    try:
        # Import the fixed macro code
        import importlib.util
        spec = importlib.util.spec_from_file_location("macro", "Macro Code")
        macro_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(macro_module)
        
        print("Successfully imported macro module with fixes")
        
        # Create a test window
        root = tk.Tk()
        root.title("Testing Image Recognition Fix")
        root.geometry("400x200")
        
        # Create macro maker instance
        macro_maker = macro_module.MacroMaker(root)
        
        print("Successfully created MacroMaker instance")
        
        # Add instructions
        instructions = """Image Recognition Fix Test

The following mouse listener threading issues have been fixed:
1. Image check recording dialog
2. Sub-actions dialog for image checks  
3. Quick action sequences (Click+Copy, Click+Paste, etc.)
4. Basic click and drag recording
5. OCR region recording

Try using the 'Img Check' button - it should no longer crash
with the TclError about window visibility."""
        
        label = tk.Label(root, text=instructions, justify='left', wraplength=380)
        label.pack(padx=10, pady=10)
        
        print("Test setup complete. You can now test the image recognition features.")
        print("The mouse listener threading issues should be resolved.")
        
        return root, macro_maker
        
    except Exception as e:
        print(f"Error during testing: {e}")
        return None, None

if __name__ == "__main__":
    root, macro_maker = test_image_recognition()
    if root:
        print("Starting GUI test...")
        root.mainloop()
