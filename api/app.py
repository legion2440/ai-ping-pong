"""FastAPI application exposing saved generation fitness data."""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ga.artifacts import GenerationRecord, load_generation_history

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GENERATIONS_PATH = PROJECT_ROOT / "logs" / "generations.csv"


class ApiInfo(BaseModel):
    name: str
    read_only: bool
    source: str
    docs: str


class HealthStatus(BaseModel):
    status: str


class GenomeResponse(BaseModel):
    paddle_speed: float
    reaction_time: float
    movement_threshold: float


class GenerationResponse(BaseModel):
    generation: int
    best_fitness: float
    mean_fitness: float
    worst_fitness: float
    genome: GenomeResponse


class FitnessResponse(BaseModel):
    generation: int
    best_fitness: float
    mean_fitness: float
    worst_fitness: float


def _generation_response(record: GenerationRecord) -> GenerationResponse:
    return GenerationResponse(
        generation=record.generation,
        best_fitness=record.best_fitness,
        mean_fitness=record.mean_fitness,
        worst_fitness=record.worst_fitness,
        genome=GenomeResponse(**record.genome.to_dict()),
    )


def _fitness_response(record: GenerationRecord) -> FitnessResponse:
    return FitnessResponse(
        generation=record.generation,
        best_fitness=record.best_fitness,
        mean_fitness=record.mean_fitness,
        worst_fitness=record.worst_fitness,
    )


def create_app(generations_path: Path) -> FastAPI:
    """Create an API that reloads the selected generation log per request."""
    source_path = Path(generations_path).resolve()
    application = FastAPI(
        title="AI Ping Pong API",
        description="Read-only access to generation and fitness history.",
    )

    def load_records() -> tuple[GenerationRecord, ...]:
        try:
            return load_generation_history(source_path)
        except FileNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail="generation log not found",
            ) from error
        except (ValueError, OSError, UnicodeError) as error:
            raise HTTPException(
                status_code=500,
                detail="generation log is invalid",
            ) from error

    @application.get("/", response_model=ApiInfo)
    def api_info() -> ApiInfo:
        return ApiInfo(
            name="AI Ping Pong API",
            read_only=True,
            source="logs/generations.csv",
            docs="/docs",
        )

    @application.get("/health", response_model=HealthStatus)
    def health() -> HealthStatus:
        return HealthStatus(status="ok")

    @application.get(
        "/generations",
        response_model=list[GenerationResponse],
    )
    def generations() -> list[GenerationResponse]:
        return [_generation_response(record) for record in load_records()]

    @application.get(
        "/generations/{generation}",
        response_model=GenerationResponse,
    )
    def generation_details(generation: int) -> GenerationResponse:
        if generation < 0:
            raise HTTPException(
                status_code=404,
                detail="generation not found",
            )

        for record in load_records():
            if record.generation == generation:
                return _generation_response(record)
        raise HTTPException(
            status_code=404,
            detail="generation not found",
        )

    @application.get("/fitness", response_model=list[FitnessResponse])
    def fitness() -> list[FitnessResponse]:
        return [_fitness_response(record) for record in load_records()]

    return application


app = create_app(DEFAULT_GENERATIONS_PATH)
