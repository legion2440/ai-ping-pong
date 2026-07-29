# AI Ping Pong

A deterministic ping-pong simulation in Python and Pygame where bots evolve through a genetic algorithm.

The project includes Human vs Bot and Bot vs Bot modes, headless training and match evaluation, reproducible generation history, a saved best bot, deterministic evidence, and generation-by-generation visual replay.

· [Русская версия](README_RU.md)

## 📋 TOC

- [🚀 Quick start](#-quick-start)
- [📝 About](#-about)
- [✨ Features](#-features)
- [🏗️ Architecture](#️-architecture)
- [🧬 Bot genome](#-bot-genome)
- [🧠 Genetic algorithm](#-genetic-algorithm)
- [📊 Fitness and evaluation](#-fitness-and-evaluation)
- [🕹️ Game modes and controls](#️-game-modes-and-controls)
- [🧰 Technology stack](#-technology-stack)
- [🧪 Tests](#-tests)
- [📁 Project structure](#-project-structure)
- [⚠️ Notes](#️-notes)
- [🧑‍💻 Author](#-author)

## 🚀 Quick start

### Prerequisites

- Python `3.13` or another version compatible with Pygame `2.6.1`
- a virtual environment is recommended

### Clone and install

```powershell
git clone https://01.tomorrow-school.ai/git/nyestaye/ai-ping-pong
cd ai-ping-pong

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Run the game

```powershell
python -m game.main
```

Direct script execution is also supported:

```powershell
python game/main.py
```

## 📝 About

AI Ping Pong is an educational project that demonstrates how a genetic algorithm can optimize bot behavior in a simple deterministic game environment.

The visual frontend is separated from the match simulation. The same simulation can therefore run:

- interactively through Pygame;
- headlessly during training;
- headlessly during deterministic evaluation;
- without opening a display during automated tests.

Training is performed separately from the GUI. The frontend loads committed artifacts:

```text
models/best_bot.json
logs/generations.csv
```

Human vs Bot uses the saved global best genome. Bot vs Bot replays each generation champion against generation `0`.

## ✨ Features

### Gameplay

- Human vs Bot mode;
- Bot vs Bot mode;
- mouse and keyboard control for the human paddle;
- generation switching with left and right arrow keys;
- score tracking and paddle/ball collision handling;
- adaptive physics substeps that prevent fast balls from tunneling through paddles;
- deterministic headless matches.

### Bot evolution

- random initial population;
- parameterized bot genome;
- tournament selection;
- per-gene blend crossover;
- per-gene Gaussian mutation;
- direct elitism;
- configurable population, generation count, mutation, crossover, seeds, and match limits;
- deterministic evolution through an isolated random generator;
- saved best bot in JSON;
- canonical generation history in CSV.

### Evidence and reproducibility

- best, mean, and worst fitness for every generation;
- held-out deterministic evaluation;
- final champion compared directly with generation `0`;
- committed JSON evaluation report;
- deterministic SVG fitness chart;
- reproducible frontend screenshots;
- canonical training and evaluation seeds documented below.

## 🏗️ Architecture

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

The core game state is independent from the display. Training and evaluation use the same simulation and controller behavior as the visual frontend.

## 🧬 Bot genome

Each bot is represented by three parameters:

| Parameter | Meaning |
|---|---|
| `paddle_speed` | maximum paddle movement speed in pixels per second |
| `reaction_time` | delay between target updates |
| `movement_threshold` | dead zone around the target position |

Canonical promoted genome:

```text
paddle_speed       = 420.0
reaction_time      = 0.039498692275418835
movement_threshold = 29.790193846648812
```

The controller updates its target from the ball position according to `reaction_time`, then moves toward that target using `paddle_speed` and `movement_threshold`.

## 🧠 Genetic algorithm

Run deterministic headless training:

```powershell
python -m ga.genetic_algorithm
```

Example with a smaller custom run:

```powershell
python -m ga.genetic_algorithm `
    --population-size 8 `
    --generations 3
```

Direct script execution is also supported:

```powershell
python ga/genetic_algorithm.py --population-size 8 --generations 3
```

### Default CLI parameters

- Evolution seed: `20260728`
- Population size: `16`
- Evaluated generations: `8`
- Elite count: `2`
- Tournament size: `3`
- Crossover rate: `0.8`
- Mutation rate: `0.2`
- Mutation sigma: `0.10`
- Match seeds: `20260728,20260729`
- Match limit: `1800` steps or `3` points
- Baseline opponent: `260,0,8`
- Score weight: `100.0`
- Return weight: `1.0`

### Canonical training run

The committed model and history were produced with:

- Evolution seed: `20260730`
- Population size: `32`
- Evaluated generations: `24`
- Elite count: `4`
- Tournament size: `4`
- Crossover rate: `0.8`
- Mutation rate: `0.2`
- Mutation sigma: `0.1`
- Training seeds: `2000,2001,2002,2003,2004,2005,2006,2007`
- Match limit: `3600` steps or `5` points
- Baseline opponent: `260,0,8`
- Score weight: `100.0`
- Return weight: `1.0`

The training command writes:

```text
logs/generations.csv
models/best_bot.json
```

Use custom paths with:

```powershell
python -m ga.genetic_algorithm `
    --log-path custom/generations.csv `
    --model-path custom/best_bot.json
```

## 📊 Fitness and evaluation

For one match, candidate fitness is calculated as:

```text
score_weight * (candidate_score - opponent_score)
    + return_weight * candidate_returns
```

Each candidate plays on both sides for every configured seed. Final fitness is the arithmetic mean across all matches.

The canonical CSV stores:

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

| Metric | Generation 0 | Generation 23 | Result |
|---|---:|---:|---:|
| Training mean fitness | -144.814453125 | 198.83984375 | +343.654296875 |
| Held-out fitness | 155.05 | 182.225 | +27.175 |
| Final vs initial | — | 13 W / 27 D / 0 L | 13:0 points |

Run the locked deterministic evaluation:

```powershell
python -m ga.evaluation
```

The evaluation uses held-out seeds `1000..1019`, which were not used during training. Every genome plays once on the left and once on the right for each seed.

Artifacts:

- [Full deterministic evaluation report](reports/evaluation.json)
- [Fitness progress chart](docs/fitness_progress.svg)

![Training and held-out fitness by generation](docs/fitness_progress.svg)

A visual replay is useful for inspection, but the numerical evaluation report is the formal evidence of improvement.

## 🕹️ Game modes and controls

### Human vs Bot

The human player controls the left paddle. The right paddle uses the saved global best genome from:

```text
models/best_bot.json
```

Controls:

- mouse inside the court;
- `W` / `S`;
- up / down arrow keys;
- `Esc` returns to the menu.

### Bot vs Bot

The selected generation champion plays on the left against generation `0` on the right.

Controls:

- left / right arrow keys change the selected generation;
- `Esc` returns to the menu.

Screenshots:

![Main menu](docs/screenshots/menu.png)

![Generation 0 replay](docs/screenshots/generation-0.png)

![Final generation replay](docs/screenshots/generation-final.png)

Regenerate them with:

```powershell
python -m tools.capture_screenshots
```

## 🧰 Technology stack

| Layer | Technology |
|---|---|
| Language | Python |
| Visual frontend | Pygame `2.6.1` |
| Simulation | custom deterministic 2D physics |
| Evolution | custom genetic algorithm |
| Artifacts | JSON, CSV, SVG, PNG |
| Tests | Python `unittest` |

No external dataset is used. Training data is generated by deterministic simulated matches.

## 🧪 Tests

Run all tests:

```powershell
python -m unittest discover -s tests -v
```

Additional checks:

```powershell
python -m compileall game ga tools tests
python -m pip check
```

The test suite covers:

- simulation and collision behavior;
- large-step and sub-30px tunneling regressions;
- bot and human controllers;
- deterministic match execution;
- genome validation;
- selection, crossover, and mutation;
- fitness aggregation;
- genetic algorithm evolution;
- CSV and JSON artifacts;
- CLI path and error behavior;
- deterministic evaluation;
- SVG generation;
- screenshot capture;
- frontend integration;
- edge cases and reproducibility.

## 📁 Project structure

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

## ⚠️ Notes

- Training is separate from the visual game and does not run in the background during gameplay.
- Human vs Bot always loads the committed best bot unless another model path is supplied.
- Bot vs Bot replays generation champions; it does not retrain them.
- `FITNESS` in the HUD is the historical training fitness of the selected generation champion, not the current match score.
- Generation numbering starts from `0`, so a 24-generation history contains generations `0..23`.
- The baseline genome `260,0,8` is used for training and evaluation; it is not the default Human vs Bot opponent.
- The committed JSON model is the implemented best-bot persistence bonus.

## 🧑‍💻 Author
Nazar Yestayev (@nyestaye)
