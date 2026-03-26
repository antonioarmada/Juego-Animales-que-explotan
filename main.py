import random
import re

import pygame

from globales import create_display, load_config, resource_path
from pdf_export import exportar_sesion_a_pdf
from sprite import Sprite
from telemetry import SessionRecorder


ANIMALES_CONFIG = (
    ("perro", "img/perro_sprite.png", "snd/perro.wav", 400, 9),
    ("oveja", "img/oveja_sprite.png", "snd/oveja.wav", 400, 9),
    ("leon", "img/leon_sprite.png", "snd/leon.wav", 400, 9),
    ("gallina", "img/gallina_sprite.png", "snd/gallo.wav", 400, 9),
    ("gato", "img/gato_sprite.png", "snd/gato.wav", 400, 9),
    ("elefante", "img/elefante_sprite.png", "snd/elefante.wav", 400, 9),
)
EXPLOSION_CONFIG = ("img/explosion_sprite.png", "snd/explosion.wav", 400, 10)
CURSOR_IMAGE_PATH = "img/cursor_varita.png"
LOGO_IMAGE_PATH = "img/invoa-blanco-400px.png"
GAME_STATE_START_SCREEN = "start_screen"
GAME_STATE_PLAYING = "playing"
GAME_STATE_FINISHED = "finished"
SAFE_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
MAX_SESSION_ID_LENGTH = 64
TRACE_COLORS = (
    (255, 104, 136),
    (103, 214, 255),
    (255, 206, 84),
    (109, 241, 210),
    (255, 159, 90),
    (200, 148, 255),
    (173, 255, 102),
    (255, 129, 203),
)


def _color_luminance(color):
    red, green, blue = color
    return (0.2126 * red) + (0.7152 * green) + (0.0722 * blue)


def _blend_color(color, target_channel, factor):
    return tuple(
        int(round(channel + ((target_channel - channel) * factor))) for channel in color
    )


def _ensure_color_contrast(color, background_color, min_luminance_delta=92):
    color_luminance = _color_luminance(color)
    background_luminance = _color_luminance(background_color)
    luminance_delta = abs(color_luminance - background_luminance)
    if luminance_delta >= min_luminance_delta:
        return color

    target_channel = 255 if background_luminance < 128 else 0
    factor = min(1.0, ((min_luminance_delta - luminance_delta) / 255) + 0.35)
    return _blend_color(color, target_channel, factor)


class Juego:
    def __init__(self, pantalla, config):
        self.pantalla = pantalla
        self.config = config
        self.screen_rect = pantalla.get_rect()
        self.clock = pygame.time.Clock()
        self.corriendo = True
        self.state = GAME_STATE_START_SCREEN

        self.frame_actual = 0
        self.explotando = False
        self.hover_collision_started_at = None
        self.current_target_started_at = None
        self.hover_explode_delay_ms = int(
            float(self.config["hover_explode_delay_seconds"]) * 1000
        )
        self.time_out_ms = int(float(self.config["time_out_seconds"]) * 1000)
        self.session_target_count = int(self.config["session_target_count"])
        self.show_session_progress = bool(self.config["show_session_progress"])

        self.animales = self._cargar_animales()
        self.explosion = self._crear_sprite(*EXPLOSION_CONFIG)
        self.cursor_image = pygame.image.load(resource_path(CURSOR_IMAGE_PATH)).convert_alpha()
        self.cursor_hotspot = (
            int(self.cursor_image.get_width() * 2 / 3),
            int(self.cursor_image.get_height() * 2 / 3),
        )
        self.logo_image = self._cargar_logo()
        self.report_logo_image = self._cargar_logo(max_width=110)
        self.index_animal = 0
        self.current_animal = self.animales[self.index_animal]
        self.sprite_actual = self.current_animal["sprite"]
        self.bounding_box = pygame.Rect(
            0, 0, self.sprite_actual.ancho_frame, self.sprite_actual.alto
        )
        self.session_recorder = None
        self.attempt_count = 0
        self.completed_target_count = 0
        self.session_id_input = ""
        self.input_error = ""
        self.finished_message = ""
        self.finished_summary = None

        self.title_font = pygame.font.SysFont("Arial", 48)
        self.ui_font = pygame.font.SysFont("Arial", 24)
        self.small_font = pygame.font.SysFont("Arial", 16)
        self.kpi_value_font = pygame.font.SysFont("Arial", 30, bold=True)
        self.kpi_label_font = pygame.font.SysFont("Arial", 14)
        self.txt_escape = self.small_font.render(
            "presionar ESCAPE para salir", True, (150, 150, 150)
        )

        pygame.key.start_text_input()
        self._iniciar_musica()

    def _crear_sprite(self, archivo_img, archivo_snd, ancho_frame, cant_frames):
        return Sprite(
            resource_path(archivo_img),
            resource_path(archivo_snd),
            ancho_frame,
            cant_frames,
        )

    def _cargar_animales(self):
        animales = []
        for animal_id, archivo_img, archivo_snd, ancho_frame, cant_frames in ANIMALES_CONFIG:
            animales.append(
                {
                    "id": animal_id,
                    "sprite": self._crear_sprite(
                        archivo_img, archivo_snd, ancho_frame, cant_frames
                    ),
                }
            )
        return tuple(animales)

    def _iniciar_musica(self):
        pygame.mixer.music.load(resource_path("snd/musica.mp3"))
        pygame.mixer.music.set_volume(float(self.config["music_volume"]))
        pygame.mixer.music.play(-1, 0.0)

    def _cargar_logo(self, max_width=150):
        logo = pygame.image.load(resource_path(LOGO_IMAGE_PATH)).convert_alpha()
        target_max_width = min(max_width, self.screen_rect.width - 160)
        scale = target_max_width / logo.get_width()
        target_size = (
            int(logo.get_width() * scale),
            int(logo.get_height() * scale),
        )
        return pygame.transform.smoothscale(logo, target_size)

    def _mover_animal_actual(self):
        max_x = max(0, self.screen_rect.width - self.sprite_actual.ancho_frame)
        max_y = max(0, self.screen_rect.height - self.sprite_actual.alto)
        self.sprite_actual.set_position(
            random.randint(0, max_x),
            random.randint(0, max_y),
        )
        self.bounding_box.size = (
            self.sprite_actual.ancho_frame,
            self.sprite_actual.alto,
        )
        self.bounding_box.topleft = self.sprite_actual.position

    def _reset_target_state(self):
        self.frame_actual = 0
        self.explotando = False
        self.hover_collision_started_at = None
        self.current_target_started_at = None

    def _spawn_current_target(self, now_ms):
        self.current_animal = self.animales[self.index_animal]
        self.sprite_actual = self.current_animal["sprite"]
        self._reset_target_state()
        self._mover_animal_actual()
        self.current_target_started_at = now_ms
        self.session_recorder.spawn_target(
            target_index=self.attempt_count + 1,
            animal_id=self.current_animal["id"],
            spawn_position=self.sprite_actual.position,
            target_size=(self.sprite_actual.ancho_frame, self.sprite_actual.alto),
            cursor_position=pygame.mouse.get_pos(),
            now_ms=now_ms,
        )

    def _start_session(self):
        session_id = self.session_id_input.strip()
        if not session_id:
            self.input_error = "Ingresa un identificador de sesion."
            return
        if len(session_id) > MAX_SESSION_ID_LENGTH or not SAFE_SESSION_ID_PATTERN.fullmatch(
            session_id
        ):
            self.input_error = "Usa letras, numeros, _ o -."
            return

        self.input_error = ""
        self.state = GAME_STATE_PLAYING
        self.index_animal = 0
        self.attempt_count = 0
        self.completed_target_count = 0
        self.current_animal = self.animales[self.index_animal]
        self.sprite_actual = self.current_animal["sprite"]
        self._reset_target_state()
        pygame.key.stop_text_input()

        now_ms = pygame.time.get_ticks()
        self.session_recorder = SessionRecorder(
            session_id=session_id,
            configured_target_count=self.session_target_count,
            data_output_dir=self.config["data_output_dir"],
            cursor_trace_hz=int(self.config["cursor_trace_hz"]),
        )
        self.session_recorder.start(now_ms=now_ms)
        self._spawn_current_target(now_ms)

    def _finish_session(self, status, now_ms):
        if self.session_recorder is None:
            self.state = GAME_STATE_FINISHED
            self.corriendo = False
            return

        self.session_recorder.finish(status=status, now_ms=now_ms)
        self.finished_summary = self.session_recorder.summary_row
        status_message = (
            "Sesion guardada." if status == "completed" else "Sesion abortada y guardada."
        )
        pdf_message = self._exportar_pdf_automatico()
        self.finished_message = f"{status_message} {pdf_message}".strip()
        self.state = GAME_STATE_FINISHED

    def _advance_target(self, now_ms, completed):
        self.attempt_count += 1
        if completed:
            self.completed_target_count += 1

        if self.attempt_count >= self.session_target_count:
            self._finish_session("completed", now_ms)
            return

        self.index_animal = (self.index_animal + 1) % len(self.animales)
        self._spawn_current_target(now_ms)

    def _request_exit(self):
        now_ms = pygame.time.get_ticks()
        if self.state == GAME_STATE_PLAYING and self.session_recorder is not None:
            self._finish_session("aborted", now_ms)
        else:
            self.corriendo = False

    def _handle_start_screen_keydown(self, event):
        if event.key == pygame.K_ESCAPE:
            self.corriendo = False
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._start_session()
            return
        if event.key == pygame.K_BACKSPACE:
            self.session_id_input = self.session_id_input[:-1]
            self.input_error = ""
            return

        if (
            event.unicode
            and len(self.session_id_input) < MAX_SESSION_ID_LENGTH
            and SAFE_SESSION_ID_PATTERN.fullmatch(event.unicode)
        ):
            self.session_id_input += event.unicode
            self.input_error = ""

    def eventos_loop(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._request_exit()
            elif event.type == pygame.KEYDOWN:
                if self.state == GAME_STATE_START_SCREEN:
                    self._handle_start_screen_keydown(event)
                elif event.key == pygame.K_ESCAPE:
                    self._request_exit()

    def _hover_elapsed_ms(self, now_ms):
        if self.hover_collision_started_at is None:
            return 0
        return max(0, now_ms - self.hover_collision_started_at)

    def _explode_current_target(self, now_ms):
        pygame.mouse.set_pos(0, 0)
        animal_actual = self.current_animal["sprite"]
        animal_actual.stop_sound()
        self.explosion.set_position(*animal_actual.position)
        self.sprite_actual = self.explosion
        self.frame_actual = 0
        self.explotando = True
        self.hover_collision_started_at = None
        self.session_recorder.explode_current_target(now_ms)

    def _expire_current_target(self, now_ms):
        animal_actual = self.current_animal["sprite"]
        animal_actual.stop_sound()
        self.hover_collision_started_at = None
        self.session_recorder.expire_current_target(now_ms)
        self._advance_target(now_ms, completed=False)

    def logica_loop(self, now_ms):
        if self.state != GAME_STATE_PLAYING or self.session_recorder is None:
            return

        if self.explotando:
            self.session_recorder.update_hover_state(False, now_ms)
            return

        mouse_pos = pygame.mouse.get_pos()
        colision = self.bounding_box.collidepoint(mouse_pos)
        self.session_recorder.update_hover_state(colision, now_ms)

        if (
            self.time_out_ms > 0
            and self.current_target_started_at is not None
            and now_ms - self.current_target_started_at >= self.time_out_ms
        ):
            self._expire_current_target(now_ms)
            return

        if not colision:
            self.hover_collision_started_at = None
            return

        if self.hover_explode_delay_ms == 0:
            self._explode_current_target(now_ms)
            return

        if self.hover_collision_started_at is None:
            self.hover_collision_started_at = now_ms
            return

        if now_ms - self.hover_collision_started_at >= self.hover_explode_delay_ms:
            self._explode_current_target(now_ms)

    def _sample_cursor(self, now_ms):
        if self.state != GAME_STATE_PLAYING or self.session_recorder is None:
            return

        self.session_recorder.sample_cursor(
            now_ms=now_ms,
            cursor_position=pygame.mouse.get_pos(),
            on_target=self.bounding_box.collidepoint(pygame.mouse.get_pos()),
            hover_elapsed_ms=self._hover_elapsed_ms(now_ms),
            exploding=self.explotando,
        )

    def _render_start_screen(self):
        self.pantalla.fill(tuple(self.config["background_color"]))
        title = self.title_font.render("Magia en el zoológico", True, (255, 255, 255))
        prompt = self.ui_font.render("Ingresa el ID de la sesion:", True, (220, 220, 220))
        session_text = self.ui_font.render(
            self.session_id_input or "_", True, (255, 230, 160)
        )
        help_text = self.small_font.render(
            "ENTER para comenzar", True, (150, 150, 150)
        )
        logo_y = max(28, self.screen_rect.centery - 225)
        title_y = logo_y + self.logo_image.get_height() + 34
        prompt_y = title_y + 84

        self.pantalla.blit(
            self.logo_image,
            (
                self.screen_rect.centerx - self.logo_image.get_width() / 2,
                logo_y,
            ),
        )
        self.pantalla.blit(
            title,
            (
                self.screen_rect.centerx - title.get_width() / 2,
                title_y,
            ),
        )
        self.pantalla.blit(
            prompt,
            (
                self.screen_rect.centerx - prompt.get_width() / 2,
                prompt_y,
            ),
        )
        self.pantalla.blit(
            session_text,
            (
                self.screen_rect.centerx - session_text.get_width() / 2,
                prompt_y + 40,
            ),
        )
        self.pantalla.blit(
            help_text,
            (
                self.screen_rect.centerx - help_text.get_width() / 2,
                prompt_y + 86,
            ),
        )

        if self.input_error:
            error_text = self.small_font.render(self.input_error, True, (255, 120, 120))
            self.pantalla.blit(
                error_text,
                (
                    self.screen_rect.centerx - error_text.get_width() / 2,
                    prompt_y + 122,
                ),
            )

        self._render_footer()
        self._render_cursor()
        pygame.display.flip()

    def _render_footer(self):
        self.pantalla.blit(
            self.txt_escape,
            (
                self.screen_rect.centerx - self.txt_escape.get_width() / 2,
                self.screen_rect.height - 30,
            ),
        )

    def _render_progress(self):
        if not self.show_session_progress or self.state != GAME_STATE_PLAYING:
            return

        progress_text = self.small_font.render(
            f"Intento {self.attempt_count + 1}/{self.session_target_count}",
            True,
            (220, 220, 220),
        )
        self.pantalla.blit(progress_text, (20, 20))

    def render_loop(self, now_ms):
        if self.state == GAME_STATE_START_SCREEN:
            self._render_start_screen()
            return
        if self.state == GAME_STATE_FINISHED:
            self._render_finished_screen()
            return

        self.pantalla.fill(tuple(self.config["background_color"]))

        if self.frame_actual < self.sprite_actual.cant_frames - 1:
            self.frame_actual += 1
        else:
            self.frame_actual = 0
            if self.explotando:
                self.explotando = False
                self._advance_target(now_ms, completed=True)
                if self.state != GAME_STATE_PLAYING:
                    self._render_finished_screen()
                    return

        self.sprite_actual.draw(self.pantalla, self.frame_actual)
        self.sprite_actual.play_sound()
        self._render_progress()
        self._render_footer()
        self._render_cursor()
        pygame.display.flip()

    def _render_finished_screen(self):
        self.pantalla.fill(tuple(self.config["background_color"]))
        self._draw_trace_background()
        summary = self.finished_summary or {}
        title = self.title_font.render("Resultados de la sesion", True, (255, 255, 255))
        subtitle = self.small_font.render(
            self.finished_message or "Sesion finalizada.", True, (210, 210, 210)
        )
        self.pantalla.blit(
            title,
            (self.screen_rect.centerx - title.get_width() / 2, 40),
        )
        self.pantalla.blit(
            subtitle,
            (self.screen_rect.centerx - subtitle.get_width() / 2, 95),
        )

        kpis = [
            ("Aciertos", self._format_metric_objetivos(summary)),
            (
                "Tiempo medio",
                self._format_metric_seconds(
                    summary, "promedio_tiempo_adquisicion_objetivo_ms"
                ),
            ),
            ("Eficiencia", self._format_metric_ratio(summary, "promedio_eficiencia_trayectoria")),
            (
                "Reingresos promedio",
                self._format_metric_ratio(summary, "promedio_reingresos_hover"),
            ),
        ]
        self._draw_kpi_cards(kpis)

        secundarios = [
            (
                "Rendimiento",
                [
                    ("Estado", summary.get("estado", "-")),
                    (
                        "Tasa de completitud",
                        self._format_metric_percent(summary, "tasa_completitud"),
                    ),
                    (
                        "Mediana tiempo adquisicion",
                        self._format_metric_seconds(
                            summary, "mediana_tiempo_adquisicion_objetivo_ms"
                        ),
                    ),
                    (
                        "Promedio reingresos hover",
                        str(summary.get("promedio_reingresos_hover", "-")),
                    ),
                ],
            ),
            (
                "Sesion",
                [
                    ("Duracion", self._format_metric_seconds(summary, "duracion_sesion_ms")),
                    (
                        "Distancia total",
                        self._format_metric_px(summary, "distancia_total_cursor_px"),
                    ),
                ],
            ),
            (
                "Configuracion",
                [
                    (
                        "Tiempo de Expiracion",
                        f"{float(self.config['time_out_seconds']):.0f} s",
                    ),
                    (
                        "Intentos configurados",
                        str(summary.get("cantidad_objetivos_configurada", "-")),
                    ),
                    ("Aciertos", str(summary.get("cantidad_objetivos_completada", "-"))),
                ],
            ),
        ]
        self._draw_secondary_metrics(secundarios)
        self._draw_report_logo()
        self._render_finished_help()
        self._render_cursor()
        pygame.display.flip()

    def _draw_kpi_cards(self, kpis):
        card_width = 230
        card_height = 126
        gap = 24
        start_x = self.screen_rect.centerx - ((card_width * 2) + gap) / 2
        start_y = 150

        for index, (label, value) in enumerate(kpis):
            row = index // 2
            col = index % 2
            rect = pygame.Rect(
                start_x + col * (card_width + gap),
                start_y + row * (card_height + gap),
                card_width,
                card_height,
            )
            pygame.draw.rect(self.pantalla, (246, 248, 252), rect, border_radius=18)
            pygame.draw.rect(self.pantalla, (214, 221, 230), rect, 2, border_radius=18)
            value_surface = self.kpi_value_font.render(value, True, (26, 32, 44))
            label_surface = self.kpi_label_font.render(label, True, (98, 108, 125))
            content_height = value_surface.get_height() + 14 + label_surface.get_height()
            content_top = rect.y + (rect.height - content_height) / 2
            self.pantalla.blit(
                value_surface,
                (rect.centerx - value_surface.get_width() / 2, content_top),
            )
            self.pantalla.blit(
                label_surface,
                (
                    rect.centerx - label_surface.get_width() / 2,
                    content_top + value_surface.get_height() + 14,
                ),
            )

    def _get_kpi_grid_rect(self):
        card_width = 230
        card_height = 126
        gap = 24
        start_x = self.screen_rect.centerx - ((card_width * 2) + gap) / 2
        start_y = 150
        total_width = (card_width * 2) + gap
        total_height = (card_height * 2) + gap
        return pygame.Rect(start_x, start_y, total_width, total_height)

    def _draw_secondary_metrics(self, secundarios):
        kpi_rect = self._get_kpi_grid_rect()
        max_items = max(len(items) for _, items in secundarios)
        section_title_height = self.small_font.get_height()
        row_height = self.small_font.get_height() + 12
        content_height = 28 + section_title_height + 18 + (max_items * row_height) + 18
        box_rect = pygame.Rect(
            self.screen_rect.centerx - 330,
            kpi_rect.bottom + 22,
            660,
            content_height + 18,
        )
        pygame.draw.rect(self.pantalla, (248, 250, 252), box_rect, border_radius=20)
        pygame.draw.rect(self.pantalla, (214, 221, 230), box_rect, 2, border_radius=18)

        title = self.small_font.render("Indicadores secundarios", True, (70, 78, 92))
        self.pantalla.blit(title, (box_rect.x + 28, box_rect.y + 24))

        column_width = 192
        section_gap = 28
        start_x = box_rect.x + 32
        section_y = box_rect.y + 68

        for section_index, (section_title, items) in enumerate(secundarios):
            section_x = start_x + section_index * (column_width + section_gap)
            section_title_surface = self.small_font.render(
                section_title, True, (70, 78, 92)
            )
            self.pantalla.blit(section_title_surface, (section_x, section_y))

            line_y = section_y + section_title_surface.get_height() + 14
            for label, value in items:
                item_surface = self.small_font.render(
                    f"{label}: {value}", True, (26, 32, 44)
                )
                self.pantalla.blit(item_surface, (section_x, line_y))
                line_y += row_height

                if label == "Finalizada en":
                    line_y += 6

    def _render_finished_help(self):
        help_text = self.small_font.render(
            "ESC cierra la sesion", True, (210, 210, 210)
        )
        self.pantalla.blit(
            help_text,
            (
                self.screen_rect.centerx - help_text.get_width() / 2,
                self.screen_rect.height - 22,
            ),
        )

    def _draw_report_logo(self):
        logo_x = self.screen_rect.centerx - self.report_logo_image.get_width() / 2
        logo_y = self.screen_rect.height - 120
        self.pantalla.blit(self.report_logo_image, (logo_x, logo_y))

    def _exportar_pdf_automatico(self):
        if self.session_recorder is None or self.session_recorder.output_dir is None:
            return ""

        try:
            pdf_path = exportar_sesion_a_pdf(
                directorio_sesion=self.session_recorder.output_dir,
                resumen=self.session_recorder.summary_row or {},
                metricas_objetivos=self.session_recorder.get_target_rows(),
                traza_cursor=self.session_recorder.cursor_trace_rows,
                eventos=self.session_recorder.event_rows,
            )
            return f"PDF exportado en {pdf_path.name}."
        except Exception as exc:
            return f"Error exportando PDF: {exc}."

    def _format_metric_seconds(self, summary, key):
        value = summary.get(key)
        if value is None or value == "":
            return "-"
        return f"{float(value) / 1000:.1f} s"

    def _format_metric_ratio(self, summary, key):
        value = summary.get(key)
        if value is None or value == "":
            return "-"
        return f"{float(value):.2f}"

    def _format_metric_percent(self, summary, key):
        value = summary.get(key)
        if value is None or value == "":
            return "-"
        return f"{float(value) * 100:.1f}%"

    def _format_metric_px(self, summary, key):
        value = summary.get(key)
        if value is None or value == "":
            return "-"
        return f"{float(value):.0f} px"

    def _format_metric_objetivos(self, summary):
        completados = summary.get("cantidad_objetivos_completada")
        configurados = summary.get("cantidad_objetivos_configurada")
        if completados is None or configurados is None:
            return "-"
        return f"{completados}/{configurados}"

    def _draw_trace_background(self):
        if self.session_recorder is None or len(self.session_recorder.cursor_trace_rows) < 2:
            return

        overlay = pygame.Surface(self.screen_rect.size, pygame.SRCALPHA)
        background_color = tuple(self.config["background_color"])
        outline_rgb = (246, 248, 252) if _color_luminance(background_color) < 128 else (15, 23, 42)
        points = [
            (row["x"], row["y"], row["explotando"], row["indice_objetivo"])
            for row in self.session_recorder.cursor_trace_rows
        ]
        for index in range(1, len(points)):
            start_x, start_y, _, start_attempt = points[index - 1]
            end_x, end_y, exploding, end_attempt = points[index]
            if start_attempt != end_attempt:
                continue
            base_color = TRACE_COLORS[(max(1, end_attempt) - 1) % len(TRACE_COLORS)]
            trace_rgb = _ensure_color_contrast(base_color, background_color)
            outline_alpha = 150 if exploding else 118
            trace_alpha = 210 if exploding else 170
            pygame.draw.line(
                overlay,
                (*outline_rgb, outline_alpha),
                (start_x, start_y),
                (end_x, end_y),
                7,
            )
            pygame.draw.line(
                overlay,
                (*trace_rgb, trace_alpha),
                (start_x, start_y),
                (end_x, end_y),
                5,
            )

        self.pantalla.blit(overlay, (0, 0))

    def _render_cursor(self):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        cursor_pos = (
            mouse_x - self.cursor_hotspot[0],
            mouse_y - self.cursor_hotspot[1],
        )
        self.pantalla.blit(self.cursor_image, cursor_pos)

    def ejecutar(self):
        while self.corriendo:
            now_ms = pygame.time.get_ticks()
            self.eventos_loop()
            self.logica_loop(now_ms)
            self._sample_cursor(now_ms)
            self.render_loop(now_ms)
            self.clock.tick(int(self.config["fps"]))


def main():
    pygame.init()
    pygame.mixer.init()

    config = load_config()
    pantalla = create_display(config)

    try:
        juego = Juego(pantalla, config)
        juego.ejecutar()
    finally:
        pygame.mixer.music.stop()
        pygame.quit()


if __name__ == "__main__":
    main()
