# Macro Maker Pro v2.1 - Complete Edition

## 🚀 What's New in This Version

This is a **clean, complete version** that includes all the latest improvements:

### ✨ **Key Features:**
- 🔍 **Image Recognition with Branching** - Conditional macro execution based on visual detection
- 👁️ **Enhanced OCR** - 4 extraction modes (all text, numbers, emails, custom regex)
- ⚡ **Quick Action Sequences** - One-click common patterns (Click+Copy, Drag+Copy, etc.)
- ⌨️ **Enhanced Shortcuts** - More keyboard shortcuts for power users
- 🎯 **Better User Experience** - Improved dialogs, status feedback, and error handling

### 🔄 **Backward Compatibility:**
- ✅ All existing macro files will work unchanged
- ✅ Legacy OCR actions are automatically converted
- ✅ No breaking changes from previous versions

## 🛠️ Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements_complete.txt
```

### 2. Install Tesseract OCR
**Windows:** Download from [Tesseract GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

**macOS:** 
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

### 3. Run the Application
```bash
python Macro_Maker_Pro_Complete.py
```

## 📋 Quick Start Guide

### **Basic Macro Creation:**
1. Click recording buttons to add actions: 🖱️ Click, ↗️ Drag, 📋 Copy, etc.
2. Use **Quick Actions** for common sequences (Click+Copy, Drag+Copy)
3. Set loop count and auto-delay options
4. Press **▶️ Start (F5)** to run your macro

### **Image Recognition:**
1. Click **🔍 Img Check** button
2. Select a reference image file (PNG, JPG, etc.)
3. Define the search region on screen
4. Set similarity threshold (0.8 = 80% match)
5. Add sub-actions to execute when image is found

### **Enhanced OCR:**
1. Click **👁️ OCR** button
2. Define the text region on screen
3. Choose extraction mode:
   - **All Text** - Copy everything
   - **Numbers Only** - Extract just digits
   - **Email Addresses** - Find emails
   - **Custom Pattern** - Use regex (e.g., `\d{4,8}` for 4-8 digit codes)
4. Select processing option (copy, show, first match, all matches)

## ⌨️ Keyboard Shortcuts

### **File Operations:**
- `Ctrl+N` - New macro
- `Ctrl+O` - Open macro
- `Ctrl+S` - Save macro

### **Macro Control:**
- `F5` or `Ctrl+R` - Run macro
- `Esc` - Stop macro

### **Action Management:**
- `Delete` - Delete selected action
- `Ctrl+D` - Duplicate selected action
- `Ctrl+E` - Edit selected action

### **Quick Actions:**
- `Ctrl+T` - Quick Click+Copy
- `Ctrl+Y` - Quick Click+Paste

## 🎯 Advanced Features

### **Image Recognition Branching:**
Create smart macros that respond to UI changes:
```
1. Normal macro steps...
2. Image Check → IF button found:
   2a. Click button
   2b. Fill form  
   2c. Submit
3. Continue normal flow...
```

### **OCR Pattern Examples:**
- **Phone Numbers:** `\d{3}-\d{3}-\d{4}`
- **Product Codes:** `[A-Z]{2,3}-\d{4,6}` 
- **Invoice Numbers:** `INV-\d+`
- **URLs:** `https?://[^\s]+`
- **Any 4-8 Digits:** `\d{4,8}`

### **Quick Action Patterns:**
- **Click + Copy** - Click field, auto-copy content
- **Click + Paste** - Click field, auto-paste content
- **Drag + Copy** - Select text, auto-copy
- **Triple Click** - Select entire line
- **Ctrl+A + Copy** - Select all, copy

## 🔧 Troubleshooting

### **Common Issues:**

**"Image not found" when it should be:**
- Lower similarity threshold (try 0.7 instead of 0.8)
- Check if UI scaling affects appearance
- Ensure search region fully contains target

**OCR not working:**
- Verify Tesseract is installed and in PATH
- Try different PSM modes (app tries multiple automatically)
- Ensure text region has good contrast

**Macro execution stops:**
- Check for error messages in console
- Verify all reference images exist
- Test individual actions first

### **Performance Tips:**
- Use smaller search regions for faster image checks
- Install scipy for better image matching performance
- Limit number of image checks per macro

## 📁 File Structure

- `Macro_Maker_Pro_Complete.py` - Main application (use this!)
- `requirements_complete.txt` - All dependencies
- `README_COMPLETE.md` - This documentation

## 🆕 What's Different from Previous Versions

### **Enhanced OCR:**
- **Before:** Only found 6-9 digit numbers, padded with zeros
- **After:** 4 extraction modes + custom regex + multiple processing options

### **Image Recognition:**
- **Before:** Not available
- **After:** Full image detection with conditional sub-actions

### **Quick Actions:**
- **Before:** Manual assembly of action sequences
- **After:** One-click common patterns

### **User Experience:**
- **Before:** Basic interface
- **After:** Better dialogs, status feedback, keyboard shortcuts

## 🎉 Migration from Old Versions

1. **Replace** your old macro file with `Macro_Maker_Pro_Complete.py`
2. **Update** requirements: `pip install -r requirements_complete.txt`
3. **Your existing macros will work unchanged** - no conversion needed!
4. **Start using new features** as desired

## 💡 Pro Tips

1. **Start with Quick Actions** for common patterns
2. **Use Image Recognition sparingly** - it adds execution time
3. **Test OCR patterns** before building large macros
4. **Save reference images** in the same folder as your macros
5. **Use keyboard shortcuts** for faster workflow

---

**Ready to automate with intelligence!** 🚀

For questions or issues, the app provides console output for debugging and status bar feedback during execution.
