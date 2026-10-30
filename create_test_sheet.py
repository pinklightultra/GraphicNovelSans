"""Create a synthetic filled lettering sheet for E2E testing."""
from PIL import Image, ImageDraw
import numpy as np

width, height = 2480, 3508
img = Image.new("RGB", (width, height), (255, 255, 255))
draw = ImageDraw.Draw(img)

margin_x, margin_top = 120, 280
cell_w = (width - 2 * margin_x) // 13
cell_h = (height - margin_top - 140) // 6

chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!?,."

for idx, char in enumerate(chars[:10]):
    r = idx // 13
    c = idx % 13
    x0 = margin_x + c * cell_w
    y0 = margin_top + r * cell_h
    x1 = x0 + cell_w
    y1 = y0 + cell_h
    
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    
    if char.isalpha():
        draw.ellipse([cx-30, cy-40, cx+30, cy+40], fill=(0, 0, 0))
        draw.rectangle([cx-5, cy-40, cx+5, cy+40], fill=(0, 0, 0))
    elif char.isdigit():
        draw.ellipse([cx-25, cy-35, cx+25, cy+35], fill=(0, 0, 0))
    else:
        draw.rectangle([cx-20, cy-5, cx+20, cy+5], fill=(0, 0, 0))

img.save("test_filled_sheet.png")
print("Created test_filled_sheet.png")
