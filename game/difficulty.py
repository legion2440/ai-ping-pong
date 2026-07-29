"""Runtime difficulty controls for the visual game."""

import math
from dataclasses import dataclass
from numbers import Real

from .utils import PADDLE_H

AUTO_INTERVAL = 20.0

BALL_SPEED_MIN = 0.5
BALL_SPEED_DEFAULT = 1.0
BALL_SPEED_MAX = 2.0
BALL_SPEED_STEP = 0.1

PADDLE_HEIGHT_MIN = 50
PADDLE_HEIGHT_DEFAULT = PADDLE_H
PADDLE_HEIGHT_MAX = 120
PADDLE_HEIGHT_STEP = 5


def _validate_real(value, name):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _validate_step_count(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("steps must be an int")
    return value


@dataclass(slots=True)
class DifficultyState:
    ball_speed_multiplier: float = BALL_SPEED_DEFAULT
    paddle_height: int = PADDLE_HEIGHT_DEFAULT
    auto_enabled: bool = True
    elapsed: float = 0.0

    def __post_init__(self):
        self.ball_speed_multiplier = _validate_real(
            self.ball_speed_multiplier,
            "ball_speed_multiplier",
        )
        if not (
            BALL_SPEED_MIN
            <= self.ball_speed_multiplier
            <= BALL_SPEED_MAX
        ):
            raise ValueError(
                "ball_speed_multiplier must be between "
                f"{BALL_SPEED_MIN} and {BALL_SPEED_MAX}"
            )
        if (
            isinstance(self.paddle_height, bool)
            or not isinstance(self.paddle_height, int)
        ):
            raise TypeError("paddle_height must be an int")
        if not (
            PADDLE_HEIGHT_MIN
            <= self.paddle_height
            <= PADDLE_HEIGHT_MAX
        ):
            raise ValueError(
                "paddle_height must be between "
                f"{PADDLE_HEIGHT_MIN} and {PADDLE_HEIGHT_MAX}"
            )
        if type(self.auto_enabled) is not bool:
            raise TypeError("auto_enabled must be a bool")
        self.elapsed = _validate_real(self.elapsed, "elapsed")
        if self.elapsed < 0:
            raise ValueError("elapsed must be non-negative")

    def reset(self):
        self.ball_speed_multiplier = BALL_SPEED_DEFAULT
        self.paddle_height = PADDLE_HEIGHT_DEFAULT
        self.auto_enabled = True
        self.elapsed = 0.0

    def set_auto(self, enabled):
        if type(enabled) is not bool:
            raise TypeError("enabled must be a bool")
        changed = enabled != self.auto_enabled
        self.auto_enabled = enabled
        return changed

    def adjust_ball_speed(self, steps):
        steps = _validate_step_count(steps)
        new_value = round(
            self.ball_speed_multiplier + steps * BALL_SPEED_STEP,
            10,
        )
        new_value = min(BALL_SPEED_MAX, max(BALL_SPEED_MIN, new_value))
        if new_value == self.ball_speed_multiplier:
            return False
        self.ball_speed_multiplier = new_value
        return True

    def adjust_paddle_height(self, steps):
        steps = _validate_step_count(steps)
        new_value = self.paddle_height + steps * PADDLE_HEIGHT_STEP
        new_value = min(
            PADDLE_HEIGHT_MAX,
            max(PADDLE_HEIGHT_MIN, new_value),
        )
        if new_value == self.paddle_height:
            return False
        self.paddle_height = new_value
        return True

    def apply_next_auto_level(self):
        speed_changed = self.adjust_ball_speed(1)
        paddle_changed = self.adjust_paddle_height(-1)
        return speed_changed or paddle_changed

    def update(self, dt):
        dt = _validate_real(dt, "dt")
        if dt < 0:
            raise ValueError("dt must be non-negative")
        if not self.auto_enabled:
            return 0

        self.elapsed += dt
        levels = 0
        while self.elapsed >= AUTO_INTERVAL:
            self.elapsed -= AUTO_INTERVAL
            self.apply_next_auto_level()
            levels += 1
        return levels
