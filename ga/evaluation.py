import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import sys
from pathlib import Path

_INVOCATION_CWD_ENV = "_AI_PING_PONG_EVALUATION_INVOCATION_CWD"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__" and __package__ is None:
    os.environ[_INVOCATION_CWD_ENV] = os.getcwd()
    os.chdir(PROJECT_ROOT)
    os.execv(
        sys.executable,
        [sys.executable, "-m", "ga.evaluation", *sys.argv[1:]],
    )

INVOCATION_CWD = Path(
    os.environ.pop(_INVOCATION_CWD_ENV, os.getcwd())
).resolve()

import argparse
import html
import json
from dataclasses import dataclass

from game.match_runner import MatchConfig
from game.utils import COLORS

from .artifacts import (
    GenerationRecord,
    atomic_write_text,
    load_generation_history,
)
from .fitness import FitnessConfig, GenomeEvaluation, evaluate_genome
from .genome import BotGenome

SCORE_WEIGHT = 100.0
RETURN_WEIGHT = 1.0
SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class EvaluationConfig:
    seeds: tuple[int, ...] = tuple(range(1000, 1020))
    match_config: MatchConfig = MatchConfig(
        dt=1 / 60,
        max_steps=3600,
        score_limit=5,
    )
    baseline_genome: BotGenome = BotGenome(260.0, 0.0, 8.0)

    def __post_init__(self):
        try:
            seeds = tuple(self.seeds)
        except TypeError as error:
            raise TypeError("seeds must be an iterable") from error
        if not seeds:
            raise ValueError("seeds must not be empty")
        if any(type(seed) is not int for seed in seeds):
            raise TypeError("every seed must be an int")
        object.__setattr__(self, "seeds", seeds)

        if not isinstance(self.match_config, MatchConfig):
            raise TypeError("match_config must be a MatchConfig")
        if not isinstance(self.baseline_genome, BotGenome):
            raise TypeError("baseline_genome must be a BotGenome")

    def to_dict(self):
        return {
            "seeds": list(self.seeds),
            "match_config": self.match_config.to_dict(),
            "baseline_genome": self.baseline_genome.to_dict(),
            "score_weight": SCORE_WEIGHT,
            "return_weight": RETURN_WEIGHT,
        }


@dataclass(frozen=True, slots=True)
class GenerationEvaluation:
    generation: int
    genome: BotGenome
    training_best_fitness: float
    training_mean_fitness: float
    training_worst_fitness: float
    held_out: GenomeEvaluation

    def to_dict(self):
        return {
            "generation": self.generation,
            "genome": self.genome.to_dict(),
            "training_best_fitness": self.training_best_fitness,
            "training_mean_fitness": self.training_mean_fitness,
            "training_worst_fitness": self.training_worst_fitness,
            "held_out": self.held_out.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    config: EvaluationConfig
    generations: tuple[GenerationEvaluation, ...]
    final_vs_initial: GenomeEvaluation
    training_mean_delta: float
    held_out_fitness_delta: float
    training_mean_improved: bool
    held_out_fitness_improved: bool
    final_outperformed_initial: bool

    def to_dict(self):
        initial = self.generations[0]
        final = self.generations[-1]
        comparison = self.final_vs_initial
        return {
            "schema_version": SCHEMA_VERSION,
            "evaluation_config": self.config.to_dict(),
            "training_progress": {
                "initial_mean_fitness": initial.training_mean_fitness,
                "final_mean_fitness": final.training_mean_fitness,
                "delta": self.training_mean_delta,
                "improved": self.training_mean_improved,
            },
            "held_out_progress": {
                "initial_fitness": initial.held_out.fitness,
                "final_fitness": final.held_out.fitness,
                "delta": self.held_out_fitness_delta,
                "improved": self.held_out_fitness_improved,
            },
            "final_vs_initial": {
                "matches": comparison.matches,
                "wins": comparison.wins,
                "draws": comparison.draws,
                "losses": comparison.losses,
                "points_for": comparison.points_for,
                "points_against": comparison.points_against,
                "returns": comparison.returns,
                "outperformed": self.final_outperformed_initial,
            },
            "generations": [
                generation.to_dict()
                for generation in self.generations
            ],
        }


def evaluate_generation_history(
    records,
    config: EvaluationConfig = EvaluationConfig(),
) -> EvaluationReport:
    try:
        records = tuple(records)
    except TypeError as error:
        raise TypeError("records must be an iterable") from error
    if not records:
        raise ValueError("records must not be empty")
    if any(not isinstance(record, GenerationRecord) for record in records):
        raise TypeError(
            "records must contain only GenerationRecord values"
        )
    if not isinstance(config, EvaluationConfig):
        raise TypeError("config must be an EvaluationConfig")

    champion_fitness_config = FitnessConfig(
        seeds=config.seeds,
        match_config=config.match_config,
        opponent_genome=config.baseline_genome,
        score_weight=SCORE_WEIGHT,
        return_weight=RETURN_WEIGHT,
    )
    generations = []
    for record in records:
        held_out = evaluate_genome(record.genome, champion_fitness_config)
        generations.append(
            GenerationEvaluation(
                generation=record.generation,
                genome=record.genome,
                training_best_fitness=record.best_fitness,
                training_mean_fitness=record.mean_fitness,
                training_worst_fitness=record.worst_fitness,
                held_out=held_out,
            )
        )
    generations = tuple(generations)

    final_fitness_config = FitnessConfig(
        seeds=config.seeds,
        match_config=config.match_config,
        opponent_genome=records[0].genome,
        score_weight=SCORE_WEIGHT,
        return_weight=RETURN_WEIGHT,
    )
    final_vs_initial = evaluate_genome(
        records[-1].genome,
        final_fitness_config,
    )

    training_mean_delta = (
        records[-1].mean_fitness - records[0].mean_fitness
    )
    held_out_fitness_delta = (
        generations[-1].held_out.fitness
        - generations[0].held_out.fitness
    )
    training_mean_improved = training_mean_delta > 0
    held_out_fitness_improved = held_out_fitness_delta > 0
    final_outperformed_initial = (
        final_vs_initial.wins > final_vs_initial.losses
        and final_vs_initial.points_for
        > final_vs_initial.points_against
    )

    return EvaluationReport(
        config=config,
        generations=generations,
        final_vs_initial=final_vs_initial,
        training_mean_delta=training_mean_delta,
        held_out_fitness_delta=held_out_fitness_delta,
        training_mean_improved=training_mean_improved,
        held_out_fitness_improved=held_out_fitness_improved,
        final_outperformed_initial=final_outperformed_initial,
    )


def _svg_color(name):
    red, green, blue = COLORS[name]
    return f"#{red:02x}{green:02x}{blue:02x}"


def _format_axis_value(value):
    return f"{value:.2f}".rstrip("0").rstrip(".")


def render_fitness_progress_svg(report: EvaluationReport) -> str:
    if not isinstance(report, EvaluationReport):
        raise TypeError("report must be an EvaluationReport")

    width = 900
    height = 500
    left = 90
    right = 30
    top = 70
    bottom = 70
    plot_width = width - left - right
    plot_height = height - top - bottom
    series = (
        (
            "Training best",
            [
                generation.training_best_fitness
                for generation in report.generations
            ],
            _svg_color("cyan"),
        ),
        (
            "Training mean",
            [
                generation.training_mean_fitness
                for generation in report.generations
            ],
            _svg_color("lime"),
        ),
        (
            "Held-out champion",
            [
                generation.held_out.fitness
                for generation in report.generations
            ],
            _svg_color("magenta"),
        ),
    )
    all_values = [
        value
        for _, values, _ in series
        for value in values
    ]
    minimum = min(all_values)
    maximum = max(all_values)
    if minimum == maximum:
        y_padding = max(abs(minimum) * 0.1, 1.0)
    else:
        y_padding = (maximum - minimum) * 0.1
    y_minimum = minimum - y_padding
    y_maximum = maximum + y_padding

    generation_numbers = [
        generation.generation
        for generation in report.generations
    ]
    x_minimum = min(generation_numbers)
    x_maximum = max(generation_numbers)

    def x_coordinate(generation):
        if x_minimum == x_maximum:
            return left + plot_width / 2
        return left + (
            (generation - x_minimum)
            / (x_maximum - x_minimum)
            * plot_width
        )

    def y_coordinate(value):
        return top + (
            (y_maximum - value)
            / (y_maximum - y_minimum)
            * plot_height
        )

    background = _svg_color("bg")
    panel = _svg_color("panel")
    border = _svg_color("border")
    grid = _svg_color("grid")
    text = _svg_color("text")
    muted = _svg_color("muted")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}">'
        ),
        "  <title>Fitness progress</title>",
        (
            "  <desc>Training best, training mean, and held-out champion "
            "fitness by generation.</desc>"
        ),
        f'  <rect width="{width}" height="{height}" fill="{background}"/>',
        (
            f'  <rect x="{left}" y="{top}" width="{plot_width}" '
            f'height="{plot_height}" fill="{panel}" stroke="{border}"/>'
        ),
        (
            f'  <text x="{width / 2:.2f}" y="35" fill="{text}" '
            'font-family="monospace" font-size="22" '
            'font-weight="bold" text-anchor="middle">'
            "Fitness progress</text>"
        ),
    ]

    for tick in range(6):
        ratio = tick / 5
        y = top + ratio * plot_height
        value = y_maximum - ratio * (y_maximum - y_minimum)
        lines.extend(
            [
                (
                    f'  <line x1="{left}" y1="{y:.2f}" '
                    f'x2="{left + plot_width}" y2="{y:.2f}" '
                    f'stroke="{grid}"/>'
                ),
                (
                    f'  <text x="{left - 12}" y="{y + 4:.2f}" '
                    f'fill="{muted}" font-family="monospace" '
                    'font-size="12" text-anchor="end">'
                    f"{html.escape(_format_axis_value(value))}</text>"
                ),
            ]
        )

    for generation in generation_numbers:
        x = x_coordinate(generation)
        lines.extend(
            [
                (
                    f'  <line x1="{x:.2f}" y1="{top}" '
                    f'x2="{x:.2f}" y2="{top + plot_height}" '
                    f'stroke="{grid}"/>'
                ),
                (
                    f'  <text x="{x:.2f}" y="{top + plot_height + 24}" '
                    f'fill="{muted}" font-family="monospace" '
                    'font-size="12" text-anchor="middle">'
                    f"{generation}</text>"
                ),
            ]
        )

    lines.extend(
        [
            (
                f'  <text x="{left + plot_width / 2:.2f}" '
                f'y="{height - 18}" fill="{muted}" '
                'font-family="monospace" font-size="13" '
                'text-anchor="middle">Generation</text>'
            ),
            (
                f'  <text x="22" y="{top + plot_height / 2:.2f}" '
                f'fill="{muted}" font-family="monospace" '
                'font-size="13" text-anchor="middle" '
                f'transform="rotate(-90 22 {top + plot_height / 2:.2f})">'
                "Fitness</text>"
            ),
        ]
    )

    for label, values, color in series:
        points = " ".join(
            f"{x_coordinate(generation):.2f},{y_coordinate(value):.2f}"
            for generation, value in zip(generation_numbers, values)
        )
        lines.append(
            f'  <polyline points="{points}" fill="none" '
            f'stroke="{color}" stroke-width="3"/>'
        )
        for generation, value in zip(generation_numbers, values):
            lines.append(
                f'  <circle cx="{x_coordinate(generation):.2f}" '
                f'cy="{y_coordinate(value):.2f}" r="4" '
                f'fill="{color}"/>'
            )

    legend_x = left + 16
    legend_y = top + 22
    for index, (label, _, color) in enumerate(series):
        x = legend_x + index * 210
        lines.extend(
            [
                (
                    f'  <line x1="{x}" y1="{legend_y}" '
                    f'x2="{x + 28}" y2="{legend_y}" '
                    f'stroke="{color}" stroke-width="3"/>'
                ),
                (
                    f'  <text x="{x + 36}" y="{legend_y + 4}" '
                    f'fill="{text}" font-family="monospace" '
                    f'font-size="12">{html.escape(label)}</text>'
                ),
            ]
        )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def _parse_seeds(value):
    try:
        return tuple(int(item.strip()) for item in value.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "evaluation seeds must be integers"
        ) from error


def _parse_genome(value):
    try:
        vector = (float(item.strip()) for item in value.split(","))
        return BotGenome.from_vector(vector)
    except (TypeError, ValueError) as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def _build_parser():
    defaults = EvaluationConfig()
    parser = argparse.ArgumentParser(
        description="Evaluate generation champions on held-out match seeds"
    )
    parser.add_argument("--generations-path", type=Path, default=None)
    parser.add_argument("--report-path", type=Path, default=None)
    parser.add_argument("--chart-path", type=Path, default=None)
    parser.add_argument("--seeds", type=_parse_seeds, default=defaults.seeds)
    parser.add_argument(
        "--match-dt",
        type=float,
        default=defaults.match_config.dt,
    )
    parser.add_argument(
        "--match-max-steps",
        type=int,
        default=defaults.match_config.max_steps,
    )
    parser.add_argument(
        "--match-score-limit",
        type=int,
        default=defaults.match_config.score_limit,
    )
    parser.add_argument(
        "--baseline",
        type=_parse_genome,
        default=defaults.baseline_genome,
    )
    parser.add_argument("--no-artifacts", action="store_true")
    return parser


def _resolve_path(path, canonical_path):
    if path is None:
        return PROJECT_ROOT / canonical_path
    if path.is_absolute():
        return path
    return INVOCATION_CWD / path


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    generations_path = _resolve_path(
        args.generations_path,
        Path("logs/generations.csv"),
    )
    report_path = _resolve_path(
        args.report_path,
        Path("reports/evaluation.json"),
    )
    chart_path = _resolve_path(
        args.chart_path,
        Path("docs/fitness_progress.svg"),
    )

    try:
        config = EvaluationConfig(
            seeds=args.seeds,
            match_config=MatchConfig(
                dt=args.match_dt,
                max_steps=args.match_max_steps,
                score_limit=args.match_score_limit,
            ),
            baseline_genome=args.baseline,
        )
        records = load_generation_history(generations_path)
        report = evaluate_generation_history(records, config)
        payload = report.to_dict()
        report_content = (
            json.dumps(payload, sort_keys=True, indent=2) + "\n"
        )
        chart_content = render_fitness_progress_svg(report)
    except (OSError, TypeError, ValueError) as error:
        parser.error(str(error))

    if not args.no_artifacts:
        try:
            atomic_write_text(report_path, report_content)
            atomic_write_text(chart_path, chart_content)
        except (OSError, ValueError) as error:
            parser.error(str(error))

    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
