import unittest
from unittest.mock import Mock, patch

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
        juego.ui_scale = 1.5

        visual_rect = juego._get_close_button_visual_rect()
        hit_rect = juego._get_close_button_hit_rect()
        scaled_margin = juego._ui(CLOSE_BUTTON_MARGIN)
        scaled_radius = juego._ui(CLOSE_BUTTON_RADIUS)
        scaled_hit_padding = juego._ui(CLOSE_BUTTON_HIT_PADDING)

        self.assertEqual(
            visual_rect,
            pygame.Rect(
                1280 - scaled_margin - (scaled_radius * 2),
                scaled_margin,
                scaled_radius * 2,
                scaled_radius * 2,
            ),
        )
        self.assertEqual(
            hit_rect.size,
            (
                visual_rect.width + (scaled_hit_padding * 2),
                visual_rect.height + (scaled_hit_padding * 2),
            ),
        )
        self.assertTrue(hit_rect.contains(visual_rect))


class ExplosionMouseBehaviorTest(unittest.TestCase):
    @patch("main.pygame.mouse.set_pos")
    def test_explosion_does_not_reposition_mouse(self, mock_set_pos):
        juego = object.__new__(Juego)
        animal_sprite = Mock()
        animal_sprite.position = (120, 240)
        juego.current_animal = {"sprite": animal_sprite}
        juego.explosion = Mock()
        juego.session_recorder = Mock()
        juego.hover_collision_started_at = 123

        juego._explode_current_target(500)

        mock_set_pos.assert_not_called()
        animal_sprite.stop_sound.assert_called_once_with()
        juego.explosion.set_position.assert_called_once_with(120, 240)
        juego.session_recorder.explode_current_target.assert_called_once_with(500)
        self.assertIs(juego.sprite_actual, juego.explosion)
        self.assertEqual(juego.frame_actual, 0)
        self.assertTrue(juego.explotando)
        self.assertIsNone(juego.hover_collision_started_at)


if __name__ == "__main__":
    unittest.main()
