import pygame


class Sprite:
    def __init__(self, archivo_img, archivo_snd, ancho_frame, cant_frames):
        self.imagen = pygame.image.load(archivo_img).convert_alpha()
        self.ancho, self.alto = self.imagen.get_size()
        self.ancho_frame = ancho_frame
        self.cant_frames = cant_frames
        self.sonido = pygame.mixer.Sound(archivo_snd)
        self.sound_channel = None
        self.pos_x = 0
        self.pos_y = 0

    @property
    def position(self):
        return (self.pos_x, self.pos_y)

    def set_position(self, x, y):
        self.pos_x = x
        self.pos_y = y

    def draw(self, pantalla, frame):
        pantalla.blit(
            self.imagen,
            self.position,
            (self.ancho_frame * frame, 0, self.ancho_frame, self.alto),
        )

    def play_sound(self):
        if self.sound_channel is None or not self.sound_channel.get_busy():
            self.sound_channel = self.sonido.play()

    def stop_sound(self):
        if self.sound_channel is not None and self.sound_channel.get_busy():
            self.sound_channel.fadeout(300)
