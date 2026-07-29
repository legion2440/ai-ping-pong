import json
import math
import random
import tempfile
import unittest
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from unittest.mock import patch

from ga.artifacts import GenerationRecord, atomic_write_text
from ga.evaluation import (
    RETURN_WEIGHT,
    SCORE_WEIGHT,
    EvaluationConfig,
    EvaluationReport,
    GenerationEvaluation,
    evaluate_generation_history,
    render_fitness_progress_svg,
)
from ga.fitness import GenomeEvaluation
from ga.genome import BotGenome
from game.match_runner import MatchConfig

INITIAL_GENOME = BotGenome(200.0, 0.1, 5.0)
MIDDLE_GENOME = BotGenome(280.0, 0.05, 8.0)
FINAL_GENOME = BotGenome(320.0, 0.02, 4.0)
BASELINE_GENOME = BotGenome(260.0, 0.0, 8.0)
RECORDS = (
    GenerationRecord(0, 10.0, -5.0, -20.0, INITIAL_GENOME),
    GenerationRecord(1, 20.0, 2.0, -10.0, MIDDLE_GENOME),
    GenerationRecord(2, 30.0, 8.0, -2.0, FINAL_GENOME),
)


def make_evaluation(
    genome,
    fitness,
    *,
    wins=1,
    draws=0,
    losses=0,
    points_for=2,
    points_against=1,
    returns=3,
):
    return GenomeEvaluation(
        genome=genome,
        fitness=fitness,
        matches=wins + draws + losses,
        wins=wins,
        draws=draws,
        losses=losses,
        points_for=points_for,
        points_against=points_against,
        returns=returns,
    )


def make_report(
    *,
    first_fitness=-4.0,
    final_fitness=6.0,
    training_mean_delta=13.0,
    held_out_fitness_delta=10.0,
    final_wins=3,
    final_losses=1,
    final_points_for=8,
    final_points_against=4,
):
    config = EvaluationConfig(
        seeds=(1000,),
        match_config=MatchConfig(max_steps=2, score_limit=1),
    )
    generations = (
        GenerationEvaluation(
            generation=0,
            genome=INITIAL_GENOME,
            training_best_fitness=10.0,
            training_mean_fitness=-5.0,
            training_worst_fitness=-20.0,
            held_out=make_evaluation(
                INITIAL_GENOME,
                first_fitness,
            ),
        ),
        GenerationEvaluation(
            generation=2,
            genome=FINAL_GENOME,
            training_best_fitness=30.0,
            training_mean_fitness=8.0,
            training_worst_fitness=-2.0,
            held_out=make_evaluation(
                FINAL_GENOME,
                final_fitness,
            ),
        ),
    )
    comparison = make_evaluation(
        FINAL_GENOME,
        99.0,
        wins=final_wins,
        draws=0,
        losses=final_losses,
        points_for=final_points_for,
        points_against=final_points_against,
        returns=12,
    )
    return EvaluationReport(
        config=config,
        generations=generations,
        final_vs_initial=comparison,
        training_mean_delta=training_mean_delta,
        held_out_fitness_delta=held_out_fitness_delta,
        training_mean_improved=training_mean_delta > 0,
        held_out_fitness_improved=held_out_fitness_delta > 0,
        final_outperformed_initial=(
            final_wins > final_losses
            and final_points_for > final_points_against
        ),
    )


class EvaluationConfigTests(unittest.TestCase):
    def test_default_seeds_are_held_out_from_training(self):
        config = EvaluationConfig()

        self.assertEqual(config.seeds, tuple(range(1000, 1020)))
        self.assertTrue(
            set(config.seeds).isdisjoint({20260728, 20260729})
        )

    def test_values_are_normalized_and_protocol_weights_are_serialized(self):
        match_config = MatchConfig(dt=0.25, max_steps=10, score_limit=2)
        config = EvaluationConfig(
            seeds=[-2, 3],
            match_config=match_config,
            baseline_genome=BASELINE_GENOME,
        )

        self.assertEqual(config.seeds, (-2, 3))
        self.assertIs(config.match_config, match_config)
        self.assertIs(config.baseline_genome, BASELINE_GENOME)
        self.assertEqual(
            config.to_dict(),
            {
                "seeds": [-2, 3],
                "match_config": match_config.to_dict(),
                "baseline_genome": BASELINE_GENOME.to_dict(),
                "score_weight": SCORE_WEIGHT,
                "return_weight": RETURN_WEIGHT,
            },
        )

    def test_seeds_must_be_a_nonempty_iterable_of_real_ints(self):
        for seeds, exception_type in (
            (None, TypeError),
            ((), ValueError),
            ((True,), TypeError),
            ((1.0,), TypeError),
            (("1",), TypeError),
        ):
            with self.subTest(seeds=seeds):
                with self.assertRaises(exception_type):
                    EvaluationConfig(seeds=seeds)

    def test_match_config_and_baseline_require_expected_types(self):
        with self.assertRaisesRegex(TypeError, "match_config"):
            EvaluationConfig(match_config={})
        with self.assertRaisesRegex(TypeError, "baseline_genome"):
            EvaluationConfig(baseline_genome={})


class GenerationHistoryEvaluationTests(unittest.TestCase):
    def test_records_are_validated_before_evaluation(self):
        for records, exception_type, message in (
            (None, TypeError, "iterable"),
            ((), ValueError, "must not be empty"),
            ((RECORDS[0], FINAL_GENOME), TypeError, "GenerationRecord"),
        ):
            with self.subTest(records=records):
                with patch("ga.evaluation.evaluate_genome") as evaluator:
                    with self.assertRaisesRegex(exception_type, message):
                        evaluate_generation_history(records)
                evaluator.assert_not_called()

        with patch("ga.evaluation.evaluate_genome") as evaluator:
            with self.assertRaisesRegex(TypeError, "EvaluationConfig"):
                evaluate_generation_history(RECORDS, {})
        evaluator.assert_not_called()

    def test_champions_use_one_config_in_order_and_final_uses_initial(self):
        calls = []
        champion_fitness = {
            INITIAL_GENOME: -10.0,
            MIDDLE_GENOME: 0.0,
            FINAL_GENOME: 15.0,
        }

        def fake_evaluate(genome, config):
            calls.append((genome, config))
            if config.opponent_genome == INITIAL_GENOME:
                return make_evaluation(
                    genome,
                    25.0,
                    wins=3,
                    losses=1,
                    points_for=8,
                    points_against=4,
                )
            return make_evaluation(genome, champion_fitness[genome])

        config = EvaluationConfig(seeds=(-3, 4))
        with patch(
            "ga.evaluation.evaluate_genome",
            side_effect=fake_evaluate,
        ):
            report = evaluate_generation_history(
                (record for record in RECORDS),
                config,
            )

        self.assertEqual(
            [generation.generation for generation in report.generations],
            [0, 1, 2],
        )
        self.assertEqual(
            [genome for genome, _ in calls],
            [INITIAL_GENOME, MIDDLE_GENOME, FINAL_GENOME, FINAL_GENOME],
        )
        champion_configs = [item[1] for item in calls[:3]]
        self.assertTrue(
            all(item is champion_configs[0] for item in champion_configs)
        )
        self.assertEqual(
            champion_configs[0].opponent_genome,
            BASELINE_GENOME,
        )
        self.assertEqual(champion_configs[0].seeds, (-3, 4))
        self.assertIsNot(calls[3][1], champion_configs[0])
        self.assertIs(calls[3][1].opponent_genome, INITIAL_GENOME)
        self.assertEqual(report.training_mean_delta, 13.0)
        self.assertEqual(report.held_out_fitness_delta, 25.0)
        self.assertTrue(report.training_mean_improved)
        self.assertTrue(report.held_out_fitness_improved)
        self.assertTrue(report.final_outperformed_initial)

    def test_improvement_and_outperformance_checks_are_strict(self):
        champion_results = (
            make_evaluation(INITIAL_GENOME, -5.0),
            make_evaluation(MIDDLE_GENOME, 1.0),
            make_evaluation(FINAL_GENOME, -5.0),
        )
        final_comparison = make_evaluation(
            FINAL_GENOME,
            100.0,
            wins=2,
            losses=2,
            points_for=5,
            points_against=4,
        )
        with patch(
            "ga.evaluation.evaluate_genome",
            side_effect=(*champion_results, final_comparison),
        ):
            report = evaluate_generation_history(RECORDS)

        self.assertFalse(report.held_out_fitness_improved)
        self.assertFalse(report.final_outperformed_initial)
        self.assertEqual(report.held_out_fitness_delta, 0.0)
        self.assertEqual(report.generations[0].held_out.fitness, -5.0)

        final_comparison = make_evaluation(
            FINAL_GENOME,
            100.0,
            wins=3,
            losses=1,
            points_for=4,
            points_against=4,
        )
        with patch(
            "ga.evaluation.evaluate_genome",
            side_effect=(*champion_results, final_comparison),
        ):
            report = evaluate_generation_history(RECORDS)
        self.assertFalse(report.final_outperformed_initial)

    def test_small_real_evaluation_is_deterministic_and_preserves_random(self):
        config = EvaluationConfig(
            seeds=(-1,),
            match_config=MatchConfig(
                dt=1 / 60,
                max_steps=4,
                score_limit=1,
            ),
        )
        random_state = random.getstate()

        first = evaluate_generation_history(RECORDS[:2], config)
        second = evaluate_generation_history(RECORDS[:2], config)

        self.assertEqual(first, second)
        self.assertEqual(random.getstate(), random_state)
        self.assertTrue(
            all(
                generation.held_out.matches == 2
                for generation in first.generations
            )
        )

    def test_equal_training_means_are_not_an_improvement(self):
        records = (
            RECORDS[0],
            GenerationRecord(
                generation=1,
                best_fitness=20.0,
                mean_fitness=RECORDS[0].mean_fitness,
                worst_fitness=-10.0,
                genome=FINAL_GENOME,
            ),
        )
        evaluations = (
            make_evaluation(INITIAL_GENOME, 0.0),
            make_evaluation(FINAL_GENOME, 1.0),
            make_evaluation(
                FINAL_GENOME,
                1.0,
                wins=2,
                losses=1,
                points_for=2,
                points_against=1,
            ),
        )

        with patch(
            "ga.evaluation.evaluate_genome",
            side_effect=evaluations,
        ):
            report = evaluate_generation_history(records)

        self.assertEqual(report.training_mean_delta, 0.0)
        self.assertFalse(report.training_mean_improved)


class EvaluationSerializationTests(unittest.TestCase):
    def test_report_uses_the_fixed_json_contract(self):
        payload = make_report().to_dict()

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(
            set(payload["generations"][0]),
            {
                "generation",
                "genome",
                "training_best_fitness",
                "training_mean_fitness",
                "training_worst_fitness",
                "held_out",
            },
        )
        self.assertEqual(
            payload["generations"][0]["held_out"],
            make_report().generations[0].held_out.to_dict(),
        )
        self.assertEqual(
            set(payload["final_vs_initial"]),
            {
                "matches",
                "wins",
                "draws",
                "losses",
                "points_for",
                "points_against",
                "returns",
                "outperformed",
            },
        )
        self.assertNotIn("fitness", payload["final_vs_initial"])
        self.assertNotIn("genome", payload["final_vs_initial"])

    def test_pretty_json_is_deterministic_with_lf_ending(self):
        report = make_report()
        content = (
            json.dumps(report.to_dict(), sort_keys=True, indent=2) + "\n"
        )

        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.json"
            second_path = Path(directory) / "second.json"
            atomic_write_text(first_path, content)
            atomic_write_text(second_path, content)

            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
            self.assertTrue(first_path.read_bytes().endswith(b"\n"))
            self.assertNotIn(b"\r\n", first_path.read_bytes())


class FitnessChartTests(unittest.TestCase):
    def test_svg_is_deterministic_valid_and_contains_all_series(self):
        report = make_report()

        first = render_fitness_progress_svg(report)
        second = render_fitness_progress_svg(report)
        root = ElementTree.fromstring(first)

        self.assertEqual(first, second)
        self.assertEqual(root.attrib["width"], "900")
        self.assertEqual(root.attrib["height"], "500")
        self.assertTrue(first.endswith("\n"))
        self.assertIn("<title>Fitness progress</title>", first)
        self.assertIn("Training best", first)
        self.assertIn("Training mean", first)
        self.assertIn("Held-out champion", first)
        self.assertNotIn("timestamp", first.lower())

    def test_svg_handles_one_generation_and_flat_negative_values(self):
        evaluation = make_evaluation(INITIAL_GENOME, -7.0)
        generation = GenerationEvaluation(
            generation=4,
            genome=INITIAL_GENOME,
            training_best_fitness=-7.0,
            training_mean_fitness=-7.0,
            training_worst_fitness=-7.0,
            held_out=evaluation,
        )
        report = EvaluationReport(
            config=EvaluationConfig(seeds=(1000,)),
            generations=(generation,),
            final_vs_initial=evaluation,
            training_mean_delta=0.0,
            held_out_fitness_delta=0.0,
            training_mean_improved=False,
            held_out_fitness_improved=False,
            final_outperformed_initial=False,
        )

        svg = render_fitness_progress_svg(report)

        ElementTree.fromstring(svg)
        self.assertNotIn("nan", svg.lower())
        self.assertNotIn("inf", svg.lower())
        self.assertEqual(svg.count("<circle "), 3)

    def test_wrong_report_type_is_rejected(self):
        with self.assertRaisesRegex(TypeError, "EvaluationReport"):
            render_fitness_progress_svg({})


if __name__ == "__main__":
    unittest.main()
