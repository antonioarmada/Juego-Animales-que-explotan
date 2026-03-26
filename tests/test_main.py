import unittest

import pygame

from main import (
    CLOSE_BUTTON_HIT_PADDING,
    CLOSE_BUTTON_MARGIN,
    CLOSE_BUTTON_RADIUS,
    Juego,
)


class CloseButtonLayoutTest(unittest.TestCase):
    def test_close_button_hitbox_stays_in_corner_and_exceeds_visual_size(self):
        juego = object.__new__(Juego)
        juego.screen_rect = pygame.Rect(0, 0, 1280, 720)

        visual_rect = juego._get_close_button_visual_rect()
        hit_rect = juego._get_close_button_hit_rect()

        self.assertEqual(
            visual_rect,
            pygame.Rect(
                1280 - CLOSE_BUTTON_MARGIN - (CLOSE_BUTTON_RADIUS * 2),
                CLOSE_BUTTON_MARGIN,
                CLOSE_BUTTON_RADIUS * 2,
                CLOSE_BUTTON_RADIUS * 2,
            ),
        )
        self.assertEqual(
            hit_rect.size,
            (
                visual_rect.width + (CLOSE_BUTTON_HIT_PADDING * 2),
                visual_rect.height + (CLOSE_BUTTON_HIT_PADDING * 2),
            ),
        )
        self.assertTrue(hit_rect.contains(visual_rect))


if __name__ == "__main__":
    unittest.main()
