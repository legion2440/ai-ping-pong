import pygame

if __package__:
    from .utils import PADDLE_W, PADDLE_H
else:
    from utils import PADDLE_W, PADDLE_H


class Paddle:
    """A paddle whose motion is driven either by player input or by a
    simple parameter-based tracking behaviour (stand-in for a GA-evolved bot).
    """

    def __init__(self, x, y, color, speed=420):
        self.x = x
        self.y = y  # center y
        self.color = color
        self.speed = speed

    def rect(self):
        return pygame.Rect(int(self.x - PADDLE_W / 2), int(self.y - PADDLE_H / 2), PADDLE_W, PADDLE_H)

    def clamp(self, top, bottom):
        half = PADDLE_H / 2
        self.y = max(top + half, min(bottom - half, self.y))

    def move_by(self, dy, top, bottom):
        self.y += dy
        self.clamp(top, bottom)

    def track(self, target_y, speed_cap, dt, threshold=8):
        """Move toward target_y capped at speed_cap px/s, ignoring tiny diffs
        (reaction threshold) so movement doesn't jitter.
        """
        diff = target_y - self.y
        if abs(diff) < threshold:
            return
        step = speed_cap * dt
        self.y += max(-step, min(step, diff))

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect(), border_radius=3)
