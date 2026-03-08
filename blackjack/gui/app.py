"""Main Pygame application: game loop, state machine, event handling."""

from __future__ import annotations

import math
import sys
import time
from dataclasses import dataclass, field
from enum import Enum, auto

import pygame

from ..models import Card, Hand, HandState, Rank, Shoe
from ..actions import Action, RoundOutcome
from ..counter import CardCounter
from ..dealer import StandardDealer
from ..difficulty import DifficultyConfig, DifficultyLevel, DIFFICULTY_PRESETS
from ..probability import ProbabilityEngine
from ..stats import Stats as GameStats
from ..trainer import MathTrainer, Challenge

from . import config as C
from . import sprites as S


# ══════════════════════════════════════════════════════════════════════════════
#  GAME STATE
# ══════════════════════════════════════════════════════════════════════════════

class State(Enum):
    MENU       = auto()
    DIFFICULTY = auto()
    BETTING    = auto()
    DEALING    = auto()
    PLAYER     = auto()
    CHALLENGE  = auto()
    DEALER     = auto()
    RESULT     = auto()
    GAME_OVER  = auto()


# ── Animation ─────────────────────────────────────────────────────────────────

@dataclass
class CardAnim:
    card: Card
    sx: float; sy: float
    ex: float; ey: float
    duration: float
    elapsed: float = 0.0
    hidden: bool = False
    done: bool = False

    @property
    def t(self) -> float:
        return min(1.0, self.elapsed / self.duration)

    @property
    def pos(self) -> tuple[float, float]:
        t = 1 - (1 - self.t) ** 3  # ease-out cubic
        return (self.sx + (self.ex - self.sx) * t,
                self.sy + (self.ey - self.sy) * t)


# ══════════════════════════════════════════════════════════════════════════════
#  APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

class App:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((C.WIN_W, C.WIN_H))
        pygame.display.set_caption(C.TITLE)
        self.clock = pygame.time.Clock()
        self.fonts = S.init_fonts()
        self.running = True

        # Game state
        self.state = State.MENU
        self.edu_mode = False
        self.difficulty = DifficultyLevel.MEDIUM
        self.cfg: DifficultyConfig | None = None

        # Game objects (initialized on new game)
        self.shoe: Shoe | None = None
        self.counter = CardCounter()
        self.trainer: MathTrainer | None = None
        self.dealer_strategy: StandardDealer | None = None
        self.stats: GameStats | None = None
        self.balance = 1000
        self.current_bet = 0
        self.selected_chip = 25

        # Round state
        self.dealer_hand: Hand | None = None
        self.player_hands: list[Hand] = []
        self.active_hand_idx = 0
        self.hide_dealer = True
        self.message = ""
        self.message_color = C.WHITE
        self.message_timer = 0.0

        # Animation
        self.anims: list[CardAnim] = []
        self.deal_queue: list[tuple] = []  # (target_hand_idx, hidden, callback)
        self.after_deal_cb: callable | None = None

        # Challenge
        self.current_challenge: Challenge | None = None
        self.challenge_input = ""
        self.challenge_result = ""
        self.challenge_done = False
        self.challenge_asked_this_round = False

        # Buttons
        self._init_buttons()

    # ── Button setup ──────────────────────────────────────────────────────

    def _init_buttons(self) -> None:
        bw, bh = 120, 45
        gap = 15
        base_x = C.WIN_W // 2 - (5 * bw + 4 * gap) // 2
        y = C.BUTTONS_Y

        self.btn_hit = S.Button(base_x, y, bw, bh, "Hit (H)",
                                C.GREEN_BTN, C.GREEN_HOVER, key="h")
        self.btn_stand = S.Button(base_x + (bw + gap), y, bw, bh, "Stand (S)",
                                  C.RED_BTN, C.RED_HOVER, key="s")
        self.btn_double = S.Button(base_x + 2 * (bw + gap), y, bw, bh, "Double (D)",
                                   C.CYAN_BTN, C.CYAN_HOVER, key="d")
        self.btn_split = S.Button(base_x + 3 * (bw + gap), y, bw, bh, "Split (P)",
                                  C.YELLOW_BTN, C.YELLOW_HOVER, key="p")
        self.btn_surr = S.Button(base_x + 4 * (bw + gap), y, bw, bh, "Surrender",
                                 C.GRAY, C.GRAY_LIGHT, key="r")
        self.action_buttons = [self.btn_hit, self.btn_stand, self.btn_double,
                               self.btn_split, self.btn_surr]

        # Betting buttons
        self.btn_deal = S.Button(C.WIN_W // 2 - 75, C.CHIPS_Y + 70, 150, 45,
                                 "DEAL", C.GOLD_DARK, C.GOLD)
        self.btn_clear = S.Button(C.WIN_W // 2 + 100, C.CHIPS_Y + 70, 100, 45,
                                  "Clear", C.GRAY, C.GRAY_LIGHT)

        # Menu buttons
        self.btn_menu_play = S.Button(C.WIN_W // 2 - 160, 350, 320, 55,
                                      "Обычная игра", C.GREEN_BTN, C.GREEN_HOVER)
        self.btn_menu_edu = S.Button(C.WIN_W // 2 - 160, 420, 320, 55,
                                     "Обучение (математика)", C.PURPLE, C.PURPLE_LIGHT)
        self.btn_menu_quit = S.Button(C.WIN_W // 2 - 100, 500, 200, 45,
                                      "Выход", C.GRAY, C.GRAY_LIGHT)

        # Difficulty buttons
        self.btn_diff_easy = S.Button(C.WIN_W // 2 - 160, 280, 320, 50,
                                      "Легкий", C.GREEN_BTN, C.GREEN_HOVER)
        self.btn_diff_med = S.Button(C.WIN_W // 2 - 160, 345, 320, 50,
                                     "Средний", C.YELLOW_BTN, C.YELLOW_HOVER)
        self.btn_diff_hard = S.Button(C.WIN_W // 2 - 160, 410, 320, 50,
                                      "Сложный", C.RED_BTN, C.RED_HOVER)

        # Difficulty: back button
        self.btn_diff_back = S.Button(C.WIN_W // 2 - 100, 490, 200, 45,
                                      "Назад", C.GRAY, C.GRAY_LIGHT)

        # Result / continue
        self.btn_continue = S.Button(C.WIN_W // 2 - 100, 550, 200, 45,
                                     "Продолжить", C.GREEN_BTN, C.GREEN_HOVER)
        self.btn_new_game = S.Button(C.WIN_W // 2 - 100, 500, 200, 45,
                                     "Новая игра", C.GREEN_BTN, C.GREEN_HOVER)

        # Menu button (shown during betting/result to go back to main menu)
        self.btn_to_menu = S.Button(20, C.WIN_H - 55, 130, 40,
                                    "Меню (Esc)", C.GRAY_DARK, C.GRAY)

    # ── New game ──────────────────────────────────────────────────────────

    def _start_game(self) -> None:
        self.cfg = DIFFICULTY_PRESETS[self.difficulty]
        self.balance = self.cfg.starting_balance
        self.shoe = Shoe(n_decks=self.cfg.n_decks)
        self.counter = CardCounter()
        self.dealer_strategy = StandardDealer(hit_soft_17=self.cfg.dealer_hits_soft17)
        self.stats = GameStats(initial_balance=self.cfg.starting_balance)
        self.trainer = (
            MathTrainer(
                allowed_levels=self.cfg.allowed_challenge_levels,
                tolerance_mult=self.cfg.tolerance_mult,
            ) if self.edu_mode else None
        )
        self.current_bet = 0
        self.selected_chip = 25
        self.state = State.BETTING

    def _draw_card(self) -> Card:
        card = self.shoe.draw()
        self.counter.update(card)
        return card

    # ── Main loop ─────────────────────────────────────────────────────────

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(C.FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._render()
        pygame.quit()

    # ── Events ────────────────────────────────────────────────────────────

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if self.state == State.MENU:
                self._event_menu(event)
            elif self.state == State.DIFFICULTY:
                self._event_difficulty(event)
            elif self.state == State.BETTING:
                self._event_betting(event)
            elif self.state == State.PLAYER:
                self._event_player(event)
            elif self.state == State.CHALLENGE:
                self._event_challenge(event)
            elif self.state == State.RESULT:
                self._event_result(event)
            elif self.state == State.GAME_OVER:
                self._event_gameover(event)

    def _event_menu(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.btn_menu_play.clicked(pos):
                self.edu_mode = False
                self._show_difficulty_select()
            elif self.btn_menu_edu.clicked(pos):
                self.edu_mode = True
                self._show_difficulty_select()
            elif self.btn_menu_quit.clicked(pos):
                self.running = False

    def _show_difficulty_select(self) -> None:
        self.state = State.DIFFICULTY

    def _event_difficulty(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.btn_diff_easy.clicked(pos):
                self.difficulty = DifficultyLevel.EASY
                self._start_game()
            elif self.btn_diff_med.clicked(pos):
                self.difficulty = DifficultyLevel.MEDIUM
                self._start_game()
            elif self.btn_diff_hard.clicked(pos):
                self.difficulty = DifficultyLevel.HARD
                self._start_game()
            elif self.btn_diff_back.clicked(pos):
                self.state = State.MENU
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = State.MENU

    def _go_to_menu(self) -> None:
        self.state = State.MENU
        self.cfg = None

    def _event_betting(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.btn_to_menu.clicked(pos):
                self._go_to_menu()
                return

            # Chip selection
            for i, denom in enumerate(C.CHIP_DENOMS):
                cx = C.WIN_W // 2 - 200 + i * 90
                cy = C.CHIPS_Y + 30
                r = C.CHIP_RADIUS
                if (pos[0] - cx) ** 2 + (pos[1] - cy) ** 2 <= r ** 2:
                    if self.current_bet + denom <= self.balance:
                        self.current_bet += denom
                    return

            if self.btn_clear.clicked(pos):
                self.current_bet = 0
            elif self.btn_deal.clicked(pos) and self.current_bet >= self.cfg.min_bet:
                self._start_round()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and self.current_bet >= self.cfg.min_bet:
                self._start_round()
            elif event.key == pygame.K_ESCAPE:
                self._go_to_menu()

    def _event_player(self, event: pygame.event.Event) -> None:
        action = None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.btn_hit.clicked(pos):
                action = Action.HIT
            elif self.btn_stand.clicked(pos):
                action = Action.STAND
            elif self.btn_double.clicked(pos) and self.btn_double.enabled:
                action = Action.DOUBLE
            elif self.btn_split.clicked(pos) and self.btn_split.enabled:
                action = Action.SPLIT
            elif self.btn_surr.clicked(pos) and self.btn_surr.enabled:
                action = Action.SURRENDER

        elif event.type == pygame.KEYDOWN:
            key_map = {
                pygame.K_h: Action.HIT, pygame.K_1: Action.HIT,
                pygame.K_s: Action.STAND, pygame.K_2: Action.STAND,
                pygame.K_d: Action.DOUBLE, pygame.K_3: Action.DOUBLE,
                pygame.K_p: Action.SPLIT, pygame.K_4: Action.SPLIT,
                pygame.K_r: Action.SURRENDER, pygame.K_5: Action.SURRENDER,
            }
            action = key_map.get(event.key)

        if action:
            self._do_action(action)

    def _event_challenge(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if self.challenge_done:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.state = State.PLAYER
                    self.current_challenge = None
                    self.challenge_result = ""
                    self.challenge_done = False
                return

            if event.key == pygame.K_RETURN and self.challenge_input:
                self._submit_challenge()
            elif event.key == pygame.K_BACKSPACE:
                self.challenge_input = self.challenge_input[:-1]
            elif event.unicode and event.unicode in "0123456789.,-+":
                self.challenge_input += event.unicode

    def _event_result(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_to_menu.clicked(event.pos):
                self._go_to_menu()
                return
            if self.btn_continue.clicked(event.pos):
                self._next_round()
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._next_round()
            elif event.key == pygame.K_ESCAPE:
                self._go_to_menu()

    def _event_gameover(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_new_game.clicked(event.pos):
                self.state = State.MENU
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.state = State.MENU

    # ── Game logic ────────────────────────────────────────────────────────

    def _start_round(self) -> None:
        self.balance -= self.current_bet
        self.player_hands = [Hand(bet=self.current_bet)]
        self.dealer_hand = Hand()
        self.active_hand_idx = 0
        self.hide_dealer = True
        self.message = ""
        self.challenge_asked_this_round = False
        self.anims.clear()
        self.stats.rounds += 1

        # Queue 4 cards: P, D, P, D(hidden)
        self.deal_queue = [
            ("player", 0, False),
            ("dealer", -1, False),
            ("player", 0, False),
            ("dealer", -1, True),
        ]
        self.state = State.DEALING
        self._deal_next()

    def _deal_next(self) -> None:
        if not self.deal_queue:
            # All dealt — check naturals
            self._after_deal()
            return

        target, hand_idx, hidden = self.deal_queue.pop(0)
        card = self._draw_card()

        if target == "player":
            hand = self.player_hands[hand_idx if hand_idx >= 0 else 0]
            n = len(hand.cards)
            cx = C.WIN_W // 2
            total = (n + 1) * C.CARD_W + n * C.CARD_GAP
            ex = cx - total // 2 + n * (C.CARD_W + C.CARD_GAP)
            ey = C.PLAYER_Y
            hand.add(card)
        else:
            hand = self.dealer_hand
            n = len(hand.cards)
            cx = C.WIN_W // 2
            total = (n + 1) * C.CARD_W + n * C.CARD_GAP
            ex = cx - total // 2 + n * (C.CARD_W + C.CARD_GAP)
            ey = C.DEALER_Y
            hand.add(card)

        anim = CardAnim(card=card, sx=C.SHOE_POS[0], sy=C.SHOE_POS[1],
                         ex=ex, ey=ey, duration=C.DEAL_SPEED, hidden=hidden)
        self.anims.append(anim)

    def _after_deal(self) -> None:
        ph = self.player_hands[0]
        dh = self.dealer_hand

        # Check naturals
        if ph.is_blackjack and dh.is_blackjack:
            self.balance += self.current_bet
            self.stats.record(RoundOutcome.PUSH)
            self._show_result("PUSH — оба Blackjack", C.GOLD)
            return
        if ph.is_blackjack:
            win = int(self.current_bet + self.current_bet * self.cfg.blackjack_payout)
            self.balance += win
            self.stats.record(RoundOutcome.BLACKJACK)
            self._show_result(f"BLACKJACK! +${win - self.current_bet}", C.GOLD)
            return
        if dh.is_blackjack:
            self.hide_dealer = False
            self.stats.record(RoundOutcome.LOSE)
            self._show_result("Дилер: Blackjack!", C.RED_SUIT)
            return

        # Maybe trigger challenge
        if (self.edu_mode and self.trainer and not self.challenge_asked_this_round
                and self.cfg and hash(time.time()) % 100 < self.cfg.challenge_chance * 100):
            ch = self.trainer.generate(ph, dh, self.shoe, self.counter)
            if ch:
                self.challenge_asked_this_round = True
                self.current_challenge = ch
                self.challenge_input = ""
                self.challenge_result = ""
                self.challenge_done = False
                self.state = State.CHALLENGE
                return

        self.state = State.PLAYER

    def _do_action(self, action: Action) -> None:
        hand = self.player_hands[self.active_hand_idx]

        if action == Action.HIT:
            hand.add(self._draw_card())
            if hand.is_bust:
                hand.state = HandState.BUST
                self._advance_hand()

        elif action == Action.STAND:
            hand.stand()
            self._advance_hand()

        elif action == Action.DOUBLE and hand.can_double and self.balance >= hand.bet:
            self.balance -= hand.bet
            hand.bet *= 2
            hand.is_doubled = True
            hand.add(self._draw_card())
            if hand.state == HandState.ACTIVE:
                hand.stand()
            self._advance_hand()

        elif action == Action.SPLIT and hand.can_split and self.balance >= hand.bet:
            self.balance -= hand.bet
            second = hand.cards.pop()
            hand.is_split = True
            hand.add(self._draw_card())
            new_hand = Hand(cards=[second], bet=hand.bet, is_split=True)
            new_hand.add(self._draw_card())
            self.player_hands.insert(self.active_hand_idx + 1, new_hand)

        elif action == Action.SURRENDER and len(hand.cards) == 2 and not hand.is_split:
            hand.surrender()
            self.balance += hand.bet // 2
            self._advance_hand()

    def _advance_hand(self) -> None:
        self.active_hand_idx += 1
        if self.active_hand_idx >= len(self.player_hands):
            # All hands done
            if all(h.state in (HandState.BUST, HandState.SURRENDER)
                   for h in self.player_hands):
                for h in self.player_hands:
                    if h.state == HandState.BUST:
                        self.stats.record(RoundOutcome.LOSE)
                    elif h.state == HandState.SURRENDER:
                        self.stats.record(RoundOutcome.SURRENDER)
                self._show_result("Перебор!", C.RED_SUIT)
            else:
                self.hide_dealer = False
                self.state = State.DEALER
                self._dealer_timer = 0.8

    def _submit_challenge(self) -> None:
        if self.current_challenge and self.trainer:
            ok, feedback = self.trainer.check(self.current_challenge, self.challenge_input)
            # Strip ANSI codes for GUI display
            import re
            clean = re.sub(r'\033\[[0-9;]*m', '', feedback)
            self.challenge_result = clean
            self.challenge_done = True

    def _show_result(self, msg: str, color: tuple) -> None:
        self.hide_dealer = False
        self.message = msg
        self.message_color = color
        self.state = State.RESULT

    def _next_round(self) -> None:
        if self.balance < self.cfg.min_bet:
            self.state = State.GAME_OVER
        else:
            self.current_bet = 0
            self.state = State.BETTING

    # ── Dealer turn logic ─────────────────────────────────────────────────

    def _run_dealer(self, dt: float) -> None:
        self._dealer_timer -= dt
        if self._dealer_timer > 0:
            return

        if self.dealer_strategy.should_hit(self.dealer_hand):
            self.dealer_hand.add(self._draw_card())
            self._dealer_timer = 0.6
        else:
            self._settle()

    def _settle(self) -> None:
        dv = self.dealer_hand.value
        d_bust = self.dealer_hand.is_bust
        results = []
        total_return = 0

        for hand in self.player_hands:
            pv = hand.value
            if hand.state == HandState.SURRENDER:
                self.stats.record(RoundOutcome.SURRENDER)
                continue
            if hand.state == HandState.BUST:
                self.stats.record(RoundOutcome.LOSE)
                continue
            if d_bust or pv > dv:
                total_return += hand.bet * 2
                self.stats.record(RoundOutcome.WIN)
                results.append("WIN")
            elif pv == dv:
                total_return += hand.bet
                self.stats.record(RoundOutcome.PUSH)
                results.append("PUSH")
            else:
                self.stats.record(RoundOutcome.LOSE)
                results.append("LOSE")

        self.balance += total_return
        net = total_return - sum(h.bet for h in self.player_hands
                                 if h.state not in (HandState.BUST, HandState.SURRENDER))
        if net > 0:
            self._show_result(f"WIN +${net}", C.GREEN_BTN)
        elif net == 0:
            self._show_result("PUSH", C.GOLD)
        else:
            self._show_result(f"LOSE -${abs(net)}", C.RED_SUIT)

    # ── Update ────────────────────────────────────────────────────────────

    def _update(self, dt: float) -> None:
        # Update animations
        active_anims = [a for a in self.anims if not a.done]
        for anim in active_anims:
            anim.elapsed += dt
            if anim.t >= 1.0:
                anim.done = True

        # In dealing state, queue next card after current animation
        if self.state == State.DEALING:
            if all(a.done for a in self.anims):
                self._deal_next()

        # Dealer turn timer
        if self.state == State.DEALER:
            self._run_dealer(dt)

        # Message timer
        if self.message_timer > 0:
            self.message_timer -= dt

    # ── Render ────────────────────────────────────────────────────────────

    def _render(self) -> None:
        self.screen.fill(C.FELT)

        if self.state == State.MENU:
            self._render_menu()
        elif self.state == State.DIFFICULTY:
            self._render_difficulty_select()
        elif self.state in (State.BETTING, State.DEALING, State.PLAYER,
                            State.CHALLENGE, State.DEALER, State.RESULT):
            self._render_table()
        elif self.state == State.GAME_OVER:
            self._render_gameover()

        pygame.display.flip()

    def _render_menu(self) -> None:
        S.draw_label(self.screen, self.fonts, "BLACKJACK 21",
                     C.WIN_W // 2, 150, C.GOLD, "title")
        S.draw_label(self.screen, self.fonts, "Pygame Edition",
                     C.WIN_W // 2, 210, C.GRAY_LIGHT, "sub")
        self.btn_menu_play.draw(self.screen, self.fonts)
        self.btn_menu_edu.draw(self.screen, self.fonts)
        self.btn_menu_quit.draw(self.screen, self.fonts)

    def _render_difficulty_select(self) -> None:
        S.draw_label(self.screen, self.fonts, "Выберите сложность",
                     C.WIN_W // 2, 180, C.GOLD, "sub")

        mode_label = "Обучение" if self.edu_mode else "Обычная игра"
        S.draw_label(self.screen, self.fonts, mode_label,
                     C.WIN_W // 2, 230, C.PURPLE_LIGHT if self.edu_mode else C.GREEN_BTN,
                     "info")

        cfgs = DIFFICULTY_PRESETS
        for lvl, btn in [
            (DifficultyLevel.EASY, self.btn_diff_easy),
            (DifficultyLevel.MEDIUM, self.btn_diff_med),
            (DifficultyLevel.HARD, self.btn_diff_hard),
        ]:
            btn.draw(self.screen, self.fonts)
            cfg = cfgs[lvl]
            desc = f"${cfg.starting_balance} | {cfg.n_decks} deck | " \
                   f"BJ {'6:5' if cfg.blackjack_payout < 1.3 else '3:2'}"
            S.draw_label(self.screen, self.fonts, desc,
                         C.WIN_W // 2, btn.rect.bottom + 14, C.GRAY_LIGHT, "info_sm")

        self.btn_diff_back.draw(self.screen, self.fonts)

    def _render_table(self) -> None:
        # Top bar
        S.draw_top_bar(
            self.screen, self.fonts,
            self.balance, self.current_bet,
            score=self.trainer.score if self.trainer else 0,
            rc=self.counter.running_count,
            tc=self.counter.true_count(self.shoe.remaining_decks) if self.shoe else 0,
            edu_mode=self.edu_mode,
        )

        # Difficulty badge
        diff_colors = {DifficultyLevel.EASY: C.GREEN_BTN,
                       DifficultyLevel.MEDIUM: C.GOLD,
                       DifficultyLevel.HARD: C.RED_BTN}
        diff_txt = self.fonts["info_sm"].render(
            self.cfg.level.label, True, diff_colors.get(self.cfg.level, C.WHITE))
        self.screen.blit(diff_txt, (C.WIN_W - diff_txt.get_width() - 20, 16))

        # Dealer cards
        if self.dealer_hand and self.dealer_hand.cards:
            dv = "?" if self.hide_dealer else str(self.dealer_hand.value)
            S.draw_label(self.screen, self.fonts, f"Дилер: {dv}",
                         C.WIN_W // 2, C.DEALER_Y - 18, C.GRAY_LIGHT, "info_sm")
            S.draw_hand(self.screen, self.dealer_hand.cards,
                        C.WIN_W // 2, C.DEALER_Y, self.fonts,
                        hide_first=self.hide_dealer)

        # Player cards
        for i, hand in enumerate(self.player_hands):
            if not hand.cards:
                continue
            n_hands = len(self.player_hands)
            offset = (i - (n_hands - 1) / 2) * 220 if n_hands > 1 else 0
            cx = int(C.WIN_W // 2 + offset)

            # Label
            label = f"Рука {i + 1}" if n_hands > 1 else "Игрок"
            status = ""
            if hand.state == HandState.BUST:
                status = " BUST"
            elif hand.is_blackjack:
                status = " BJ!"
            elif hand.state == HandState.SURRENDER:
                status = " SURR"

            is_active = (self.state == State.PLAYER and i == self.active_hand_idx)
            lbl_color = C.GOLD if is_active else C.GRAY_LIGHT
            S.draw_label(self.screen, self.fonts,
                         f"{label}: {hand.value}{status} [${hand.bet}]",
                         cx, C.PLAYER_Y - 18, lbl_color, "info_sm")
            S.draw_hand(self.screen, hand.cards, cx, C.PLAYER_Y, self.fonts)

            # Active indicator
            if is_active:
                pygame.draw.polygon(self.screen, C.GOLD,
                                    [(cx - 8, C.PLAYER_Y - 28),
                                     (cx + 8, C.PLAYER_Y - 28),
                                     (cx, C.PLAYER_Y - 22)])

        # Animated cards in flight
        for anim in self.anims:
            if not anim.done:
                px, py = anim.pos
                S.draw_card(self.screen, anim.card, int(px), int(py),
                            self.fonts, hidden=anim.hidden)

        # State-specific UI
        if self.state == State.BETTING:
            self._render_betting()
        elif self.state == State.PLAYER:
            self._render_player_ui()
        elif self.state == State.CHALLENGE:
            self._render_challenge()
        elif self.state == State.RESULT:
            self._render_result_ui()

        # Message
        if self.message and self.state == State.RESULT:
            S.draw_label(self.screen, self.fonts, self.message,
                         C.WIN_W // 2, C.PLAYER_Y + 160,
                         self.message_color, "sub")

    def _render_betting(self) -> None:
        S.draw_label(self.screen, self.fonts, "Выберите ставку",
                     C.WIN_W // 2, C.BUTTONS_Y + 10, C.WHITE, "sub")

        # Chips
        for i, denom in enumerate(C.CHIP_DENOMS):
            cx = C.WIN_W // 2 - 200 + i * 90
            cy = C.CHIPS_Y + 30
            can_afford = self.current_bet + denom <= self.balance
            S.draw_chip(self.screen, cx, cy, denom, self.fonts,
                        selected=(not can_afford))

        # Current bet display
        S.draw_label(self.screen, self.fonts,
                     f"Ставка: ${self.current_bet}",
                     C.WIN_W // 2, C.CHIPS_Y + 72, C.GOLD, "info")

        # Buttons
        self.btn_deal.enabled = self.current_bet >= self.cfg.min_bet
        self.btn_deal.draw(self.screen, self.fonts)
        self.btn_clear.visible = self.current_bet > 0
        self.btn_clear.draw(self.screen, self.fonts)

        # Min bet hint
        S.draw_label(self.screen, self.fonts,
                     f"Мин. ставка: ${self.cfg.min_bet}",
                     C.WIN_W // 2, C.CHIPS_Y + 130, C.GRAY, "info_sm")

        # Menu button
        self.btn_to_menu.draw(self.screen, self.fonts)

    def _render_player_ui(self) -> None:
        hand = self.player_hands[self.active_hand_idx]

        # Update button states
        self.btn_double.enabled = hand.can_double and self.balance >= hand.bet
        self.btn_split.enabled = (hand.can_split and self.balance >= hand.bet
                                  and len(self.player_hands) < 4)
        self.btn_surr.enabled = len(hand.cards) == 2 and not hand.is_split

        for btn in self.action_buttons:
            btn.draw(self.screen, self.fonts)

        # Edu HUD
        if self.edu_mode and self.cfg and self.cfg.show_prob_hud:
            p_bust = ProbabilityEngine.bust_probability(hand, self.shoe) * 100
            c21, _ = ProbabilityEngine.cards_to_target(hand, 21, self.shoe)
            ev_h = ProbabilityEngine.ev_hit(hand, self.dealer_hand.cards[1],
                                            self.shoe, n_sims=300)
            ev_s = ProbabilityEngine.ev_stand(hand, self.dealer_hand.cards[1],
                                              self.shoe, n_sims=300)
            S.draw_hud_panel(self.screen, self.fonts, p_bust, c21,
                             self.shoe.remaining, ev_h, ev_s,
                             show_ev=self.cfg.show_optimal_hint)

    def _render_challenge(self) -> None:
        if self.current_challenge:
            lines = self.current_challenge.question.split("\n")
            title = f"ЗАДАЧА ({self.current_challenge.difficulty.name}, " \
                    f"+{self.current_challenge.points} очков)"
            S.draw_popup(self.screen, self.fonts, title, lines,
                         self.challenge_input,
                         show_input=not self.challenge_done,
                         result_text=self.challenge_result)

    def _render_result_ui(self) -> None:
        self.btn_continue.draw(self.screen, self.fonts)
        self.btn_to_menu.draw(self.screen, self.fonts)

    def _render_gameover(self) -> None:
        S.draw_label(self.screen, self.fonts, "GAME OVER",
                     C.WIN_W // 2, 180, C.RED_SUIT, "title")

        if self.stats:
            profit = self.balance - self.stats.initial_balance
            clr = C.GREEN_BTN if profit >= 0 else C.RED_SUIT
            lines = [
                f"Раундов: {self.stats.rounds}",
                f"Побед: {self.stats.wins}  |  Поражений: {self.stats.losses}  |  Push: {self.stats.pushes}",
                f"Blackjack: {self.stats.blackjacks}  |  Win Rate: {self.stats.win_rate:.1f}%",
                f"Баланс: ${self.balance}",
            ]
            for i, line in enumerate(lines):
                S.draw_label(self.screen, self.fonts, line,
                             C.WIN_W // 2, 280 + i * 35, C.WHITE, "info")

            profit_str = f"Профит: {'+' if profit >= 0 else ''}{profit}"
            S.draw_label(self.screen, self.fonts, profit_str,
                         C.WIN_W // 2, 430, clr, "sub")

            if self.trainer and self.trainer.total_asked > 0:
                math_lines = [
                    f"Задач: {self.trainer.total_asked}  |  "
                    f"Верно: {self.trainer.total_correct} ({self.trainer.accuracy:.0f}%)",
                    f"Score: {self.trainer.score}  |  Max streak: {self.trainer.max_streak}",
                ]
                for i, line in enumerate(math_lines):
                    S.draw_label(self.screen, self.fonts, line,
                                 C.WIN_W // 2, 470 + i * 30, C.PURPLE_LIGHT, "info")

        self.btn_new_game.draw(self.screen, self.fonts)


def run_gui() -> None:
    App().run()
