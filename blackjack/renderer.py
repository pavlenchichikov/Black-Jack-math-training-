"""Terminal renderer: ASCII cards, table display, probability HUD."""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from .models import Card, Hand, HandState, Shoe

if TYPE_CHECKING:
    from .counter import CardCounter
    from .trainer import MathTrainer


# ── ANSI codes ────────────────────────────────────────────────────────────────

class Ansi:
    RST = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"; UNDER = "\033[4m"
    RED = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
    BLUE = "\033[94m"; MAGENTA = "\033[95m"; CYAN = "\033[96m"; WHITE = "\033[97m"


# ── Renderer ──────────────────────────────────────────────────────────────────

class TerminalRenderer:
    CARD_HEIGHT = 7

    def __init__(self, edu_mode: bool = False,
                 show_prob_hud: bool = True,
                 show_optimal_hint: bool = False) -> None:
        self.edu_mode = edu_mode
        self.show_prob_hud = show_prob_hud
        self.show_optimal_hint = show_optimal_hint

    def clear(self) -> None:
        os.system("cls" if sys.platform == "win32" else "clear")

    def show_message(self, msg: str) -> None:
        print(f"\n  {msg}")

    def show_table(
        self,
        dealer: Hand,
        player_hands: list[Hand],
        active_idx: int = 0,
        hide_dealer: bool = True,
        balance: int = 0,
        message: str = "",
        trainer: MathTrainer | None = None,
        counter: CardCounter | None = None,
        shoe: Shoe | None = None,
    ) -> None:
        self.clear()
        self._banner()
        self._info_bar(balance, player_hands, trainer, counter, shoe)

        if message:
            print(f"\n  {message}")

        # Dealer
        dv_str = "?" if hide_dealer else str(dealer.value)
        print(f"\n  {Ansi.DIM}-- Дилер ({dv_str}) --{Ansi.RST}")
        print(self._render_hand(dealer.cards, hide_first=hide_dealer))

        # Player hands
        for i, hand in enumerate(player_hands):
            marker = (f" {Ansi.GREEN}<{Ansi.RST}"
                      if len(player_hands) > 1 and i == active_idx else "")
            label = f"Рука {i + 1}" if len(player_hands) > 1 else "Игрок"
            status = self._hand_status_tag(hand)
            dbl = " x2" if hand.is_doubled else ""
            print(f"\n  {Ansi.DIM}-- {label} ({hand.value})"
                  f"  [${hand.bet}{dbl}]{status}{marker} --{Ansi.RST}")
            print(self._render_hand(hand.cards))

        # Probability HUD (after dealer reveal)
        if self.edu_mode and self.show_prob_hud and shoe and not hide_dealer:
            self._show_prob_hud(player_hands, dealer, shoe)

    def show_prob_hud_inline(self, hand: Hand, dealer: Hand, shoe: Shoe) -> None:
        """Probability HUD during player turn."""
        if not self.edu_mode or not self.show_prob_hud:
            return

        from .probability import ProbabilityEngine

        p_bust = ProbabilityEngine.bust_probability(hand, shoe) * 100
        c21, _ = ProbabilityEngine.cards_to_target(hand, 21, shoe)

        print(f"\n  {Ansi.CYAN}{Ansi.BOLD}--- PROBABILITY HUD ---{Ansi.RST}")
        print(f"  {Ansi.CYAN}P(bust при Hit): {p_bust:.1f}%"
              f"   |   Карт до 21: {c21} шт"
              f"   |   Осталось в shoe: {shoe.remaining}{Ansi.RST}")

        if self.show_optimal_hint:
            ev_h = ProbabilityEngine.ev_hit(hand, dealer.cards[1], shoe, n_sims=500)
            ev_s = ProbabilityEngine.ev_stand(hand, dealer.cards[1], shoe, n_sims=500)
            best = "Hit" if ev_h > ev_s else "Stand"
            print(f"  {Ansi.GREEN}Подсказка: {best} "
                  f"(EV Hit={ev_h:+.2f}  EV Stand={ev_s:+.2f}){Ansi.RST}")

    # ── Card rendering ────────────────────────────────────────────────────

    def _render_card(self, card: Card, hidden: bool = False) -> list[str]:
        if hidden:
            return [
                "\u250c\u2500\u2500\u2500\u2500\u2500\u2510",
                "\u2502\u2591\u2591\u2591\u2591\u2591\u2502",
                "\u2502\u2591\u2591\u2591\u2591\u2591\u2502",
                "\u2502\u2591 ? \u2591\u2502",
                "\u2502\u2591\u2591\u2591\u2591\u2591\u2502",
                "\u2502\u2591\u2591\u2591\u2591\u2591\u2502",
                "\u2514\u2500\u2500\u2500\u2500\u2500\u2518",
            ]
        clr = Ansi.RED if card.suit.is_red else Ansi.WHITE
        r = card.rank.label.ljust(2) if len(card.rank.label) < 2 else card.rank.label
        r2 = card.rank.label.rjust(2) if len(card.rank.label) < 2 else card.rank.label
        s = card.suit.symbol
        return [
            "\u250c\u2500\u2500\u2500\u2500\u2500\u2510",
            f"\u2502{clr}{r}{Ansi.RST}   \u2502",
            f"\u2502     \u2502",
            f"\u2502  {clr}{s}{Ansi.RST}  \u2502",
            f"\u2502     \u2502",
            f"\u2502   {clr}{r2}{Ansi.RST}\u2502",
            "\u2514\u2500\u2500\u2500\u2500\u2500\u2518",
        ]

    def _render_hand(self, cards: list[Card], hide_first: bool = False) -> str:
        rendered = [
            self._render_card(c, hidden=(i == 0 and hide_first))
            for i, c in enumerate(cards)
        ]
        return "\n".join(
            "  ".join(rendered[j][row] for j in range(len(rendered)))
            for row in range(self.CARD_HEIGHT)
        )

    @staticmethod
    def _hand_status_tag(hand: Hand) -> str:
        if hand.state is HandState.BUST:
            return f"  {Ansi.RED}BUST{Ansi.RST}"
        if hand.state is HandState.BLACKJACK:
            return f"  {Ansi.YELLOW}BLACKJACK!{Ansi.RST}"
        if hand.state is HandState.SURRENDER:
            return f"  {Ansi.DIM}SURRENDER{Ansi.RST}"
        return ""

    def _info_bar(self, balance: int, hands: list[Hand],
                  trainer: MathTrainer | None, counter: CardCounter | None,
                  shoe: Shoe | None) -> None:
        total_bet = sum(h.bet for h in hands)
        parts = [f"{Ansi.CYAN}Баланс: ${balance}{Ansi.RST}",
                 f"{Ansi.YELLOW}Ставка: ${total_bet}{Ansi.RST}"]

        if self.edu_mode and trainer:
            parts.append(f"{Ansi.MAGENTA}Score: {trainer.score} "
                         f"({trainer.accuracy:.0f}%){Ansi.RST}")
        if self.edu_mode and counter and shoe:
            tc = counter.true_count(shoe.remaining_decks)
            parts.append(f"{Ansi.BLUE}RC: {counter.running_count:+d} "
                         f"TC: {tc:+.1f}{Ansi.RST}")

        print(f"  {'    '.join(parts)}")

    def _show_prob_hud(self, player_hands: list[Hand], dealer: Hand,
                       shoe: Shoe) -> None:
        from .probability import ProbabilityEngine

        for i, hand in enumerate(player_hands):
            if hand.state in (HandState.BUST, HandState.SURRENDER):
                continue
            label = f"Рука {i + 1}" if len(player_hands) > 1 else "Итог"
            ev_s = ProbabilityEngine.ev_stand(hand, dealer.cards[1], shoe, n_sims=500)
            print(f"\n  {Ansi.CYAN}[{label}] EV(Stand)={ev_s:+.2f}{Ansi.RST}")

    @staticmethod
    def _banner() -> None:
        print(f"""
{Ansi.YELLOW}{Ansi.BOLD}    +==========================================+
    |     S  B L A C K J A C K  2 1  H       |
    |        Terminal Edition v3 / EDU         |
    +==========================================+{Ansi.RST}""")
