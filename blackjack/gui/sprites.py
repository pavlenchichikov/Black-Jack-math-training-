"""Drawing utilities: cards, buttons, chips, HUD elements."""

from __future__ import annotations

import pygame
from ..models import Card, Rank, Suit
from . import config as C


def _sys_font(names: str, size: int, bold: bool = False) -> pygame.font.Font:
    """Try system font with fallback chain, then Pygame default."""
    font = pygame.font.SysFont(names, size, bold=bold)
    # SysFont returns the default font when nothing matches — that's fine
    return font


_MONO = "consolas,inconsolata,dejavusansmono,liberationmono,couriernew,monospace"
_SANS = "segoeui,arial,helvetica,dejavusans,liberationsans,freesans,sans"


def init_fonts() -> dict[str, pygame.font.Font]:
    """Call after pygame.init(). Works on Windows, macOS, and Linux."""
    return {
        "card":    _sys_font(_MONO, 18, bold=True),
        "card_lg": _sys_font(_MONO, 28, bold=True),
        "btn":     _sys_font(_SANS, 20, bold=True),
        "info":    _sys_font(_SANS, 18),
        "info_sm": _sys_font(_SANS, 15),
        "title":   _sys_font(_SANS, 44, bold=True),
        "sub":     _sys_font(_SANS, 24),
        "chip":    _sys_font(_MONO, 14, bold=True),
        "hud":     _sys_font(_MONO, 16),
        "popup":   _sys_font(_SANS, 20),
        "popup_q": _sys_font(_SANS, 18),
        "input":   _sys_font(_MONO, 22),
    }


# ── Card drawing ──────────────────────────────────────────────────────────────

SUIT_SYMBOLS = {
    Suit.HEARTS: "\u2665", Suit.DIAMONDS: "\u2666",
    Suit.CLUBS: "\u2663", Suit.SPADES: "\u2660",
}


def draw_card(surf: pygame.Surface, card: Card, x: int, y: int,
              fonts: dict, hidden: bool = False) -> pygame.Rect:
    """Draw a single card. Returns its rect."""
    rect = pygame.Rect(x, y, C.CARD_W, C.CARD_H)

    if hidden:
        pygame.draw.rect(surf, C.CARD_BACK_COLOR, rect, border_radius=C.CARD_RADIUS)
        pygame.draw.rect(surf, C.BLUE_LIGHT, rect, 2, border_radius=C.CARD_RADIUS)
        # Pattern
        inner = rect.inflate(-12, -12)
        pygame.draw.rect(surf, C.BLUE_DARK, inner, border_radius=4)
        q = fonts["card_lg"].render("?", True, C.WHITE)
        surf.blit(q, q.get_rect(center=rect.center))
        return rect

    # Face-up card
    pygame.draw.rect(surf, C.WHITE, rect, border_radius=C.CARD_RADIUS)
    pygame.draw.rect(surf, C.GRAY, rect, 2, border_radius=C.CARD_RADIUS)

    color = C.RED_SUIT if card.suit.is_red else C.BLACK
    label = card.rank.label
    sym = SUIT_SYMBOLS[card.suit]

    # Top-left rank
    r_surf = fonts["card"].render(label, True, color)
    surf.blit(r_surf, (x + 6, y + 4))

    # Top-left suit (small)
    s_small = fonts["card"].render(sym, True, color)
    surf.blit(s_small, (x + 6, y + 22))

    # Center suit (large)
    s_big = fonts["card_lg"].render(sym, True, color)
    surf.blit(s_big, s_big.get_rect(center=rect.center))

    # Bottom-right rank (inverted)
    r2 = pygame.transform.rotate(r_surf, 180)
    surf.blit(r2, (x + C.CARD_W - 6 - r2.get_width(), y + C.CARD_H - 4 - r2.get_height()))

    return rect


def draw_hand(surf: pygame.Surface, cards: list[Card], cx: int, y: int,
              fonts: dict, hide_first: bool = False) -> list[pygame.Rect]:
    """Draw a hand centered at cx. Returns list of card rects."""
    n = len(cards)
    total_w = n * C.CARD_W + (n - 1) * C.CARD_GAP
    start_x = cx - total_w // 2
    rects = []
    for i, card in enumerate(cards):
        rx = start_x + i * (C.CARD_W + C.CARD_GAP)
        r = draw_card(surf, card, rx, y, fonts, hidden=(i == 0 and hide_first))
        rects.append(r)
    return rects


# ── Buttons ───────────────────────────────────────────────────────────────────

class Button:
    def __init__(self, x: int, y: int, w: int, h: int, text: str,
                 color: tuple, hover_color: tuple,
                 text_color: tuple = C.WHITE, key: str = ""):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.key = key
        self.visible = True
        self.enabled = True

    def draw(self, surf: pygame.Surface, fonts: dict) -> None:
        if not self.visible:
            return
        mx, my = pygame.mouse.get_pos()
        hovered = self.rect.collidepoint(mx, my)
        clr = self.hover_color if (hovered and self.enabled) else self.color
        if not self.enabled:
            clr = C.GRAY_DARK
        pygame.draw.rect(surf, clr, self.rect, border_radius=10)
        pygame.draw.rect(surf, C.WHITE, self.rect, 2, border_radius=10)
        txt = fonts["btn"].render(self.text, True,
                                  self.text_color if self.enabled else C.GRAY)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def clicked(self, pos: tuple) -> bool:
        return self.visible and self.enabled and self.rect.collidepoint(pos)


# ── Chips ─────────────────────────────────────────────────────────────────────

def draw_chip(surf: pygame.Surface, cx: int, cy: int, value: int,
              fonts: dict, selected: bool = False) -> pygame.Rect:
    """Draw a casino chip. Returns clickable rect."""
    color = C.CHIP_COLORS.get(value, C.WHITE)
    r = C.CHIP_RADIUS

    # Shadow
    pygame.draw.circle(surf, (0, 0, 0, 80), (cx + 2, cy + 2), r)
    # Main circle
    pygame.draw.circle(surf, color, (cx, cy), r)
    # Inner ring
    pygame.draw.circle(surf, C.WHITE, (cx, cy), r, 3)
    pygame.draw.circle(surf, color, (cx, cy), r - 6)
    # Dashes around edge
    import math
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x1 = cx + int((r - 4) * math.cos(rad))
        y1 = cy + int((r - 4) * math.sin(rad))
        x2 = cx + int((r + 1) * math.cos(rad))
        y2 = cy + int((r + 1) * math.sin(rad))
        pygame.draw.line(surf, C.WHITE, (x1, y1), (x2, y2), 2)

    # Value text
    txt_color = C.WHITE if value == 100 else C.BLACK
    txt = fonts["chip"].render(f"${value}", True, txt_color)
    surf.blit(txt, txt.get_rect(center=(cx, cy)))

    # Selection ring
    if selected:
        pygame.draw.circle(surf, C.GOLD, (cx, cy), r + 4, 3)

    return pygame.Rect(cx - r, cy - r, r * 2, r * 2)


# ── HUD / Info ────────────────────────────────────────────────────────────────

def draw_top_bar(surf: pygame.Surface, fonts: dict,
                 balance: int, bet: int, score: int = 0,
                 rc: int = 0, tc: float = 0.0,
                 edu_mode: bool = False) -> None:
    """Draw the top information bar."""
    bar = pygame.Rect(0, 0, C.WIN_W, C.TOP_BAR_H)
    pygame.draw.rect(surf, C.FELT_DARK, bar)
    pygame.draw.line(surf, C.GOLD_DARK, (0, C.TOP_BAR_H), (C.WIN_W, C.TOP_BAR_H), 2)

    y = 14
    # Balance
    txt = fonts["info"].render(f"Balance: ${balance}", True, C.WHITE)
    surf.blit(txt, (20, y))

    # Bet
    txt = fonts["info"].render(f"Bet: ${bet}", True, C.GOLD)
    surf.blit(txt, (220, y))

    if edu_mode:
        txt = fonts["info"].render(f"Score: {score}", True, C.PURPLE_LIGHT)
        surf.blit(txt, (400, y))
        txt = fonts["info_sm"].render(f"RC: {rc:+d}  TC: {tc:+.1f}", True, C.CYAN_BTN)
        surf.blit(txt, (560, y))


def draw_label(surf: pygame.Surface, fonts: dict, text: str,
               cx: int, y: int, color: tuple = C.WHITE,
               font_key: str = "info") -> None:
    """Draw centered text."""
    txt = fonts[font_key].render(text, True, color)
    surf.blit(txt, txt.get_rect(center=(cx, y)))


def draw_hud_panel(surf: pygame.Surface, fonts: dict,
                   p_bust: float, cards_21: int,
                   remaining: int, ev_hit: float = 0,
                   ev_stand: float = 0, show_ev: bool = True) -> None:
    """Draw the probability HUD panel at bottom."""
    panel = pygame.Rect(20, C.HUD_Y, C.WIN_W - 40, 130)
    panel_surf = pygame.Surface((panel.w, panel.h), pygame.SRCALPHA)
    panel_surf.fill((0, 0, 0, 120))
    surf.blit(panel_surf, panel.topleft)
    pygame.draw.rect(surf, C.CYAN_BTN, panel, 2, border_radius=8)

    x, y = panel.x + 20, panel.y + 12
    txt = fonts["hud"].render("PROBABILITY HUD", True, C.CYAN_BTN)
    surf.blit(txt, (x, y))

    y += 28
    txt = fonts["hud"].render(
        f"P(bust):  {p_bust:.1f}%     Cards to 21:  {cards_21}     "
        f"Remaining:  {remaining}", True, C.WHITE
    )
    surf.blit(txt, (x, y))

    if show_ev:
        y += 24
        ev_clr = C.GREEN_BTN if ev_hit > ev_stand else C.RED_BTN
        es_clr = C.GREEN_BTN if ev_stand >= ev_hit else C.RED_BTN
        txt = fonts["hud"].render(f"EV(Hit): ", True, C.GRAY_LIGHT)
        surf.blit(txt, (x, y))
        w = txt.get_width()
        txt = fonts["hud"].render(f"{ev_hit:+.3f}", True, ev_clr)
        surf.blit(txt, (x + w, y))
        w2 = w + txt.get_width() + 40
        txt = fonts["hud"].render(f"EV(Stand): ", True, C.GRAY_LIGHT)
        surf.blit(txt, (x + w2, y))
        w3 = w2 + txt.get_width()
        txt = fonts["hud"].render(f"{ev_stand:+.3f}", True, es_clr)
        surf.blit(txt, (x + w3, y))
        best = ">>> Hit" if ev_hint(ev_hit, ev_stand) else ">>> Stand"
        best_clr = C.GOLD
        txt = fonts["hud"].render(f"  {best}", True, best_clr)
        surf.blit(txt, (x + w3 + 80, y))


def ev_hint(ev_h: float, ev_s: float) -> bool:
    return ev_h > ev_s


# ── Popup / Challenge dialog ─────────────────────────────────────────────────

def draw_popup(surf: pygame.Surface, fonts: dict,
               title: str, lines: list[str],
               input_text: str = "", show_input: bool = True,
               result_text: str = "") -> pygame.Rect:
    """Draw a centered popup dialog. Returns popup rect."""
    pw, ph = 600, 350
    px = (C.WIN_W - pw) // 2
    py = (C.WIN_H - ph) // 2
    popup_rect = pygame.Rect(px, py, pw, ph)

    # Overlay
    overlay = pygame.Surface((C.WIN_W, C.WIN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surf.blit(overlay, (0, 0))

    # Popup box
    pygame.draw.rect(surf, C.FELT_DARK, popup_rect, border_radius=12)
    pygame.draw.rect(surf, C.GOLD, popup_rect, 3, border_radius=12)

    # Title
    txt = fonts["popup"].render(title, True, C.GOLD)
    surf.blit(txt, txt.get_rect(center=(C.WIN_W // 2, py + 30)))

    # Question lines
    y = py + 65
    for line in lines:
        txt = fonts["popup_q"].render(line, True, C.WHITE)
        surf.blit(txt, (px + 30, y))
        y += 28

    # Input field
    if show_input and not result_text:
        input_rect = pygame.Rect(px + 30, y + 15, pw - 60, 40)
        pygame.draw.rect(surf, C.WHITE, input_rect, border_radius=6)
        pygame.draw.rect(surf, C.GOLD, input_rect, 2, border_radius=6)
        txt = fonts["input"].render(input_text + "|", True, C.BLACK)
        surf.blit(txt, (input_rect.x + 10, input_rect.y + 8))

        hint = fonts["info_sm"].render("Enter для ответа", True, C.GRAY)
        surf.blit(hint, hint.get_rect(center=(C.WIN_W // 2, y + 75)))

    # Result
    if result_text:
        y_r = py + ph - 80
        for i, rline in enumerate(result_text.split("\n")):
            color = C.GREEN_BTN if i == 0 and "Верно" in rline else (
                C.RED_BTN if i == 0 and "Неверно" in rline else C.GRAY_LIGHT)
            txt = fonts["popup_q"].render(rline.strip(), True, color)
            surf.blit(txt, (px + 30, y_r + i * 24))

    return popup_rect
