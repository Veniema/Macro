# Image Recognition and Branching in Macro Maker Pro

## Overview

Macro Maker Pro now supports **image recognition with conditional branching**! This powerful feature allows your macros to:

1. Look for specific images at certain points during execution
2. Execute different sub-actions when an image is found vs. not found
3. Create intelligent, adaptive macros that respond to changing UI states

## How It Works

The new "🔍 Img Check" action type works like this:

```
1. Take a screenshot of a defined region
2. Compare it with a reference image you provide
3. If image similarity >= threshold:
   → Execute sub-actions (branch A)
4. If image not found:
   → Skip sub-actions and continue main flow (branch B)
```

## Example Usage Scenario

Your original example translates perfectly to this system:

```
Main Macro Flow:
1. 🖱️ Click (action 1)
2. ↗️ Drag (action 2) 
3. 📋 Copy (action 3)
4. 🖱️ Click (action 4)
5. 📄 Paste (action 5)
6. 🖱️ Click (action 6)
7. 🔍 Img Check (conditional branching point)
   └─ IF IMAGE FOUND:
      7a. 🖱️ Click (sub-action)
      7b. ↗️ Drag (sub-action)
      7c. 📋 Copy (sub-action)
      7d. 🖱️ Click (sub-action)
      7e. 📄 Paste (sub-action)
   └─ IF IMAGE NOT FOUND:
      → Continue directly to step 8
8. 🖱️ Click (final action - executed regardless)
```

## Setting Up Image Recognition

### 1. Recording an Image Check Action

1. Click the **"🔍 Img Check"** button in the macro recorder
2. Select your reference image file (PNG, JPG, etc.)
3. Click and drag to define the search region on screen
4. Set similarity threshold (0.0-1.0, higher = more strict)
5. Define sub-actions using the pop-up dialog

### 2. Reference Image Tips

**Good reference images:**
- Clear, distinctive visual elements
- Consistent across UI states
- Not too small (at least 20x20 pixels)
- High contrast elements work best

**Examples:**
- Button icons or text
- Status indicators
- Specific UI elements that appear/disappear
- Error dialogs or success messages

### 3. Threshold Settings

- **0.9-1.0**: Very strict matching (exact pixel match)
- **0.8-0.9**: Good for consistent UI elements  
- **0.7-0.8**: More forgiving, handles slight variations
- **0.5-0.7**: Very lenient, may have false positives

## Advanced Features

### Sub-Action Types Supported
- **Click**: Mouse clicks at specific coordinates
- **Drag**: Mouse drag operations  
- **Delay**: Wait periods between actions
- **Copy**: Ctrl+C clipboard operations
- **Paste**: Ctrl+V clipboard operations

### Search Region Strategy
- **Small regions**: Faster processing, more precise
- **Large regions**: More forgiving positioning, slower
- **Multiple checks**: Use several img_check actions for complex logic

## Technical Details

### Image Comparison Algorithm
1. Converts both images to grayscale
2. Uses normalized cross-correlation when scipy is available
3. Falls back to pixel-by-pixel similarity comparison
4. Handles different image sizes through resizing

### Dependencies Added
- `numpy>=1.21.0` - Required for image processing arrays
- `scipy>=1.7.0` - Optional, provides better image matching

### Debug Information
- Similarity scores are printed to console during execution  
- Screenshots can be saved for debugging purposes
- Status bar shows real-time feedback during macro execution

## Testing the Feature

Use the included `test_image_check.py` script to:
1. Test image recognition with your reference images
2. Experiment with different similarity thresholds
3. Validate search regions before recording macros

## Best Practices

### 1. Macro Design
- Use image checks sparingly - they add execution time
- Place them at logical decision points in your workflow
- Keep sub-action lists focused and minimal

### 2. Reference Images
- Capture reference images in the same environment where macros will run
- Update reference images if UI changes
- Test with multiple similarity thresholds to find optimal settings

### 3. Error Handling  
- The macro continues even if image comparison fails
- Failed image loads are logged but don't stop execution
- Missing reference files are handled gracefully

## File Format Support

**Reference Images:**
- PNG (recommended for UI elements)
- JPG/JPEG (good for photographs) 
- BMP (uncompressed, larger files)
- GIF (basic support)

## Troubleshooting

### Common Issues

**"Image not found" when it should be:**
- Lower the similarity threshold
- Check if UI scaling affects image appearance
- Ensure search region fully contains the target image

**False positive matches:**
- Increase the similarity threshold
- Use a more distinctive reference image
- Reduce the search region size

**Slow execution:**
- Use smaller search regions
- Install scipy for faster image comparison
- Limit the number of image checks per macro

### Debug Tips

1. Run `test_image_check.py` to validate your setup
2. Check console output for similarity scores
3. Save debug screenshots to verify search regions
4. Use the status bar for real-time execution feedback

## Migration from v2.0

Existing macros continue to work unchanged. The new image recognition feature is purely additive and doesn't affect existing action types.

To add image recognition to existing macros:
1. Open your saved macro file
2. Insert new "🔍 Img Check" actions where needed
3. Save the updated macro

## Performance Notes

- Image checks add 100-500ms per check (depending on region size)
- scipy installation can improve matching speed by 2-3x
- Multiple image checks in sequence will slow execution
- Consider caching reference images for frequently-run macros

---

**Happy automating with intelligent image recognition!** 🚀
