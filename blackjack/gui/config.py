"""GUI constants: colors, sizes, layout."""

# ── Window ────────────────────────────────────────────────────────────────────
WIN_W, WIN_H = 1280, 800
FPS = 60
TITLE = "BLACKJACK 21 — Pygame Edition"

# ── Colors ────────────────────────────────────────────────────────────────────
FELT         = (30, 100, 50)
FELT_DARK    = (20, 75, 35)
WHITE        = (255, 255, 255)
BLACK        = (0, 0, 0)
RED_SUIT     = (200, 30, 30)
GOLD         = (255, 215, 0)
GOLD_DARK    = (180, 150, 0)
GRAY         = (120, 120, 120)
GRAY_LIGHT   = (180, 180, 180)
GRAY_DARK    = (60, 60, 60)
BLUE         = (50, 100, 200)
BLUE_DARK    = (30, 60, 140)
BLUE_LIGHT   = (100, 150, 240)
GREEN_BTN    = (40, 160, 80)
GREEN_HOVER  = (60, 200, 100)
RED_BTN      = (180, 50, 50)
RED_HOVER    = (220, 70, 70)
YELLOW_BTN   = (200, 180, 40)
YELLOW_HOVER = (240, 220, 60)
CYAN_BTN     = (40, 180, 200)
CYAN_HOVER   = (60, 220, 240)
PURPLE       = (140, 60, 200)
PURPLE_LIGHT = (180, 100, 240)
OVERLAY      = (0, 0, 0, 160)

# ── Card sizes ────────────────────────────────────────────────────────────────
CARD_W, CARD_H = 80, 120
CARD_GAP = 25
CARD_RADIUS = 8
CARD_BACK_COLOR = (40, 70, 160)

# ── Layout Y positions ───────────────────────────────────────────────────────
TOP_BAR_H = 50
DEALER_Y = 90
PLAYER_Y = 310
BUTTONS_Y = 480
CHIPS_Y = 560
HUD_Y = 650

# ── Chip denominations ───────────────────────────────────────────────────────
CHIP_DENOMS = [10, 25, 50, 100, 250]
CHIP_COLORS = {
    10:  (255, 255, 255),
    25:  (220, 50, 50),
    50:  (50, 100, 220),
    100: (30, 30, 30),
    250: (140, 50, 200),
}
CHIP_RADIUS = 28

# ── Animation ─────────────────────────────────────────────────────────────────
DEAL_SPEED = 0.3        # seconds per card
SHOE_POS = (1200, 30)   # where cards come from
