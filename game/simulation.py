import math
from dataclasses import dataclass

if __package__:
    from .ball import Ball
    from .paddle import Paddle
    from .utils import (
        BALL_SIZE,
        COLORS,
        COURT_H,
        COURT_W,
        COURT_X,
        COURT_Y,
        HUMAN_SPEED,
        PADDLE_MARGIN,
        PADDLE_W,
    )
else:
    from ball import Ball
    from paddle import Paddle
    from utils import (
        BALL_SIZE,
        COLORS,
        COURT_H,
        COURT_W,
        COURT_X,
        COURT_Y,
        HUMAN_SPEED,
        PADDLE_MARGIN,
        PADDLE_W,
    )


@dataclass(frozen=True, slots=True)
class StepEvents:
    left_return: bool = False
    right_return: bool = False
    point_winner: str | None = None


class MatchSimulation:
    def __init__(self, rng=None):
        self.rng = rng
        self.reset()

    def reset(self):
        cy = COURT_Y + COURT_H / 2
        self.p1 = Paddle(COURT_X + PADDLE_MARGIN, cy, COLORS["cyan"], HUMAN_SPEED)
        self.p2 = Paddle(COURT_X + COURT_W - PADDLE_MARGIN, cy, COLORS["lime"], HUMAN_SPEED)
        self.ball = Ball(COURT_X + COURT_W / 2, cy, rng=self.rng)
        self.ball.reset(COURT_X + COURT_W / 2, cy)
        self.score1 = 0
        self.score2 = 0

    def step(self, dt):
        collision_zone = PADDLE_W + BALL_SIZE
        horizontal_distance = abs(self.ball.vx) * dt
        if horizontal_distance < collision_zone:
            return self._step_once(dt)

        substeps = max(
            1,
            math.ceil(horizontal_distance / (collision_zone / 2)),
        )
        sub_dt = dt / substeps
        left_return = False
        right_return = False

        for _ in range(substeps):
            events = self._step_once(sub_dt)
            left_return = left_return or events.left_return
            right_return = right_return or events.right_return
            if events.point_winner is not None:
                return StepEvents(
                    left_return=left_return,
                    right_return=right_return,
                    point_winner=events.point_winner,
                )

        return StepEvents(
            left_return=left_return,
            right_return=right_return,
        )

    def _step_once(self, dt):
        left_return = False
        right_return = False
        point_winner = None

        self.ball.update(dt, COURT_Y, COURT_Y + COURT_H)

        p1r, p2r, br = self.p1.rect(), self.p2.rect(), self.ball.rect()
        if self.ball.vx < 0 and br.colliderect(p1r):
            self.ball.x = p1r.right + BALL_SIZE / 2
            self.ball.bounce_off_paddle(self.p1.y, 1)
            left_return = True
        if self.ball.vx > 0 and br.colliderect(p2r):
            self.ball.x = p2r.left - BALL_SIZE / 2
            self.ball.bounce_off_paddle(self.p2.y, -1)
            right_return = True

        if self.ball.x < COURT_X - 30:
            self.score2 += 1
            self.ball.reset(COURT_X + COURT_W / 2, COURT_Y + COURT_H / 2)
            point_winner = "right"
        elif self.ball.x > COURT_X + COURT_W + 30:
            self.score1 += 1
            self.ball.reset(COURT_X + COURT_W / 2, COURT_Y + COURT_H / 2)
            point_winner = "left"

        return StepEvents(
            left_return=left_return,
            right_return=right_return,
            point_winner=point_winner,
        )
