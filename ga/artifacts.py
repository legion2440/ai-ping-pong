import csv
import io
import json
import os
import tempfile
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
