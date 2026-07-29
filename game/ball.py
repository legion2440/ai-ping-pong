import math
import random
from numbers import Real

import pygame

if __package__:
    from .utils import BALL_SIZE, COLORS
else:
    from utils import BALL_SIZE, COLORS


class Ball:
    def __init__(
        self,
        x,
        y,
        vx=0.0,
        vy=0.0,
        rng=None,
        speed_multiplier=1.0,
    ):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.rng = rng if rng is not None else random
        self.speed_multiplier = self._validate_speed_multiplier(
            speed_multiplier
        )

    @staticmethod
    def _validate_speed_multiplier(value):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError("speed_multiplier must be a real number")
        value = float(value)
        if not math.isfinite(value) or value <= 0:
            raise ValueError(
                "speed_multiplier must be a finite positive number"
            )
        return value

    def set_speed_multiplier(self, multiplier):
        multiplier = self._validate_speed_multiplier(multiplier)
        if multiplier == self.speed_multiplier:
            return False

        ratio = multiplier / self.speed_multiplier
        self.vx *= ratio
        self.vy *= ratio
        self.speed_multiplier = multiplier
        return True

    def rect(self):
        return pygame.Rect(int(self.x - BALL_SIZE / 2), int(self.y - BALL_SIZE / 2), BALL_SIZE, BALL_SIZE)

    def update(self, dt, top, bottom):
        self.x += self.vx * dt
        self.y += self.vy * dt
        half = BALL_SIZE / 2
        if self.y - half <= top:
            self.y = top + half
            self.vy = abs(self.vy)
        if self.y + half >= bottom:
            self.y = bottom - half
            self.vy = -abs(self.vy)

    def bounce_off_paddle(
        self,
        paddle_y,
        direction,
        bounce_factor=1.04,
        max_speed=680,
    ):
        if self.speed_multiplier == 1.0:
            self.vx = direction * min(
                abs(self.vx) * bounce_factor,
                max_speed,
            )
            offset = self.y - paddle_y
            self.vy = max(
                -420.0,
                min(420.0, self.vy + offset * 1.6),
            )
            return

        horizontal_cap = max_speed * self.speed_multiplier
        vertical_cap = 420.0 * self.speed_multiplier
        self.vx = direction * min(
            abs(self.vx) * bounce_factor,
            horizontal_cap,
        )
        offset = self.y - paddle_y
        vertical_impulse = offset * 1.6 * self.speed_multiplier
        self.vy = max(
            -vertical_cap,
            min(vertical_cap, self.vy + vertical_impulse),
        )

    def reset(self, x, y):
        self.x, self.y = x, y
        direction = self.rng.choice([-1, 1])
        if self.speed_multiplier == 1.0:
            self.vx = 260 * direction
            self.vy = self.rng.uniform(-100, 100)
        else:
            self.vx = 260 * direction * self.speed_multiplier
            self.vy = (
                self.rng.uniform(-100, 100)
                * self.speed_multiplier
            )

    def draw(self, surface):
        pygame.draw.circle(surface, COLORS["ball"], (int(self.x), int(self.y)), BALL_SIZE // 2)
