"""Run once to generate assets/icon.png"""
from PIL import Image, ImageDraw
import os

img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.ellipse([4, 4, 60, 60], fill=(52, 120, 246))
# Speaker symbol: triangle body
draw.polygon([(18, 24), (18, 40), (28, 40), (38, 50), (38, 14), (28, 24)], fill="white")
# Sound waves
draw.arc([38, 20, 52, 44], start=-60, end=60, fill="white", width=3)
draw.arc([42, 16, 58, 48], start=-60, end=60, fill="white", width=3)
os.makedirs("assets", exist_ok=True)
img.save("assets/icon.png")
print("Icon saved to assets/icon.png")
