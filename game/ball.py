import random

import pygame

if __package__:
    from .utils import BALL_SIZE, COLORS
else:
    from utils import BALL_SIZE, COLORS


class Ball:
    def __init__(self, x, y, vx=0.0, vy=0.0, rng=None):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.rng = rng if rng is not None else random

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

    def bounce_off_paddle(self, paddle_y, direction, speed_mult=1.04, max_speed=680):
        self.vx = direction * min(abs(self.vx) * speed_mult, max_speed)
        offset = self.y - paddle_y
        self.vy = max(-420.0, min(420.0, self.vy + offset * 1.6))

    def reset(self, x, y):
        self.x, self.y = x, y
        direction = self.rng.choice([-1, 1])
        self.vx = 260 * direction
        self.vy = self.rng.uniform(-100, 100)

    def draw(self, surface):
        pygame.draw.circle(surface, COLORS["ball"], (int(self.x), int(self.y)), BALL_SIZE // 2)
