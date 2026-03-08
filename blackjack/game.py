"""Main game orchestrator."""

from __future__ import annotations

import random
import time

from .actions import Action, RoundOutcome
from .counter import CardCounter
from .dealer import StandardDealer
from .difficulty import DifficultyConfig, DifficultyLevel, DIFFICULTY_PRESETS
from .input_handler import TerminalInput
from .models import Card, Hand, HandState, Rank, Shoe
from .renderer import Ansi, TerminalRenderer
from .stats import Stats
from .trainer import MathTrainer


class BlackjackGame:
    MAX_SPLITS = 4

    def __init__(
        self,
        edu_mode: bool = False,
        difficulty: DifficultyLevel = DifficultyLevel.MEDIUM,
    ):
        self.cfg: DifficultyConfig = DIFFICULTY_PRESETS[difficulty]
        self.edu_mode = edu_mode
        self.balance = self.cfg.starting_balance

        self.shoe = Shoe(n_decks=self.cfg.n_decks)
        self.renderer = TerminalRenderer(
            edu_mode=edu_mode,
            show_prob_hud=self.cfg.show_prob_hud,
            show_optimal_hint=self.cfg.show_optimal_hint,
        )
        self.input = TerminalInput()
        self.dealer_strategy = StandardDealer(hit_soft_17=self.cfg.dealer_hits_soft17)
        self.stats = Stats(initial_balance=self.cfg.starting_balance)
        self.counter = CardCounter()
        self.trainer = (
            MathTrainer(
                allowed_levels=self.cfg.allowed_challenge_levels,
                tolerance_mult=self.cfg.tolerance_mult,
            )
            if edu_mode
            else None
        )

        self.shoe.on_reshuffle(self._on_reshuffle)

    def _on_reshuffle(self) -> None:
        self.renderer.show_message(
            f"{Ansi.YELLOW}Перетасовка колоды...{Ansi.RST}"
        )
        self.counter.reset()

    def _draw(self) -> Card:
        card = self.shoe.draw()
        self.counter.update(card)
        return card

    # ── Public API ────────────────────────────────────────────────────────

    def run(self) -> None:
        self.renderer.clear()
        self._show_rules()
        self.input.wait("Enter чтобы начать...")

        while self.balance >= self.cfg.min_bet:
            if not self._play_round():
                break

        self.renderer.clear()
        if self.balance < self.cfg.min_bet:
            self.renderer.show_message(
                f"{Ansi.RED}{Ansi.BOLD}Банкрот! Баланс: ${self.balance}{Ansi.RST}"
            )
        else:
            self.renderer.show_message(
                f"{Ansi.GREEN}Вы уходите с ${self.balance}{Ansi.RST}"
            )
        print(self.stats.display(self.balance, self.trainer))
        print(f"\n  {Ansi.DIM}Спасибо за игру!{Ansi.RST}\n")

    # ── Round flow ────────────────────────────────────────────────────────

    def _play_round(self) -> bool:
        self.stats.rounds += 1
        self.renderer.clear()

        bet = self.input.get_bet(self.balance, self.cfg.min_bet)
        if bet is None:
            return False
        self.balance -= bet

        player_hands = [Hand(bet=bet)]
        dealer = Hand()
        player_hands[0].add(self._draw())
        dealer.add(self._draw())
        player_hands[0].add(self._draw())
        dealer.add(self._draw())

        self._refresh(dealer, player_hands, hide_dealer=True)

        # Insurance
        if dealer.cards[1].rank is Rank.ACE:
            if self._handle_insurance(dealer, player_hands, bet):
                return True

        # Naturals
        if self._handle_naturals(dealer, player_hands, bet):
            return True

        # Player turn
        self._player_turn(dealer, player_hands)

        # All bust?
        if all(h.state is HandState.BUST for h in player_hands):
            self._refresh(dealer, player_hands, hide_dealer=False,
                          message=f"{Ansi.RED}Все руки перебор!{Ansi.RST}")
            for _ in player_hands:
                self.stats.record(RoundOutcome.LOSE)
            self.input.wait()
            return True

        # Dealer turn
        self._dealer_turn(dealer, player_hands)

        # Settle
        self._settle(dealer, player_hands)
        return True

    # ── Insurance ─────────────────────────────────────────────────────────

    def _handle_insurance(self, dealer: Hand, player_hands: list[Hand],
                          bet: int) -> bool:
        ins_cost = bet // 2
        if self.balance < ins_cost:
            if dealer.is_blackjack:
                return self._resolve_dealer_bj(dealer, player_hands)
            return False

        # Edu: challenge about P(BJ) before insurance decision
        if self.edu_mode and self.trainer:
            ch = self.trainer._challenge_conditional_bj(
                player_hands[0], dealer, self.shoe, self.counter
            )
            if ch:
                raw = self.input.get_challenge_answer(ch)
                _, feedback = self.trainer.check(ch, raw)
                self.renderer.show_message(feedback)
                self.input.wait()
                self._refresh(dealer, player_hands, hide_dealer=True)

        if not self.input.get_yes_no("Страховка?"):
            if dealer.is_blackjack:
                return self._resolve_dealer_bj(dealer, player_hands)
            return False

        self.balance -= ins_cost
        if dealer.is_blackjack:
            self.balance += ins_cost * 3
            msg = f"{Ansi.GREEN}Страховка сработала! +${ins_cost * 2}{Ansi.RST}"
            self._refresh(dealer, player_hands, hide_dealer=False, message=msg)
            if player_hands[0].is_blackjack:
                self.balance += bet
                self.stats.record(RoundOutcome.PUSH)
                self.renderer.show_message(
                    f"{Ansi.YELLOW}Push — оба Blackjack{Ansi.RST}"
                )
            else:
                self.stats.record(RoundOutcome.LOSE)
                self.renderer.show_message(
                    f"{Ansi.RED}Дилер: Blackjack{Ansi.RST}"
                )
            self.input.wait()
            return True

        self._refresh(dealer, player_hands, hide_dealer=True,
                      message=f"{Ansi.RED}Страховка не сработала (-${ins_cost}){Ansi.RST}")
        time.sleep(1)
        return False

    # ── Naturals ──────────────────────────────────────────────────────────

    def _handle_naturals(self, dealer: Hand, player_hands: list[Hand],
                         bet: int) -> bool:
        p_bj = player_hands[0].is_blackjack
        d_bj = dealer.is_blackjack

        if p_bj and d_bj:
            self.balance += bet
            self.stats.record(RoundOutcome.PUSH)
            self._refresh(dealer, player_hands, hide_dealer=False,
                          message=f"{Ansi.YELLOW}Push! Оба Blackjack{Ansi.RST}")
            self.input.wait()
            return True

        if p_bj:
            winnings = int(bet + bet * self.cfg.blackjack_payout)
            self.balance += winnings
            self.stats.record(RoundOutcome.BLACKJACK)
            self._refresh(
                dealer, player_hands, hide_dealer=False,
                message=f"{Ansi.GREEN}{Ansi.BOLD}BLACKJACK! +${winnings - bet}{Ansi.RST}",
            )
            self.input.wait()
            return True

        if d_bj:
            return self._resolve_dealer_bj(dealer, player_hands)

        return False

    def _resolve_dealer_bj(self, dealer: Hand, player_hands: list[Hand]) -> bool:
        self.stats.record(RoundOutcome.LOSE)
        self._refresh(dealer, player_hands, hide_dealer=False,
                      message=f"{Ansi.RED}Дилер: Blackjack!{Ansi.RST}")
        self.input.wait()
        return True

    # ── Player turn ───────────────────────────────────────────────────────

    def _player_turn(self, dealer: Hand, player_hands: list[Hand]) -> None:
        idx = 0
        challenge_asked = False

        while idx < len(player_hands):
            hand = player_hands[idx]

            while hand.state is HandState.ACTIVE:
                self._refresh(dealer, player_hands, active_idx=idx, hide_dealer=True)
                self.renderer.show_prob_hud_inline(hand, dealer, self.shoe)

                # Math challenge (once per round)
                if (self.edu_mode and self.trainer and not challenge_asked
                        and random.random() < self.cfg.challenge_chance):
                    challenge_asked = True
                    ch = self.trainer.generate(
                        hand, dealer, self.shoe, self.counter
                    )
                    if ch:
                        raw = self.input.get_challenge_answer(ch)
                        _, feedback = self.trainer.check(ch, raw)
                        self.renderer.show_message(feedback)
                        self.input.wait()
                        self._refresh(dealer, player_hands, active_idx=idx,
                                      hide_dealer=True)
                        self.renderer.show_prob_hud_inline(hand, dealer, self.shoe)

                actions = self._available_actions(hand, player_hands)
                action = self.input.get_action(actions)

                match action:
                    case Action.HIT:
                        hand.add(self._draw())
                    case Action.STAND:
                        hand.stand()
                    case Action.DOUBLE:
                        self.balance -= hand.bet
                        hand.bet *= 2
                        hand.is_doubled = True
                        hand.add(self._draw())
                        if hand.state is HandState.ACTIVE:
                            hand.stand()
                    case Action.SPLIT:
                        new_hand = self._split_hand(hand)
                        player_hands.insert(idx + 1, new_hand)
                        continue
                    case Action.SURRENDER:
                        hand.surrender()
                        self.balance += hand.bet // 2

            idx += 1

    def _split_hand(self, hand: Hand) -> Hand:
        self.balance -= hand.bet
        second_card = hand.cards.pop()
        hand.is_split = True
        hand.add(self._draw())

        new_hand = Hand(cards=[second_card], bet=hand.bet, is_split=True)
        new_hand.add(self._draw())
        return new_hand

    def _available_actions(self, hand: Hand, all_hands: list[Hand]) -> list[Action]:
        actions = [Action.HIT, Action.STAND]
        if hand.can_double and self.balance >= hand.bet:
            actions.append(Action.DOUBLE)
        if (hand.can_split and self.balance >= hand.bet
                and len(all_hands) < self.MAX_SPLITS):
            actions.append(Action.SPLIT)
        if len(hand.cards) == 2 and not hand.is_split:
            actions.append(Action.SURRENDER)
        return actions

    # ── Dealer turn ───────────────────────────────────────────────────────

    def _dealer_turn(self, dealer: Hand, player_hands: list[Hand]) -> None:
        self._refresh(dealer, player_hands, hide_dealer=False,
                      message=f"{Ansi.DIM}Дилер открывает карты...{Ansi.RST}")
        time.sleep(0.8)
        while self.dealer_strategy.should_hit(dealer):
            dealer.add(self._draw())
            self._refresh(dealer, player_hands, hide_dealer=False,
                          message=f"{Ansi.DIM}Дилер берёт карту...{Ansi.RST}")
            time.sleep(0.8)

    # ── Settlement ────────────────────────────────────────────────────────

    def _settle(self, dealer: Hand, player_hands: list[Hand]) -> None:
        results: list[str] = []
        total_return = 0

        for i, hand in enumerate(player_hands):
            label = f"Рука {i + 1} " if len(player_hands) > 1 else ""
            outcome, payout, tag = self._judge(
                hand, dealer.value, dealer.is_bust, label
            )
            total_return += payout
            self.stats.record(outcome)
            results.append(tag)

        self.balance += total_return
        self._refresh(dealer, player_hands, hide_dealer=False,
                      message="  |  ".join(results))
        self.input.wait()

    @staticmethod
    def _judge(hand: Hand, dealer_val: int, dealer_bust: bool,
               label: str) -> tuple[RoundOutcome, int, str]:
        pv = hand.value

        if hand.state is HandState.SURRENDER:
            return (RoundOutcome.SURRENDER, 0,
                    f"{Ansi.DIM}{label}SURRENDER{Ansi.RST}")
        if hand.state is HandState.BUST:
            return (RoundOutcome.LOSE, 0,
                    f"{Ansi.RED}{label}BUST (-${hand.bet}){Ansi.RST}")
        if dealer_bust or pv > dealer_val:
            return (RoundOutcome.WIN, hand.bet * 2,
                    f"{Ansi.GREEN}{label}WIN +${hand.bet}{Ansi.RST}")
        if pv == dealer_val:
            return (RoundOutcome.PUSH, hand.bet,
                    f"{Ansi.YELLOW}{label}PUSH{Ansi.RST}")
        return (RoundOutcome.LOSE, 0,
                f"{Ansi.RED}{label}LOSE -${hand.bet}{Ansi.RST}")

    # ── Helpers ───────────────────────────────────────────────────────────

    def _refresh(self, dealer: Hand, player_hands: list[Hand],
                 active_idx: int = 0, hide_dealer: bool = True,
                 message: str = "") -> None:
        self.renderer.show_table(
            dealer, player_hands, active_idx, hide_dealer,
            self.balance, message,
            self.trainer, self.counter, self.shoe,
        )

    def _show_rules(self) -> None:
        c = self.cfg
        mode = (f"{Ansi.MAGENTA}{Ansi.BOLD}ОБУЧЕНИЕ{Ansi.RST}"
                if self.edu_mode
                else f"{Ansi.GREEN}ОБЫЧНАЯ ИГРА{Ansi.RST}")
        diff_color = {
            DifficultyLevel.EASY: Ansi.GREEN,
            DifficultyLevel.MEDIUM: Ansi.YELLOW,
            DifficultyLevel.HARD: Ansi.RED,
        }[c.level]

        bj_pay = "6:5" if c.blackjack_payout < 1.3 else "3:2"
        soft17 = "Hit" if c.dealer_hits_soft17 else "Stand"

        print(f"""
{Ansi.YELLOW}{Ansi.BOLD}    +==========================================+
    |     S  B L A C K J A C K  2 1  H       |
    |        Terminal Edition v3 / EDU         |
    +==========================================+{Ansi.RST}

  Режим: {mode}
  Сложность: {diff_color}{Ansi.BOLD}{c.level.label} ({c.level.label_en}){Ansi.RST}

  {Ansi.WHITE}Правила:{Ansi.RST}
  {Ansi.DIM}* Набери 21 или ближе к 21, чем дилер
  * Туз = 11 или 1  |  J/Q/K = 10
  * Blackjack платит {bj_pay}
  * Дилер soft 17: {soft17}  |  Колоды: {c.n_decks}
  * Hit, Stand, Double, Split (до 4 рук), Surrender
  * Стартовый баланс: ${c.starting_balance}  |  Мин. ставка: ${c.min_bet}{Ansi.RST}""")

        if self.edu_mode:
            hud = "Да + подсказки" if c.show_optimal_hint else ("Да" if c.show_prob_hud else "Нет")
            print(f"""
  {Ansi.MAGENTA}{Ansi.BOLD}Режим обучения:{Ansi.RST}
  {Ansi.DIM}* Probability HUD: {hud}
  * Частота задач: {c.challenge_chance:.0%}
  * Точность ответов: x{c.tolerance_mult:.1f}
  * Задачи: {', '.join({1:'Easy',2:'Medium',3:'Hard'}[l] for l in c.allowed_challenge_levels)}
  * Типы задач:
    - P(bust) при Hit (формула Лапласа)
    - Сколько карт до 21 (комбинаторика)
    - Hi-Lo Running Count (card counting)
    - P(dealer bust) (условная вероятность)
    - EV: Hit vs Stand (мат. ожидание)
    - P(Blackjack у дилера) (формула Байеса){Ansi.RST}
            """)
