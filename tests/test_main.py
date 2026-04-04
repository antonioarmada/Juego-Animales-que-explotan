import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import pygame

from main import (
    CLOSE_BUTTON_HIT_PADDING,
    CLOSE_BUTTON_MARGIN,
    CLOSE_BUTTON_RADIUS,
    GAME_STATE_START_SCREEN,
    Juego,
    draw_translucent_rounded_panel,
    resolve_session_id,
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


class StartScreenInputBehaviorTest(unittest.TestCase):
    @patch("main.show_windows_touch_keyboard")
    @patch("main.pygame.key.start_text_input")
    def test_click_on_session_input_requests_touch_keyboard(
        self,
        mock_start_text_input,
        mock_show_windows_touch_keyboard,
    ):
        juego = object.__new__(Juego)
        juego.session_input_rect = pygame.Rect(100, 200, 300, 60)

        handled = juego._handle_start_screen_pointer_down((150, 220))

        self.assertTrue(handled)
        mock_start_text_input.assert_called_once_with()
        mock_show_windows_touch_keyboard.assert_called_once_with()

    def test_click_on_continue_button_starts_session(self):
        juego = object.__new__(Juego)
        juego.session_input_rect = pygame.Rect(100, 200, 300, 60)
        juego.session_continue_button_rect = pygame.Rect(420, 200, 180, 60)
        juego._start_session = Mock()

        handled = juego._handle_start_screen_pointer_down((450, 225))

        self.assertTrue(handled)
        juego._start_session.assert_called_once_with()

    def test_textinput_appends_only_supported_characters(self):
        juego = object.__new__(Juego)
        juego.session_id_input = "Paciente"
        juego.input_error = "error previo"

        juego._handle_start_screen_text_input("_01 ñ!")

        self.assertEqual(juego.session_id_input, "Paciente_01")
        self.assertEqual(juego.input_error, "")

    @patch.object(Juego, "_handle_start_screen_pointer_down")
    @patch("main.pygame.event.get")
    def test_fingerdown_uses_scaled_touch_position(
        self,
        mock_event_get,
        mock_handle_pointer_down,
    ):
        juego = object.__new__(Juego)
        juego.state = GAME_STATE_START_SCREEN
        juego.screen_rect = pygame.Rect(0, 0, 1280, 720)
        juego._request_exit = Mock()
        juego._get_close_button_hit_rect = Mock(return_value=pygame.Rect(0, 0, 0, 0))
        mock_event_get.return_value = [
            pygame.event.Event(pygame.FINGERDOWN, {"x": 0.5, "y": 0.25})
        ]

        juego.eventos_loop()

        mock_handle_pointer_down.assert_called_once_with((640, 180))


class SessionIdResolutionTest(unittest.TestCase):
    def test_empty_session_id_generates_timestamped_default(self):
        resolved = resolve_session_id("", now=datetime(2026, 4, 4, 13, 5, 9))

        self.assertEqual(resolved, "sesion_20260404_130509")

    def test_invalid_session_id_raises_error(self):
        with self.assertRaises(ValueError):
            resolve_session_id("paciente invalido")


class TranslucentPanelHelperTest(unittest.TestCase):
    def test_panel_fill_keeps_alpha_and_border_is_opaque(self):
        target = pygame.Surface((120, 100), pygame.SRCALPHA)
        rect = pygame.Rect(10, 10, 80, 60)

        draw_translucent_rounded_panel(
            target,
            rect,
            fill_color=(246, 248, 252, 128),
            border_color=(214, 221, 230),
            border_width=4,
            border_radius=0,
        )

        self.assertEqual(target.get_at((30, 30)), pygame.Color(246, 248, 252, 128))
        self.assertEqual(target.get_at((10, 10)), pygame.Color(214, 221, 230, 255))


if __name__ == "__main__":
    unittest.main()
