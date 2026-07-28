import pygame

from ga.genome import BotGenome

from .utils import COURT_H, COURT_W, COURT_X, COURT_Y

BASELINE_PADDLE_SPEED = 260.0
BASELINE_REACTION_TIME = 0.0
BASELINE_MOVEMENT_THRESHOLD = 8.0


class HumanController:
    def reset(self):
        pass

    def update(self, paddle, ball, dt):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            paddle.move_by(-paddle.speed * dt, COURT_Y, COURT_Y + COURT_H)
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            paddle.move_by(paddle.speed * dt, COURT_Y, COURT_Y + COURT_H)
        mx, my = pygame.mouse.get_pos()
        if pygame.Rect(COURT_X, COURT_Y, COURT_W, COURT_H).collidepoint(mx, my):
            paddle.y = my


class BotController:
    def __init__(self, genome):
        self.genome = genome
        self.reset()

    def reset(self):
        self.target_y = None
        self.elapsed_time = 0.0

    def update(self, paddle, ball, dt):
        if self.target_y is None:
            self.target_y = ball.y
            self.elapsed_time = 0.0
        elif self.genome.reaction_time == 0:
            self.target_y = ball.y
            self.elapsed_time = 0.0
        else:
            self.elapsed_time += dt
            if self.elapsed_time >= self.genome.reaction_time:
                self.target_y = ball.y
                self.elapsed_time = 0.0

        paddle.track(
            self.target_y,
            self.genome.paddle_speed,
            dt,
            self.genome.movement_threshold,
        )


class BaselineController(BotController):
    def __init__(self):
        super().__init__(
            BotGenome(
                paddle_speed=BASELINE_PADDLE_SPEED,
                reaction_time=BASELINE_REACTION_TIME,
                movement_threshold=BASELINE_MOVEMENT_THRESHOLD,
            )
        )
