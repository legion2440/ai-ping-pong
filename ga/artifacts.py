import csv
import io
import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .genome import BotGenome

CSV_HEADER = (
    "generation",
    "best_fitness",
    "mean_fitness",
    "worst_fitness",
    "paddle_speed",
    "reaction_time",
    "movement_threshold",
)
SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class GenerationRecord:
    generation: int
    best_fitness: float
    mean_fitness: float
    worst_fitness: float
    genome: BotGenome


def _atomic_write_text(path, content):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.replace(temporary_path, target)
    except BaseException:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
        raise


def write_generations_csv(result, path):
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(CSV_HEADER)

    for stats in result.history:
        genome = stats.best_genome
        writer.writerow(
            (
                stats.generation,
                stats.best_fitness,
                stats.mean_fitness,
                stats.worst_fitness,
                genome.paddle_speed,
                genome.reaction_time,
                genome.movement_threshold,
            )
        )

    _atomic_write_text(path, output.getvalue())


def load_generation_history(path) -> tuple[GenerationRecord, ...]:
    try:
        with Path(path).open(encoding="utf-8", newline="") as history_file:
            reader = csv.DictReader(history_file, strict=True)
            if tuple(reader.fieldnames or ()) != CSV_HEADER:
                raise ValueError(
                    "generation history must use the exact canonical header"
                )

            records = []
            for expected_generation, row in enumerate(reader):
                if None in row or any(row[field] is None for field in CSV_HEADER):
                    raise ValueError(
                        "generation history row does not match the header"
                    )

                try:
                    generation = int(row["generation"])
                except ValueError as error:
                    raise ValueError(
                        "generation must be an integer"
                    ) from error
                if generation != expected_generation:
                    raise ValueError(
                        "generations must be consecutive and start at zero"
                    )

                numeric_values = {}
                for field in CSV_HEADER[1:]:
                    try:
                        value = float(row[field])
                    except ValueError as error:
                        raise ValueError(
                            f"{field} must be a number"
                        ) from error
                    if not math.isfinite(value):
                        raise ValueError(f"{field} must be finite")
                    numeric_values[field] = value

                try:
                    genome = BotGenome(
                        paddle_speed=numeric_values["paddle_speed"],
                        reaction_time=numeric_values["reaction_time"],
                        movement_threshold=numeric_values[
                            "movement_threshold"
                        ],
                    )
                except (TypeError, ValueError) as error:
                    raise ValueError(
                        "generation history contains an invalid genome"
                    ) from error

                records.append(
                    GenerationRecord(
                        generation=generation,
                        best_fitness=numeric_values["best_fitness"],
                        mean_fitness=numeric_values["mean_fitness"],
                        worst_fitness=numeric_values["worst_fitness"],
                        genome=genome,
                    )
                )
    except csv.Error as error:
        raise ValueError("generation history contains invalid CSV") from error

    if not records:
        raise ValueError("generation history must contain at least one row")
    return tuple(records)


def write_best_genome_json(result, path):
    payload = {
        "schema_version": SCHEMA_VERSION,
        "fitness": result.best_fitness,
        "genome": result.best_genome.to_dict(),
        "evolution_config": result.evolution_config.to_dict(),
        "fitness_config": result.fitness_config.to_dict(),
    }
    content = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    _atomic_write_text(path, content)


def load_best_genome(path):
    try:
        with Path(path).open(encoding="utf-8") as model_file:
            payload = json.load(model_file)
    except json.JSONDecodeError as error:
        raise ValueError("best genome file contains invalid JSON") from error

    if not isinstance(payload, dict):
        raise ValueError("best genome file root must be a JSON object")

    schema_version = payload.get("schema_version")
    if type(schema_version) is not int or schema_version != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {schema_version!r}")

    genome_payload = payload.get("genome")
    if not isinstance(genome_payload, dict):
        raise ValueError("genome must be a JSON object")

    try:
        return BotGenome(**genome_payload)
    except (TypeError, ValueError) as error:
        raise ValueError("best genome file contains an invalid genome") from error
