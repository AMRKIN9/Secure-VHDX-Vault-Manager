import os
import math
from PIL import Image, ImageDraw, ImageFilter

def create_mac_silver_hdd_icon(output_ico_path="icon.ico", output_png_path="icon.png", size=512):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # Dimensions
    pad = 36
    x0, y0 = pad, pad + 12
    x1, y1 = size - pad, size - pad + 6
    radius = 38

    # 1. Soft Ambient Drop Shadow
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle([x0 + 4, y0 + 16, x1 - 4, y1 + 18], radius=radius, fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    img.alpha_composite(shadow)

    # 2. Outer Aluminum Chassis (Vertical Metallic Gradient)
    chassis = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(chassis)
    
    chassis_mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(chassis_mask).rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=255)

    for y in range(y0, y1):
        ratio = (y - y0) / (y1 - y0)
        # Silver brushed gradient from #E6EAEF to #969BA1
        r = int(230 - ratio * 78)
        g = int(234 - ratio * 78)
        b = int(238 - ratio * 76)
        cdraw.line([(x0, y), (x1, y)], fill=(r, g, b, 255))
        
    chassis.putalpha(chassis_mask)
    img.alpha_composite(chassis)

    draw = ImageDraw.Draw(img)

    # 3. Outer Chamfer & Bevel Stroke
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, outline=(255, 255, 255, 200), width=2)
    draw.rounded_rectangle([x0 + 1, y0 + 1, x1 - 1, y1 - 1], radius=radius, outline=(60, 64, 70, 90), width=1)

    # 4. Front Bezel / Lower Section Divider
    divider_y = y1 - 66
    draw.line([(x0 + 6, divider_y), (x1 - 6, divider_y)], fill=(65, 69, 75, 220), width=2)
    draw.line([(x0 + 6, divider_y + 2), (x1 - 6, divider_y + 2)], fill=(255, 255, 255, 160), width=1)

    # 5. Front Details: Activity LED & Micro-perforations
    led_x, led_y = x0 + 42, divider_y + 32
    led_glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(led_glow)
    gdraw.ellipse([led_x - 9, led_y - 9, led_x + 9, led_y + 9], fill=(215, 25, 33, 160))
    led_glow = led_glow.filter(ImageFilter.GaussianBlur(6))
    img.alpha_composite(led_glow)

    draw = ImageDraw.Draw(img)
    draw.ellipse([led_x - 4, led_y - 4, led_x + 4, led_y + 4], fill=(255, 50, 50, 255))
    draw.ellipse([led_x - 2, led_y - 2, led_x + 1, led_y + 1], fill=(255, 220, 220, 240))

    # Front Air Vents / Grid dots
    for vx in range(x0 + 80, x1 - 40, 14):
        draw.ellipse([vx, divider_y + 30, vx + 4, divider_y + 34], fill=(55, 59, 65, 220))
        draw.ellipse([vx, divider_y + 31, vx + 4, divider_y + 35], fill=(255, 255, 255, 100))

    # 6. Recessed Drive Bay Plate (Upper Body)
    bay_x0, bay_y0 = x0 + 24, y0 + 22
    bay_x1, bay_y1 = x1 - 24, divider_y - 20
    bay_r = 16

    # Bay plate image with mask so platter lines NEVER spill outside
    bay_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(bay_img)
    bay_mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(bay_mask).rounded_rectangle([bay_x0, bay_y0, bay_x1, bay_y1], radius=bay_r, fill=255)

    # Darker recessed plate gradient
    for by in range(bay_y0, bay_y1):
        ratio = (by - bay_y0) / (bay_y1 - bay_y0)
        gr = int(140 - ratio * 35)
        gg = int(144 - ratio * 35)
        gb = int(150 - ratio * 33)
        bdraw.line([(bay_x0, by), (bay_x1, by)], fill=(gr, gg, gb, 255))

    # 7. Concentric Platter Rings (Confined cleanly to bay plate)
    cx = (bay_x0 + bay_x1) // 2
    cy = (bay_y0 + bay_y1) // 2
    max_platter_r = min(cx - bay_x0, cy - bay_y0) - 22

    for r_offset in range(max_platter_r, 48, -14):
        alpha_val = int(35 + (r_offset / max_platter_r) * 60)
        bdraw.ellipse([cx - r_offset, cy - r_offset, cx + r_offset, cy + r_offset],
                      outline=(230, 235, 240, alpha_val), width=1)

    bay_img.putalpha(bay_mask)
    img.alpha_composite(bay_img)

    draw = ImageDraw.Draw(img)

    # Bay plate bevel & border
    draw.rounded_rectangle([bay_x0, bay_y0, bay_x1, bay_y1], radius=bay_r, outline=(65, 69, 75, 220), width=2)
    draw.rounded_rectangle([bay_x0 + 1, bay_y0 + 1, bay_x1 - 1, bay_y1 - 1], radius=bay_r, outline=(255, 255, 255, 80), width=1)

    # 8. Center Spindle (Dark brushed gunmetal)
    spindle_r = 46
    draw.ellipse([cx - spindle_r, cy - spindle_r, cx + spindle_r, cy + spindle_r],
                 fill=(70, 74, 80, 255), outline=(45, 49, 55, 255), width=2)
    draw.ellipse([cx - spindle_r + 2, cy - spindle_r + 2, cx + spindle_r - 2, cy + spindle_r - 2],
                 outline=(200, 205, 212, 140), width=1)

    # 9. Integrated Precision Lock Cylinder (Clean, mechanical, zero cringe)
    lock_r = 24
    draw.ellipse([cx - lock_r, cy - lock_r, cx + lock_r, cy + lock_r],
                 fill=(35, 38, 42, 255), outline=(170, 175, 180, 220), width=2)
    # Key slot
    draw.rounded_rectangle([cx - 4, cy - 14, cx + 4, cy + 14], radius=2, fill=(15, 16, 18, 255))
    draw.ellipse([cx - 7, cy - 4, cx + 7, cy + 4], fill=(15, 16, 18, 255))
    draw.line([(cx - 3, cy - 13), (cx - 3, cy + 13)], fill=(110, 115, 120, 180), width=1)

    # 10. Precision Torx Screws in 4 corners of the drive bay
    screw_coords = [
        (bay_x0 + 15, bay_y0 + 15),
        (bay_x1 - 15, bay_y0 + 15),
        (bay_x0 + 15, bay_y1 - 15),
        (bay_x1 - 15, bay_y1 - 15)
    ]
    for sx, sy in screw_coords:
        sr = 7
        draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(165, 170, 176, 255), outline=(85, 89, 95, 255), width=1)
        draw.line([(sx - 3, sy), (sx + 3, sy)], fill=(45, 49, 55, 255), width=1)
        draw.line([(sx, sy - 3), (sx, sy + 3)], fill=(45, 49, 55, 255), width=1)
        draw.line([(sx - 2, sy - 2), (sx + 2, sy + 2)], fill=(45, 49, 55, 255), width=1)

    # 11. Subtle Laser Engraving: "VHDX // SECURE" and "XTS-AES 256"
    draw.text((bay_x0 + 18, bay_y1 - 30), "VHDX // SECURE", fill=(70, 74, 80, 220))
    draw.text((bay_x1 - 96, bay_y1 - 30), "XTS-AES 256", fill=(70, 74, 80, 220))

    # Save PNG
    img.save(output_png_path, "PNG")

    # Generate multi-resolution Windows .ico
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img.save(output_ico_path, format="ICO", sizes=icon_sizes)
    print(f"[+] Refined Icon generated: {output_ico_path} and {output_png_path}")

if __name__ == "__main__":
    create_mac_silver_hdd_icon()
