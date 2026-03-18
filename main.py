import random

import pygame

from globales import create_display, load_config, resource_path
from sprite import Sprite


ANIMALES_CONFIG = (
    ("img/perro_sprite.png", "snd/perro.wav", 400, 9),
    ("img/oveja_sprite.png", "snd/oveja.wav", 400, 9),
    ("img/leon_sprite.png", "snd/leon.wav", 400, 9),
    ("img/gallina_sprite.png", "snd/gallo.wav", 400, 9),
    ("img/gato_sprite.png", "snd/gato.wav", 400, 9),
    ("img/elefante_sprite.png", "snd/elefante.wav", 400, 9),
)
EXPLOSION_CONFIG = ("img/explosion_sprite.png", "snd/explosion.wav", 400, 10)
CURSOR_IMAGE_PATH = "img/cursor_varita.png"


class Juego:
    def __init__(self, pantalla, config):
        self.pantalla = pantalla
        self.config = config
        self.screen_rect = pantalla.get_rect()
        self.clock = pygame.time.Clock()
        self.corriendo = True
        self.frame_actual = 0
        self.explotando = False
        self.hover_collision_started_at = None
        self.hover_explode_delay_ms = int(
            float(self.config["hover_explode_delay_seconds"]) * 1000
        )

        self.animales = self._cargar_animales()
        self.explosion = self._crear_sprite(*EXPLOSION_CONFIG)
        self.cursor_image = pygame.image.load(resource_path(CURSOR_IMAGE_PATH)).convert_alpha()
        self.cursor_hotspot = (
            int(self.cursor_image.get_width() * 2 / 3),
            int(self.cursor_image.get_height() * 2 / 3),
        )
        self.index_animal = 0
        self.sprite_actual = self.animales[self.index_animal]
        self.bounding_box = pygame.Rect(
            0, 0, self.sprite_actual.ancho_frame, self.sprite_actual.alto
        )

        fuente = pygame.font.SysFont("Arial", 15)
        self.txt_escape = fuente.render(
            "presionar ESCAPE para salir", True, (150, 150, 150)
        )

        self._iniciar_musica()
        self._mover_animal_actual()

    def _crear_sprite(self, archivo_img, archivo_snd, ancho_frame, cant_frames):
        return Sprite(
            resource_path(archivo_img),
            resource_path(archivo_snd),
            ancho_frame,
            cant_frames,
        )

    def _cargar_animales(self):
        return tuple(self._crear_sprite(*animal_config) for animal_config in ANIMALES_CONFIG)

    def _iniciar_musica(self):
        pygame.mixer.music.load(resource_path("snd/musica.mp3"))
        pygame.mixer.music.set_volume(float(self.config["music_volume"]))
        pygame.mixer.music.play(-1, 0.0)

    def _mover_animal_actual(self):
        max_x = max(0, self.screen_rect.width - self.sprite_actual.ancho_frame)
        max_y = max(0, self.screen_rect.height - self.sprite_actual.alto)
        self.sprite_actual.set_position(
            random.randint(0, max_x),
            random.randint(0, max_y),
        )
        self.bounding_box.topleft = self.sprite_actual.position

    def _avanzar_animal(self):
        self.index_animal = (self.index_animal + 1) % len(self.animales)
        self.sprite_actual = self.animales[self.index_animal]
        self.frame_actual = 0
        self.hover_collision_started_at = None
        self._mover_animal_actual()

    def eventos_loop(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.corriendo = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.corriendo = False

    def hubo_colision(self):
        pygame.mouse.set_pos(0, 0)
        animal_actual = self.sprite_actual
        animal_actual.stop_sound()
        self.explosion.set_position(*animal_actual.position)
        self.sprite_actual = self.explosion
        self.frame_actual = 0
        self.explotando = True
        self.hover_collision_started_at = None

    def logica_loop(self):
        if self.explotando:
            self.hover_collision_started_at = None
            return

        colision = self.bounding_box.collidepoint(pygame.mouse.get_pos())
        if not colision:
            self.hover_collision_started_at = None
            return

        if self.hover_explode_delay_ms == 0:
            self.hubo_colision()
            return

        current_ticks = pygame.time.get_ticks()
        if self.hover_collision_started_at is None:
            self.hover_collision_started_at = current_ticks
            return

        if current_ticks - self.hover_collision_started_at >= self.hover_explode_delay_ms:
            self.hubo_colision()

    def render_loop(self):
        self.pantalla.fill(tuple(self.config["background_color"]))

        if self.frame_actual < self.sprite_actual.cant_frames - 1:
            self.frame_actual += 1
        else:
            self.frame_actual = 0
            if self.explotando:
                self.explotando = False
                self._avanzar_animal()

        self.sprite_actual.draw(self.pantalla, self.frame_actual)
        self.sprite_actual.play_sound()
        self.pantalla.blit(
            self.txt_escape,
            (
                self.screen_rect.centerx - self.txt_escape.get_width() / 2,
                self.screen_rect.height - 30,
            ),
        )
        self._render_cursor()
        pygame.display.flip()

    def _render_cursor(self):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        cursor_pos = (
            mouse_x - self.cursor_hotspot[0],
            mouse_y - self.cursor_hotspot[1],
        )
        self.pantalla.blit(self.cursor_image, cursor_pos)

    def ejecutar(self):
        while self.corriendo:
            self.eventos_loop()
            self.logica_loop()
            self.render_loop()
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
