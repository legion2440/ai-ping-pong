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
- [🌐 API поколений](#-api-поколений)
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

#### Windows (Git Bash)

```bash
git clone https://01.tomorrow-school.ai/git/nyestaye/ai-ping-pong
cd ai-ping-pong

python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
```

#### macOS / Linux

```bash
git clone https://01.tomorrow-school.ai/git/nyestaye/ai-ping-pong
cd ai-ping-pong

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Все команды ниже используют синтаксис Bash и работают в Git Bash на Windows и в стандартном терминале macOS или Linux после активации virtual environment.

### Запуск игры

```bash
python -m game.main
```

Также поддерживается прямой запуск файла:

```bash
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

Human vs Bot использует сохранённый глобально лучший геном. Bot vs Bot позволяет независимо выбрать любых двух чемпионов поколений.

## ✨ Возможности

### Игровой процесс

- режим Human vs Bot;
- режим Bot vs Bot;
- управление ракеткой мышью и клавиатурой;
- независимый выбор левого и правого поколений мышью или клавиатурой;
- ручная настройка скорости мяча и размера ракеток;
- опциональное автоматическое усложнение каждые 20 секунд;
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

### Реализованные бонусы

- read-only API поколений и fitness;
- ручная и автоматическая gradual difficulty;
- сохранение лучшего бота в JSON.

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

    +-----------------------------------------------------+
    | Read-only generation API                            |
    | api/app.py -> ga/artifacts.py -> generations.csv    |
    +-----------------------------------------------------+
```

Основное состояние игры не зависит от display. Обучение и оценка используют ту же симуляцию и ту же логику контроллеров, что и визуальный frontend. Runtime difficulty принадлежит только визуальному `Game` через `game/difficulty.py`; `MatchSimulation` ничего не знает об элементах UI и автоматическом таймере. API также не зависит от Pygame и только читает canonical-историю поколений через существующий artifact loader.

## 🧬 Геном бота

Каждый бот представлен тремя параметрами:

| Параметр             | Значение                                                       |
|----------------------|----------------------------------------------------------------|
| `paddle_speed`       | максимальная скорость перемещения ракетки в пикселях в секунду |
| `reaction_time`      | задержка между обновлениями цели                               |
| `movement_threshold` | мёртвая зона вокруг целевой позиции                            |

Canonical promoted genome:

```text
paddle_speed       = 420.0
reaction_time      = 0.039498692275418835
movement_threshold = 29.790193846648812
```

Контроллер обновляет целевую позицию по координате мяча с учётом `reaction_time`, затем движется к ней с параметрами `paddle_speed` и `movement_threshold`.

## 🧠 Генетический алгоритм

Blend crossover комбинирует значения внутри диапазона родительских геномов, а mutation обеспечивает исследование за пределами текущего диапазона популяции.

Запуск детерминированного headless-обучения:

```bash
python -m ga.genetic_algorithm
```

Пример небольшого пользовательского запуска:

```bash
python -m ga.genetic_algorithm \
    --population-size 8 \
    --generations 3
```

Также поддерживается прямой запуск:

```bash
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

CLI defaults предназначены для более короткого демонстрационного запуска. Команда ниже воспроизводит canonical configuration, использованную для зафиксированных артефактов.

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

```bash
python -m ga.genetic_algorithm \
    --seed 20260730 \
    --population-size 32 \
    --generations 24 \
    --elite-count 4 \
    --tournament-size 4 \
    --crossover-rate 0.8 \
    --mutation-rate 0.2 \
    --mutation-sigma 0.1 \
    --match-seeds 2000,2001,2002,2003,2004,2005,2006,2007 \
    --match-dt 0.016666666666666666 \
    --match-max-steps 3600 \
    --match-score-limit 5 \
    --opponent 260,0,8 \
    --score-weight 100 \
    --return-weight 1
```

Команда выше воспроизводит canonical configuration. Она приведена для воспроизводимости; существующие зафиксированные артефакты в рамках этого изменения не пересоздаются.

Команда обучения записывает:

```text
logs/generations.csv
models/best_bot.json
```

Пользовательские пути:

```bash
python -m ga.genetic_algorithm \
    --log-path custom/generations.csv \
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

| Метрика                     | Поколение 0    | Поколение 23                       | Результат      |
|-----------------------------|---------------:|-----------------------------------:|---------------:|
| Средний training fitness    | -144.814453125 | 198.83984375                       | +343.654296875 |
| Held-out fitness            | 155.05         | 182.225                            | +27.175        |
| Финальный против начального | —              | 13 побед / 27 ничьих / 0 поражений | 13:0 по очкам  |

Средний fitness популяции может колебаться между поколениями, поскольку crossover и mutation добавляют новых кандидатов. Зафиксированное улучшение — это общее изменение от поколения 0 до поколения 23.

Запуск locked deterministic evaluation:

```bash
python -m ga.evaluation
```

Оценка использует held-out seeds `1000..1019`, которые не участвовали в обучении. Каждый геном играет один раз слева и один раз справа на каждом seed.

Артефакты:

- [Полный детерминированный отчёт](reports/evaluation.json)
- [График прогресса fitness](docs/fitness_progress.svg)

График fitness создаётся как детерминированный SVG без внешней библиотеки построения графиков.

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
- кликабельные controls runtime difficulty;
- `Esc` возвращает в меню.

### Bot vs Bot

Левая и правая стороны независимо загружают любого чемпиона из `logs/generations.csv`. Обе начинают с поколения `0`.

Управление:

- `A` / `D` переключают LEFT GEN;
- стрелки влево / вправо переключают RIGHT GEN;
- кнопки со стрелками рядом с каждым ботом выполняют те же действия;
- `Esc` возвращает в меню.

### Runtime difficulty

Runtime difficulty доступна в обоих режимах через кликабельную нижнюю панель и keyboard shortcuts:

- `-` / `+` или numpad `-` / `+` изменяют скорость мяча;
- `[` / `]` изменяют высоту обеих ракеток;
- `T` включает и выключает автоматическое усложнение.

| Настройка      | Минимум | По умолчанию | Максимум | Шаг    |
|----------------|--------:|-------------:|---------:|-------:|
| Скорость мяча  | `x0.50` | `x1.00`      | `x2.00`  | `0.10` |
| Высота ракетки | `50 px` | `90 px`      | `120 px` | `5 px` |

AUTO по умолчанию выключен и включается кликабельной кнопкой AUTO или клавишей `T`. После включения каждые 20 секунд активного матча он добавляет `0.10` к скорости мяча и убирает `5 px` от высоты ракеток независимо до указанных границ. Выключение AUTO ставит таймер на паузу, а повторное включение продолжает с сохранённого остатка. Ручные изменения не перезапускают таймер.

Изменение difficulty сохраняет счёт, текущий rally, позиции объектов и controllers. При изменении высоты сохраняется центр каждой ракетки, после чего применяется clamp к границам корта. Гол сохраняет difficulty, а новый мяч использует текущий speed multiplier. Фактическая смена поколения или новый вход в режим сбрасывает difficulty до скорости мяча `x1.00`, высоты ракеток `90 px` и AUTO OFF; нажатие неактивной граничной кнопки поколения не меняет ничего.

Значения training fitness были получены в canonical-среде со стандартными параметрами: скорость мяча `x1.00` и высота ракетки `90 px`, без runtime-изменения сложности. `TRAIN FITNESS` ранжирует чемпионов поколений только для этих условий обучения.

Ручное или автоматическое изменение сложности создаёт отдельную stress-test среду, которая не использовалась при обучении. Поскольку параметры генома, включая `movement_threshold`, заданы в абсолютных пикселях, изменение скорости мяча или высоты ракеток может изменить относительную эффективность поколений. Поэтому более раннее поколение может победить более позднее при пользовательских настройках, и это не противоречит зафиксированному прогрессу обучения.

Для сопоставимого сравнения поколений следует сохранить настройки приложения по умолчанию: скорость мяча `x1.00`, высоту ракетки `90 px` и AUTO OFF.

Screenshots:

![Главное меню](docs/screenshots/menu.png)

![Replay поколения 0](docs/screenshots/generation-0.png)

![Replay финального поколения](docs/screenshots/generation-final.png)

Пересоздание screenshots:

```bash
python -m tools.capture_screenshots
```

## 🌐 API поколений

Сервис FastAPI предоставляет read-only доступ к текущей истории поколений и fitness. Он не запускает генетический алгоритм, не меняет игру и не записывает данные в `logs/generations.csv`. Выбранный CSV загружается заново при каждом запросе данных, поэтому завершённый training run становится доступен без перезапуска сервера.

Запуск локального сервера:

```bash
python -m api.main
```

Также поддерживается прямой запуск файла:

```bash
python api/main.py
```

Swagger UI доступен по адресу [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

| Метод | Endpoint                    | Ответ                                                       |
|-------|-----------------------------|-------------------------------------------------------------|
| `GET` | `/`                         | название API, read-only status, источник и URL документации |
| `GET` | `/health`                   | состояние сервиса без чтения CSV                            |
| `GET` | `/generations`              | все поколения вместе с геномами                             |
| `GET` | `/generations/{generation}` | одно поколение                                              |
| `GET` | `/fitness`                  | история fitness без геномов                                 |

Примеры запросов:

```bash
curl -s http://127.0.0.1:8000/generations
curl -s http://127.0.0.1:8000/generations/23
curl -s http://127.0.0.1:8000/fitness
```

Использование другого generation log:

```bash
python -m api.main \
    --generations-path custom/generations.csv
```

Без этого аргумента API использует canonical `logs/generations.csv` от корня проекта. Явно переданный относительный путь разрешается от invocation working directory; абсолютный путь используется без изменений. По умолчанию сервер слушает только `127.0.0.1` на порту `8000`.

## 🧰 Стек технологий

| Слой                | Технология                              |
|---------------------|-----------------------------------------|
| Язык                | Python                                  |
| Визуальный frontend | Pygame `2.6.1`                          |
| Read-only API       | FastAPI `0.139.2`, Uvicorn `0.51.0`     |
| Симуляция           | собственная детерминированная 2D-физика |
| Эволюция            | собственный генетический алгоритм       |
| Артефакты           | JSON, CSV, SVG, PNG                     |
| Тесты               | Python `unittest`                       |

Внешний dataset не используется. Обучающие данные создаются детерминированными simulated matches.

## 🧪 Тесты

Запуск всех тестов:

```bash
python -m unittest discover -s tests -v
```

Дополнительные проверки:

```bash
python -m compileall api game ga tools tests
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
- runtime difficulty и независимое управление поколениями;
- read-only API endpoints, reload behavior, ошибки, paths и CLI;
- edge cases и воспроизводимость.

## 📁 Структура проекта

```text
ai-ping-pong/
├── api/
│   ├── app.py
│   └── main.py
├── docs/
│   ├── fitness_progress.svg
│   └── screenshots/
├── game/
│   ├── ball.py
│   ├── controllers.py
│   ├── difficulty.py
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
- `TRAIN FITNESS` в HUD — исторический training fitness чемпиона выбранного поколения, а не счёт текущего матча.
- Нумерация поколений начинается с `0`, поэтому история из 24 поколений содержит поколения `0..23`.
- Ручная и автоматическая gradual difficulty реализованы как бонусы визуальной игры и не меняют canonical training или evaluation.
- Baseline genome `260,0,8` используется при обучении и evaluation; это не стандартный соперник Human vs Bot.
- Зафиксированная JSON-модель является реализованным bonus сохранения лучшего бота.
- API поколений и fitness является реализованным read-only bonus и никогда не записывает training artifacts.

## 🧑‍💻 Автор
Nazar Yestayev (@nyestaye)
