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
    )


class MatchSimulation:
    def __init__(self):
        self.reset()

    def reset(self):
        cy = COURT_Y + COURT_H / 2
        self.p1 = Paddle(COURT_X + PADDLE_MARGIN, cy, COLORS["cyan"], HUMAN_SPEED)
        self.p2 = Paddle(COURT_X + COURT_W - PADDLE_MARGIN, cy, COLORS["lime"], HUMAN_SPEED)
        self.ball = Ball(COURT_X + COURT_W / 2, cy)
        self.ball.reset(COURT_X + COURT_W / 2, cy)
        self.score1 = 0
        self.score2 = 0

    def step(self, dt):
        self.ball.update(dt, COURT_Y, COURT_Y + COURT_H)

        p1r, p2r, br = self.p1.rect(), self.p2.rect(), self.ball.rect()
        if self.ball.vx < 0 and br.colliderect(p1r):
            self.ball.x = p1r.right + BALL_SIZE / 2
            self.ball.bounce_off_paddle(self.p1.y, 1)
        if self.ball.vx > 0 and br.colliderect(p2r):
            self.ball.x = p2r.left - BALL_SIZE / 2
            self.ball.bounce_off_paddle(self.p2.y, -1)

        if self.ball.x < COURT_X - 30:
            self.score2 += 1
            self.ball.reset(COURT_X + COURT_W / 2, COURT_Y + COURT_H / 2)
        elif self.ball.x > COURT_X + COURT_W + 30:
            self.score1 += 1
            self.ball.reset(COURT_X + COURT_W / 2, COURT_Y + COURT_H / 2)
