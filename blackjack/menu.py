"""Main menu, difficulty selection, and theory reference."""

from __future__ import annotations

import os
import sys

from .difficulty import DifficultyLevel, DIFFICULTY_PRESETS
from .renderer import Ansi


def main_menu() -> None:
    os.system("cls" if sys.platform == "win32" else "clear")
    print(f"""
{Ansi.YELLOW}{Ansi.BOLD}    +==========================================+
    |     S  B L A C K J A C K  2 1  H       |
    |        Terminal Edition v3 / EDU         |
    +==========================================+{Ansi.RST}

  Выберите режим:

  {Ansi.GREEN}{Ansi.BOLD}1{Ansi.RST}  Обычная игра
     {Ansi.DIM}Классический блэкджек{Ansi.RST}

  {Ansi.MAGENTA}{Ansi.BOLD}2{Ansi.RST}  Обучение (теория вероятностей)
     {Ansi.DIM}Задачи + HUD вероятностей + Hi-Lo + EV{Ansi.RST}

  {Ansi.CYAN}{Ansi.BOLD}3{Ansi.RST}  Теория (справочник)
     {Ansi.DIM}Формулы и концепции без игры{Ansi.RST}

  {Ansi.DIM}q  Выход{Ansi.RST}
    """)


def select_difficulty() -> DifficultyLevel | None:
    """Submenu for difficulty selection. Returns None on cancel."""
    os.system("cls" if sys.platform == "win32" else "clear")

    presets = DIFFICULTY_PRESETS

    e = presets[DifficultyLevel.EASY]
    m = presets[DifficultyLevel.MEDIUM]
    h = presets[DifficultyLevel.HARD]

    print(f"""
{Ansi.YELLOW}{Ansi.BOLD}    === ВЫБОР СЛОЖНОСТИ ==={Ansi.RST}

  {Ansi.GREEN}{Ansi.BOLD}1  Легкий{Ansi.RST}
     {Ansi.DIM}${e.starting_balance} | {e.n_decks} колоды | Дилер soft 17: Stand
     BJ 3:2 | Ставка от ${e.min_bet}{Ansi.RST}
     {Ansi.GREEN}Обучение: HUD + подсказки, задачи Easy/Medium, толеранс x2{Ansi.RST}

  {Ansi.YELLOW}{Ansi.BOLD}2  Средний{Ansi.RST}
     {Ansi.DIM}${m.starting_balance} | {m.n_decks} колод | Дилер soft 17: Stand
     BJ 3:2 | Ставка от ${m.min_bet}{Ansi.RST}
     {Ansi.YELLOW}Обучение: HUD без подсказок, все задачи, толеранс x1{Ansi.RST}

  {Ansi.RED}{Ansi.BOLD}3  Сложный{Ansi.RST}
     {Ansi.DIM}${h.starting_balance} | {h.n_decks} колод | Дилер soft 17: Hit
     BJ 6:5 | Ставка от ${h.min_bet}{Ansi.RST}
     {Ansi.RED}Обучение: без HUD, задачи Medium/Hard, толеранс x0.5{Ansi.RST}

  {Ansi.DIM}b  Назад{Ansi.RST}
    """)

    while True:
        raw = input(f"  {Ansi.BOLD}Выбор: {Ansi.RST}").strip().lower()
        if raw in ("1", "л"):
            return DifficultyLevel.EASY
        if raw in ("2", "с"):
            return DifficultyLevel.MEDIUM
        if raw in ("3", "т"):
            return DifficultyLevel.HARD
        if raw in ("b", "back", "н", "назад"):
            return None


def show_theory() -> None:
    os.system("cls" if sys.platform == "win32" else "clear")
    print(f"""
{Ansi.YELLOW}{Ansi.BOLD}  === СПРАВОЧНИК: МАТЕМАТИКА БЛЭКДЖЕКА ==={Ansi.RST}

  {Ansi.CYAN}{Ansi.BOLD}1. Формула Лапласа (классическая вероятность){Ansi.RST}
  {Ansi.DIM}  P(A) = m / n
  m = число благоприятных исходов, n = общее число исходов.
  Пример: P(bust при 16) = карт с 6+ очками / все оставшиеся.{Ansi.RST}

  {Ansi.CYAN}{Ansi.BOLD}2. Условная вероятность (Формула Байеса){Ansi.RST}
  {Ansi.DIM}  P(A|B) = P(B|A) * P(A) / P(B)
  Пример: У дилера туз. P(BJ) = кол-во 10-очковых / оставшиеся.
  Это прямое условие: мы ЗНАЕМ первую карту, считаем вторую.{Ansi.RST}

  {Ansi.CYAN}{Ansi.BOLD}3. Математическое ожидание (EV){Ansi.RST}
  {Ansi.DIM}  EV = SUM(p_i * x_i)
  p_i = вероятность исхода, x_i = выплата.
  EV(Stand) = P(win)*1 + P(push)*0 + P(lose)*(-1)
  EV(Hit)   = SUM по всем картам: P(карта) * EV(новая рука)
  Действие с наибольшим EV — оптимальный ход.{Ansi.RST}

  {Ansi.CYAN}{Ansi.BOLD}4. Критерий Келли (оптимальная ставка){Ansi.RST}
  {Ansi.DIM}  f* = (bp - q) / b
  b = коэффициент выплаты, p = P(win), q = P(lose).
  Максимизирует долгосрочный рост капитала.{Ansi.RST}

  {Ansi.CYAN}{Ansi.BOLD}5. Hi-Lo Card Counting{Ansi.RST}
  {Ansi.DIM}  2-6: +1 | 7-9: 0 | 10-A: -1
  Running Count (RC) = сумма по вышедшим картам.
  True Count (TC) = RC / оставшихся колод.
  TC > +2: преимущество игрока (больше 10-ок и тузов в колоде).
  TC < -2: преимущество казино.{Ansi.RST}

  {Ansi.CYAN}{Ansi.BOLD}6. Дисперсия и Закон Больших Чисел{Ansi.RST}
  {Ansi.DIM}  Краткосрочно: высокая дисперсия, результаты случайны.
  Долгосрочно: результат стремится к EV.
  House edge в BJ: ~0.5% при базовой стратегии.
  С card counting: edge может стать +0.5-1.5% в пользу игрока.{Ansi.RST}

  {Ansi.CYAN}{Ansi.BOLD}7. P(dealer bust) по открытой карте{Ansi.RST}
  {Ansi.DIM}  2: ~35%  |  3: ~37%  |  4: ~40%
  5: ~42%  |  6: ~42%  |  7: ~26%
  8: ~24%  |  9: ~23%  | 10: ~23%  |  A: ~17%
  Запомни: 4-5-6 = "bust cards" дилера.{Ansi.RST}

  {Ansi.CYAN}{Ansi.BOLD}8. Правило дополнения{Ansi.RST}
  {Ansi.DIM}  P(Ā) = 1 − P(A)
  Пример: P(НЕ bust) = 1 − P(bust).
  Удобно когда проще считать «неудачу», чем «удачу».{Ansi.RST}

  {Ansi.CYAN}{Ansi.BOLD}9. Правило сложения (P(A∪B)){Ansi.RST}
  {Ansi.DIM}  P(A ∪ B) = P(A) + P(B) − P(A ∩ B)
  Для несовместных событий: P(A ∪ B) = P(A) + P(B).
  Пример: P(красная ИЛИ картинка) — вычитаем пересечение.{Ansi.RST}

  {Ansi.CYAN}{Ansi.BOLD}10. Правило умножения (зависимые события){Ansi.RST}
  {Ansi.DIM}  P(A ∩ B) = P(A) × P(B|A)
  Карты без возврата — зависимые события.
  Пример: P(два туза подряд) = 4/52 × 3/51 ≈ 0.45%.{Ansi.RST}

  {Ansi.CYAN}{Ansi.BOLD}11. Комбинаторика (правило умножения){Ansi.RST}
  {Ansi.DIM}  Кол-во комбинаций = m × n
  Пример: BJ = Туз + 10-value. Из 4 тузов и 16 десяток: 4×16 = 64 комб.
  C(n,k) = n! / (k!(n−k)!) — сочетания без повторений.{Ansi.RST}

  {Ansi.CYAN}{Ansi.BOLD}12. Дисперсия и стандартное отклонение{Ansi.RST}
  {Ansi.DIM}  D(X) = Σ pᵢ(xᵢ − μ)²     σ = √D(X)
  σ показывает типичный разброс от среднего.
  В BJ: высокая σ = больше колебаний баланса.{Ansi.RST}

  {Ansi.CYAN}{Ansi.BOLD}13. Формула Бернулли (биномиальное распределение){Ansi.RST}
  {Ansi.DIM}  P(X = k) = C(n,k) × p^k × (1−p)^(n−k)
  n = число испытаний, k = число успехов, p = P(успех).
  Пример: P(bust 2 раза из 5) при P(bust) = 40%:
  C(5,2) × 0.4² × 0.6³ = 10 × 0.16 × 0.216 = 34.6%.{Ansi.RST}

  {Ansi.CYAN}{Ansi.BOLD}14. Формула Байеса (апостериорная вероятность){Ansi.RST}
  {Ansi.DIM}  P(A|B) = P(B|A) × P(A) / P(B)
  Обновляем вероятность гипотезы при новых данных.
  Пример: карта красная — какова P(это туз)?
  P(Ace|Red) = P(Red|Ace) × P(Ace) / P(Red).{Ansi.RST}

  {Ansi.CYAN}{Ansi.BOLD}15. Распределение Пуассона (редкие события){Ansi.RST}
  {Ansi.DIM}  P(X = k) = (λ^k × e^(−λ)) / k!
  λ = среднее число событий (n × p).
  Пример: P(BJ) ≈ 4.8%. За 20 рук λ = 0.96.
  P(ровно 2 BJ) = (0.96² × e^(−0.96)) / 2! ≈ 17.6%.{Ansi.RST}

  {Ansi.CYAN}{Ansi.BOLD}16. Влияние правил на house edge{Ansi.RST}
  {Ansi.DIM}  BJ 3:2 vs 6:5:      +1.39% edge казино при 6:5
  Dealer hits soft 17: +0.22% edge казино
  8 колод vs 4 колоды: +0.06% edge казино
  Поэтому Сложный режим значительно труднее!{Ansi.RST}
    """)
    input(f"  {Ansi.DIM}Enter для возврата в меню...{Ansi.RST}")
