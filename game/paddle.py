import pygame

if __package__:
    from .utils import PADDLE_W, PADDLE_H
else:
    from utils import PADDLE_W, PADDLE_H


class Paddle:
    """A paddle whose motion is driven either by player input or by a
    simple parameter-based tracking behaviour (stand-in for a GA-evolved bot).
    """

    def __init__(self, x, y, color, speed=420, height=PADDLE_H):
        if isinstance(height, bool) or not isinstance(height, int):
            raise TypeError("height must be an int")
        if height <= 0:
            raise ValueError("height must be positive")
        self.x = x
        self.y = y  # center y
        self.color = color
        self.speed = speed
        self.height = height

    def set_height(self, height):
        if isinstance(height, bool) or not isinstance(height, int):
            raise TypeError("height must be an int")
        if height <= 0:
            raise ValueError("height must be positive")
        if height == self.height:
            return False
        self.height = height
        return True

    def rect(self):
        return pygame.Rect(
            int(self.x - PADDLE_W / 2),
            int(self.y - self.height / 2),
            PADDLE_W,
            self.height,
        )

    def clamp(self, top, bottom):
        half = self.height / 2
        self.y = max(top + half, min(bottom - half, self.y))

    def move_by(self, dy, top, bottom):
        self.y += dy
        self.clamp(top, bottom)

    def track(self, target_y, speed_cap, dt, threshold=8):
        """Move toward target_y capped at speed_cap px/s, ignoring tiny diffs
        (reaction threshold) so movement doesn't jitter.
        """
        diff = target_y - self.y
        if abs(diff) <= threshold:
            return

        remaining = abs(diff) - threshold
        step = min(speed_cap * dt, remaining)
        self.y += step if diff > 0 else -step

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect(), border_radius=3)
