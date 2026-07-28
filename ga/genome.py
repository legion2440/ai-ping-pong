import math
from dataclasses import dataclass
from numbers import Real

PADDLE_SPEED_MIN = 120.0
PADDLE_SPEED_MAX = 420.0
REACTION_TIME_MIN = 0.0
REACTION_TIME_MAX = 0.30
MOVEMENT_THRESHOLD_MIN = 0.0
MOVEMENT_THRESHOLD_MAX = 40.0


def _validated_parameter(name, value, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")

    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True)
class BotGenome:
    paddle_speed: float
    reaction_time: float
    movement_threshold: float

    def __post_init__(self):
        object.__setattr__(
            self,
            "paddle_speed",
            _validated_parameter(
                "paddle_speed",
                self.paddle_speed,
                PADDLE_SPEED_MIN,
                PADDLE_SPEED_MAX,
            ),
        )
        object.__setattr__(
            self,
            "reaction_time",
            _validated_parameter(
                "reaction_time",
                self.reaction_time,
                REACTION_TIME_MIN,
                REACTION_TIME_MAX,
            ),
        )
        object.__setattr__(
            self,
            "movement_threshold",
            _validated_parameter(
                "movement_threshold",
                self.movement_threshold,
                MOVEMENT_THRESHOLD_MIN,
                MOVEMENT_THRESHOLD_MAX,
            ),
        )

    def to_vector(self):
        return [
            self.paddle_speed,
            self.reaction_time,
            self.movement_threshold,
        ]

    @classmethod
    def from_vector(cls, vector):
        try:
            values = tuple(vector)
        except TypeError as error:
            raise TypeError("vector must be iterable") from error

        if len(values) != 3:
            raise ValueError("vector must contain exactly three elements")
        return cls(*values)

    def to_dict(self):
        return {
            "paddle_speed": self.paddle_speed,
            "reaction_time": self.reaction_time,
            "movement_threshold": self.movement_threshold,
        }
