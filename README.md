# BLACKJACK 21

Образовательная игра в блэкджек: 24 задачи по теории вероятностей,
базовая стратегия, Hi-Lo Index Plays, headless-бэктестер.

| Главное меню | Задача | Игра |
|:---:|:---:|:---:|
| ![Меню](1.png) | ![Задача](2.png) | ![Игра](3.png) |

## Возможности

- Hit, Stand, Double, Split (до 4 рук), Surrender, Insurance.
- 24 типа задач (Лаплас, Байес, Бернулли, Пуассон, E(X), D(X), Келли,
  Hi-Lo, правила сложения и умножения) с weak-topic adaptive выбором.
- Probability HUD: P(bust), аналитический P(dealer bust), рекурсивный
  EV(Hit) и EV(Stand) с кэшем по shoe-сигнатуре.
- Basic strategy 6-deck S17 DAS, Illustrious 18 + Fab 4, TC-bet ramp 1-12.
- Profile в `~/.blackjack_edu/profile.json`: lifetime stats и per-topic
  accuracy между сессиями.
- Headless backtester (PnL, ROI, sigma, P(bankruptcy)).
- Два UI: Terminal (ANSI) и Pygame.
- 146 тестов, GitHub Actions на Python 3.11/3.12.

## Уровни сложности

| Параметр | Лёгкий | Средний | Сложный |
|---|---|---|---|
| Баланс | $2000 | $1000 | $500 |
| Колоды | 4 | 6 | 8 |
| Blackjack | 3:2 | 3:2 | 6:5 |
| Dealer soft 17 | Stand | Stand | Hit |
| Мин. ставка | $10 | $15 | $25 |
| HUD | Да + подсказки | Да | Нет |
| Задачи | Easy/Medium | Все | Medium/Hard |

## Установка и запуск

Требуется Python 3.11+. Pygame ставится автоматически.

```bash
pip install -e .              # или ".[dev]" для pytest + ruff
python main.py                # интерактивный выбор Terminal/GUI
python main.py terminal | gui
blackjack.bat                 # Windows-меню
```

**Управление.** Terminal: ставка цифрой, `q` выход; `H` Hit, `S` Stand,
`D` Double, `P` Split, `R` Surrender. GUI: те же клавиши, `ESC` в меню,
`Enter`/`Space` продолжить.

## Backtester

```bash
python -m blackjack.backtest --hands 10000 --seed 42
python -m blackjack.backtest --hands 50000 --counting hi-lo
```

Отчёт: PnL, ROI per unit, win rate, sigma per hand, Sharpe-аналог,
hand at which player went bankrupt.

## Тесты

```bash
pytest                        # 146 тестов
ruff check blackjack tests
```

## Структура

```
blackjack/
  models.py             Card, Rank, Suit, Hand, Shoe (seeded RNG)
  actions.py            Action, RoundOutcome
  difficulty.py         DifficultyLevel + presets
  game.py               BlackjackGame (раунд-оркестратор)
  dealer.py             StandardDealer (soft-17 toggle)
  counter.py            CardCounter (Hi-Lo)
  probability.py        аналитический P(bust), рекурсивный EV(Hit)
  basic_strategy.py     6-deck S17 DAS chart
  strategy_deviations.py Illustrious 18 + Fab 4 + bet ramp
  trainer.py            24 задачи, weak-topic adaptive
  persistence.py        Profile JSON store
  backtest.py           headless CLI
  renderer.py           Terminal (ANSI)
  input_handler.py      Terminal input
  stats.py              Stats
  menu.py               меню + справочник
  gui/                  Pygame
tests/                  146 тестов
```
