# AI Ping Pong

Детерминированная симуляция пинг-понга на Python и Pygame, в которой боты развиваются с помощью генетического алгоритма.

Проект включает режимы Human vs Bot и Bot vs Bot, headless-обучение и оценку матчей, воспроизводимую историю поколений, сохранённого лучшего бота, числовые доказательства улучшения и визуальный replay чемпионов поколений.

· [English version](README.md)

## 📋 Оглавление

- [🚀 Быстрый запуск](#-быстрый-запуск)
- [📝 О проекте](#-о-проекте)
- [✨ Возможности](#-возможности)
- [🏗️ Архитектура](#️-архитектура)
- [🧬 Геном бота](#-геном-бота)
- [🧠 Генетический алгоритм](#-генетический-алгоритм)
- [📊 Fitness и оценка](#-fitness-и-оценка)
- [🕹️ Режимы игры и управление](#️-режимы-игры-и-управление)
- [🧰 Стек технологий](#-стек-технологий)
- [🧪 Тесты](#-тесты)
- [📁 Структура проекта](#-структура-проекта)
- [⚠️ Примечания](#️-примечания)
- [🧑‍💻 Автор](#-автор)

## 🚀 Быстрый запуск

### Требования

- Python `3.13` или другая версия, совместимая с Pygame `2.6.1`
- рекомендуется использовать virtual environment

### Клонирование и установка

```powershell
git clone https://01.tomorrow-school.ai/git/nyestaye/ai-ping-pong
cd ai-ping-pong

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Запуск игры

```powershell
python -m game.main
```

Также поддерживается прямой запуск файла:

```powershell
python game/main.py
```

## 📝 О проекте

AI Ping Pong — учебный проект, демонстрирующий, как генетический алгоритм может оптимизировать поведение бота в простой детерминированной игровой среде.

Визуальный frontend отделён от симуляции матча. Поэтому одна и та же симуляция может работать:

- интерактивно через Pygame;
- без окна во время обучения;
- без окна во время детерминированной оценки;
- без создания display в автоматических тестах.

Обучение выполняется отдельно от GUI. Frontend загружает зафиксированные артефакты:

```text
models/best_bot.json
logs/generations.csv
```

Human vs Bot использует сохранённый глобально лучший геном. Bot vs Bot воспроизводит чемпиона выбранного поколения против поколения `0`.

## ✨ Возможности

### Игровой процесс

- режим Human vs Bot;
- режим Bot vs Bot;
- управление ракеткой мышью и клавиатурой;
- переключение поколений стрелками влево и вправо;
- подсчёт очков и обработка столкновений мяча с ракетками;
- адаптивные физические substeps, предотвращающие пролёт быстрого мяча сквозь ракетку;
- детерминированные headless-матчи.

### Эволюция ботов

- случайная начальная популяция;
- параметризованный геном бота;
- tournament selection;
- per-gene blend crossover;
- per-gene Gaussian mutation;
- direct elitism;
- настраиваемые размеры популяции, число поколений, mutation, crossover, seeds и ограничения матчей;
- детерминированная эволюция через изолированный random generator;
- сохранение лучшего бота в JSON;
- canonical-история поколений в CSV.

### Доказательства и воспроизводимость

- лучший, средний и худший fitness каждого поколения;
- детерминированная оценка на held-out seeds;
- прямое сравнение финального чемпиона с поколением `0`;
- зафиксированный JSON-отчёт;
- детерминированный SVG-график fitness;
- воспроизводимые screenshots frontend;
- документированные canonical training и evaluation seeds.

## 🏗️ Архитектура

```text
                    +----------------------+
                    |   Pygame frontend    |
                    |     game/main.py     |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |  MatchSimulation     |
                    | game/simulation.py   |
                    +----------+-----------+
                               |
              +----------------+----------------+
              |                                 |
              v                                 v
    +-------------------+             +-------------------+
    | HumanController   |             | BotController     |
    | keyboard / mouse  |             | genome-driven     |
    +-------------------+             +-------------------+

    +-----------------------------------------------------+
    | Headless training and evaluation                    |
    | ga/genetic_algorithm.py -> ga/fitness.py            |
    |                           -> game/match_runner.py    |
    +-----------------------------------------------------+
```

Основное состояние игры не зависит от display. Обучение и оценка используют ту же симуляцию и ту же логику контроллеров, что и визуальный frontend.

## 🧬 Геном бота

Каждый бот представлен тремя параметрами:

| Параметр | Значение |
|---|---|
| `paddle_speed` | максимальная скорость перемещения ракетки в пикселях в секунду |
| `reaction_time` | задержка между обновлениями цели |
| `movement_threshold` | мёртвая зона вокруг целевой позиции |

Canonical promoted genome:

```text
paddle_speed       = 420.0
reaction_time      = 0.039498692275418835
movement_threshold = 29.790193846648812
```

Контроллер обновляет целевую позицию по координате мяча с учётом `reaction_time`, затем движется к ней с параметрами `paddle_speed` и `movement_threshold`.

## 🧠 Генетический алгоритм

Запуск детерминированного headless-обучения:

```powershell
python -m ga.genetic_algorithm
```

Пример небольшого пользовательского запуска:

```powershell
python -m ga.genetic_algorithm `
    --population-size 8 `
    --generations 3
```

Также поддерживается прямой запуск:

```powershell
python ga/genetic_algorithm.py --population-size 8 --generations 3
```

### Параметры CLI по умолчанию

- Evolution seed: `20260728`
- Population size: `16`
- Evaluated generations: `8`
- Elite count: `2`
- Tournament size: `3`
- Crossover rate: `0.8`
- Mutation rate: `0.2`
- Mutation sigma: `0.10`
- Match seeds: `20260728,20260729`
- Match limit: `1800` шагов или `3` очка
- Baseline opponent: `260,0,8`
- Score weight: `100.0`
- Return weight: `1.0`

### Canonical training run

Зафиксированные model и history были получены со следующими параметрами:

- Evolution seed: `20260730`
- Population size: `32`
- Evaluated generations: `24`
- Elite count: `4`
- Tournament size: `4`
- Crossover rate: `0.8`
- Mutation rate: `0.2`
- Mutation sigma: `0.1`
- Training seeds: `2000,2001,2002,2003,2004,2005,2006,2007`
- Match limit: `3600` шагов или `5` очков
- Baseline opponent: `260,0,8`
- Score weight: `100.0`
- Return weight: `1.0`

Команда обучения записывает:

```text
logs/generations.csv
models/best_bot.json
```

Пользовательские пути:

```powershell
python -m ga.genetic_algorithm `
    --log-path custom/generations.csv `
    --model-path custom/best_bot.json
```

## 📊 Fitness и оценка

Fitness кандидата за один матч рассчитывается так:

```text
score_weight * (candidate_score - opponent_score)
    + return_weight * candidate_returns
```

На каждом seed кандидат играет с обеих сторон. Итоговый fitness — арифметическое среднее по всем матчам.

Canonical CSV хранит:

```text
generation
best_fitness
mean_fitness
worst_fitness
paddle_speed
reaction_time
movement_threshold
```

### Canonical result

| Метрика | Поколение 0 | Поколение 23 | Результат |
|---|---:|---:|---:|
| Средний training fitness | -144.814453125 | 198.83984375 | +343.654296875 |
| Held-out fitness | 155.05 | 182.225 | +27.175 |
| Финальный против начального | — | 13 побед / 27 ничьих / 0 поражений | 13:0 по очкам |

Запуск locked deterministic evaluation:

```powershell
python -m ga.evaluation
```

Оценка использует held-out seeds `1000..1019`, которые не участвовали в обучении. Каждый геном играет один раз слева и один раз справа на каждом seed.

Артефакты:

- [Полный детерминированный отчёт](reports/evaluation.json)
- [График прогресса fitness](docs/fitness_progress.svg)

![Training and held-out fitness по поколениям](docs/fitness_progress.svg)

Visual replay полезен для просмотра, но формальным доказательством улучшения является числовой evaluation report.

## 🕹️ Режимы игры и управление

### Human vs Bot

Игрок управляет левой ракеткой. Правая использует сохранённый глобально лучший геном из:

```text
models/best_bot.json
```

Управление:

- мышь внутри корта;
- `W` / `S`;
- стрелки вверх / вниз;
- `Esc` возвращает в меню.

### Bot vs Bot

Чемпион выбранного поколения играет слева против поколения `0` справа.

Управление:

- стрелки влево / вправо переключают поколение;
- `Esc` возвращает в меню.

Screenshots:

![Главное меню](docs/screenshots/menu.png)

![Replay поколения 0](docs/screenshots/generation-0.png)

![Replay финального поколения](docs/screenshots/generation-final.png)

Пересоздание screenshots:

```powershell
python -m tools.capture_screenshots
```

## 🧰 Стек технологий

| Слой | Технология |
|---|---|
| Язык | Python |
| Визуальный frontend | Pygame `2.6.1` |
| Симуляция | собственная детерминированная 2D-физика |
| Эволюция | собственный генетический алгоритм |
| Артефакты | JSON, CSV, SVG, PNG |
| Тесты | Python `unittest` |

Внешний dataset не используется. Обучающие данные создаются детерминированными simulated matches.

## 🧪 Тесты

Запуск всех тестов:

```powershell
python -m unittest discover -s tests -v
```

Дополнительные проверки:

```powershell
python -m compileall game ga tools tests
python -m pip check
```

Набор тестов покрывает:

- симуляцию и столкновения;
- регрессии tunneling для больших шагов и перемещений менее 30 px;
- bot и human controllers;
- детерминированные матчи;
- валидацию генома;
- selection, crossover и mutation;
- агрегацию fitness;
- эволюцию генетического алгоритма;
- CSV- и JSON-артефакты;
- CLI paths и обработку ошибок;
- deterministic evaluation;
- генерацию SVG;
- capture screenshots;
- интеграцию frontend;
- edge cases и воспроизводимость.

## 📁 Структура проекта

```text
ai-ping-pong/
├── docs/
│   ├── fitness_progress.svg
│   └── screenshots/
├── game/
│   ├── ball.py
│   ├── controllers.py
│   ├── main.py
│   ├── match_runner.py
│   ├── paddle.py
│   ├── simulation.py
│   └── utils.py
├── ga/
│   ├── artifacts.py
│   ├── crossover.py
│   ├── evaluation.py
│   ├── fitness.py
│   ├── genetic_algorithm.py
│   ├── genome.py
│   ├── mutation.py
│   └── selection.py
├── logs/
│   └── generations.csv
├── models/
│   └── best_bot.json
├── reports/
│   └── evaluation.json
├── tests/
├── tools/
│   └── capture_screenshots.py
├── requirements.txt
├── README.md
└── README_RU.md
```

## ⚠️ Примечания

- Обучение отделено от визуальной игры и не выполняется в фоне во время матча.
- Human vs Bot всегда загружает зафиксированного лучшего бота, если явно не передан другой model path.
- Bot vs Bot воспроизводит чемпионов поколений и не переобучает их.
- `FITNESS` в HUD — исторический training fitness чемпиона выбранного поколения, а не счёт текущего матча.
- Нумерация поколений начинается с `0`, поэтому история из 24 поколений содержит поколения `0..23`.
- Baseline genome `260,0,8` используется при обучении и evaluation; это не стандартный соперник Human vs Bot.
- Зафиксированная JSON-модель является реализованным bonus сохранения лучшего бота.

## 🧑‍💻 Автор
Nazar Yestayev (@nyestaye)
