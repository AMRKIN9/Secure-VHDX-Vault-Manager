"""
Nothing OS Industrial Design System Tokens & Constants
Monochrome, Typographic, Industrial Minimalism with Nothing Red Accent
"""

# Color Palette (OLED Black, Stark White, Technical Grays, Signature Red)
COLOR_BG_ROOT = "#000000"         # True OLED Black
COLOR_SURFACE_1 = "#0D0D0D"       # Deep background layer
COLOR_SURFACE_2 = "#141414"       # Card / Container background
COLOR_SURFACE_3 = "#1E1E1E"       # Interactive element / Button background
COLOR_SURFACE_HOVER = "#2A2A2A"   # Hover background
COLOR_BORDER = "#2A2A2A"          # Crisp 1px mechanical border
COLOR_BORDER_FOCUS = "#555555"    # Active/focused border

# High Contrast Typography
COLOR_TEXT_PRIMARY = "#FFFFFF"     # 100% Stark White
COLOR_TEXT_SECONDARY = "#999999"   # Muted Technical Metadata
COLOR_TEXT_DIM = "#666666"         # Disabled / Inactive text

# Intentional Accents
COLOR_ACCENT_RED = "#D71921"       # Nothing Signature Red (Panic / Emergency / Locked)
COLOR_ACCENT_RED_HOVER = "#B3141A" # Red Hover
COLOR_ACCENT_GREEN = "#00E575"     # Active Mount / Verified Checksum
COLOR_ACCENT_YELLOW = "#FFCC00"    # Warning / Action Required

# Solid, Bold, Highly Legible Typography
FONT_FAMILY_MONO = "Consolas"
FONT_FAMILY_SANS = "Segoe UI"

FONT_TITLE = (FONT_FAMILY_SANS, 16, "bold")
FONT_HEADING = (FONT_FAMILY_SANS, 14, "bold")
FONT_BODY = (FONT_FAMILY_SANS, 12, "bold")
FONT_BODY_NORMAL = (FONT_FAMILY_SANS, 12, "normal")
FONT_BUTTON = (FONT_FAMILY_SANS, 11, "bold")
FONT_STATUS = (FONT_FAMILY_MONO, 12, "bold")
FONT_CAPTION = (FONT_FAMILY_SANS, 11, "bold")
FONT_METADATA = (FONT_FAMILY_MONO, 11, "bold")

# Geometry (Clean industrial corner radii)
CORNER_RADIUS_CARD = 6
CORNER_RADIUS_BTN = 4
CORNER_RADIUS_PILL = 3
BORDER_WIDTH = 1
