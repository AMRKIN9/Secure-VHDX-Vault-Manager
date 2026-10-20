"""
Nothing OS Industrial Design System Tokens & Constants
Monochrome, Typographic, Industrial Minimalism with Nothing Red Accent
"""

# Color Palette (OLED Black, Stark White, Technical Grays, Signature Red)
COLOR_BG_ROOT = "#000000"         # True OLED Black
COLOR_SURFACE_1 = "#0A0A0A"       # Deep background layer
COLOR_SURFACE_2 = "#121212"       # Card / Container background
COLOR_SURFACE_3 = "#1A1A1A"       # Interactive element / Button background
COLOR_SURFACE_HOVER = "#242424"   # Hover background
COLOR_BORDER = "#222222"          # Crisp 1px mechanical border
COLOR_BORDER_FOCUS = "#444444"    # Active/focused border

# High Contrast Typography
COLOR_TEXT_PRIMARY = "#FFFFFF"     # 100% Stark White
COLOR_TEXT_SECONDARY = "#888888"   # Muted Technical Metadata
COLOR_TEXT_DIM = "#555555"         # Disabled / Inactive text

# Intentional Accents
COLOR_ACCENT_RED = "#D71921"       # Nothing Signature Red (Panic / Emergency / Locked)
COLOR_ACCENT_RED_HOVER = "#B3141A" # Red Hover
COLOR_ACCENT_GREEN = "#00E575"     # Active Mount / Verified Checksum
COLOR_ACCENT_YELLOW = "#FFCC00"    # Warning / Action Required

# Typography Fonts (Cascadia Code / Consolas for technical data)
FONT_FAMILY_MONO = "Consolas"
FONT_FAMILY_SANS = "Segoe UI"

FONT_TITLE = (FONT_FAMILY_MONO, 14, "bold")
FONT_HEADING = (FONT_FAMILY_MONO, 12, "bold")
FONT_BODY = (FONT_FAMILY_MONO, 10, "normal")
FONT_BODY_BOLD = (FONT_FAMILY_MONO, 10, "bold")
FONT_CAPTION = (FONT_FAMILY_MONO, 8, "normal")
FONT_STATUS = (FONT_FAMILY_MONO, 9, "bold")

# Geometry (Clean industrial corner radii)
CORNER_RADIUS_CARD = 4
CORNER_RADIUS_BTN = 3
CORNER_RADIUS_PILL = 2
BORDER_WIDTH = 1
