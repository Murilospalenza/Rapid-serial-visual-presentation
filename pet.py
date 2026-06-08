"""
pet.py — Tela de espera com arte ASCII animada
ESP32-2432S028 (Cheap Yellow Display) | MicroPython

Mostra arte ASCII (coruja, gato, robô, etc.) na tela com
animação mínima: piscada do olho e rotação entre artes.
Usa dirty flag para só redesenhar quando muda.
"""

import time
from screen import draw_ascii_art, draw_text_center, ALL_PETS

# ═══ Configuração ════════════════════════════════════════════════

# Lista de pets para ciclar
PET_ORDER = ['owl', 'cat', 'robot', 'fish', 'moon']

# Cores
BG_COLOR      = (10, 10, 30)
PET_COLOR     = (100, 200, 255)   # azul claro
PET_COLOR_ALT = (200, 150, 255)   # roxo (alterna)
TEXT_COLOR    = (150, 150, 180)
ACCENT_COLOR  = (100, 200, 255)

# Timings (ms)
ROTATION_INTERVAL = 5000   # troca de pet a cada 5s
BLINK_INTERVAL    = 2000   # piscada a cada 2s
BLINK_DURATION    = 200    # duração da piscada (olho fechado)


class PetScreen:
    """Tela de espera com arte ASCII. Usa dirty flag para redesenho mínimo."""

    def __init__(self, display, touch):
        self.d = display
        self.touch = touch

        self.pet_index = 0
        self.blink = False
        self.alt_color = False
        self.dirty = True
        self.last_rotation = 0
        self.last_blink = 0
        self.blink_start = 0

        # Estado para navegação
        self.tap_count = 0
        self.tap_window_start = 0
        self.TAP_THRESHOLD = 3
        self.TAP_WINDOW_MS = 1500

    def _draw(self):
        """Redesenha a tela inteira (chamado só quando dirty)."""
        pet_name = PET_ORDER[self.pet_index]
        art = ALL_PETS[pet_name]

        # Fundo
        self.d.fill(BG_COLOR[0], BG_COLOR[1], BG_COLOR[2])

        # Centraliza a arte
        lines = art.split('\n')
        art_h = len(lines)
        art_w = max(len(l) for l in lines)
        pw = art_w * 8 * 2    # escala 2
        ph = art_h * 8 * 2
        x = (self.d.width - pw) // 2
        y = 30

        # Cor do pet (alterna suavemente)
        color = PET_COLOR_ALT if self.alt_color else PET_COLOR

        # Fundo da arte
        self.d.fill_rect(x - 4, y - 4, pw + 8, ph + 8,
                         20, 20, 50)

        # Desenha arte
        draw_ascii_art(self.d, art, x, y, 2, color)

        # Nome do pet
        draw_text_center(self.d, f"~~ {pet_name.upper()} ~~",
                         y + ph + 20, 1, TEXT_COLOR[0], TEXT_COLOR[1],
                         TEXT_COLOR[2])

        # Instrução
        draw_text_center(self.d, "Toque 3x para ler",
                         self.d.height - 30, 1, TEXT_COLOR[0],
                         TEXT_COLOR[1], TEXT_COLOR[2])

        self.dirty = False

    def _blink_effect(self):
        """Pisca os olhos da coruja (desenha traço sobre os olhos)."""
        # Só funciona direito na coruja ('owl')
        if PET_ORDER[self.pet_index] != 'owl':
            return

        # Posição do olho da coruja na arte (escala 2)
        # owl tem olhos nas posições da linha "/ _ \" e "| (_) |"
        # Desenha tracinhos simulando olho fechado
        lines = ALL_PETS['owl'].split('\n')
        art_h = len(lines)
        art_w = max(len(l) for l in lines)
        pw = art_w * 8 * 2
        x = (self.d.width - pw) // 2
        y = 30

        # Posição dos olhos: linha 1, colunas ~4 e ~8
        eye_y = y + 1 * 8 * 2 + 4
        eye_r = x + 4 * 8 * 2
        eye_l = x + 9 * 8 * 2

        if self.blink:
            # Fecha olhos (desenha retângulo da cor do fundo)
            bg = (10, 10, 30)
            self.d.fill_rect(eye_r - 2, eye_y - 2, 6, 6,
                             bg[0], bg[1], bg[2])
            self.d.fill_rect(eye_l - 2, eye_y - 2, 6, 6,
                             bg[0], bg[1], bg[2])
        else:
            # Reabre olhos (redesenha os pixels do olho)
            color = PET_COLOR_ALT if self.alt_color else PET_COLOR
            from screen import draw_char
            # Redesenha os caracteres ( e ) que são os olhos
            draw_char(self.d, eye_r - 4, eye_y - 4, '>', 2,
                      color[0], color[1], color[2])
            draw_char(self.d, eye_l - 4, eye_y - 4, '<', 2,
                      color[0], color[1], color[2])

    def update(self, now_ms):
        """
        Atualiza o estado do pet.
        Retorna 'go_rsvp' se 3 toques detectados, None caso contrário.
        """
        # ── Touch ──────────────────────────────────────────────
        tap = self.touch.read_taps()
        if tap:
            if self.tap_count == 0:
                self.tap_window_start = now_ms
                self.tap_count = 1
            elif now_ms - self.tap_window_start < self.TAP_WINDOW_MS:
                self.tap_count += 1
            else:
                self.tap_window_start = now_ms
                self.tap_count = 1

            if self.tap_count >= self.TAP_THRESHOLD:
                self.tap_count = 0
                return 'go_rsvp'

        # ── Rotação de pet ──────────────────────────────────────
        if now_ms - self.last_rotation > ROTATION_INTERVAL:
            self.pet_index = (self.pet_index + 1) % len(PET_ORDER)
            self.last_rotation = now_ms
            self.dirty = True

        # ── Alternância de cor ──────────────────────────────────
        if now_ms - self.last_rotation > (ROTATION_INTERVAL // 2):
            self.alt_color = not self.alt_color
            self.last_rotation = now_ms
            self.dirty = True

        # ── Piscada ─────────────────────────────────────────────
        if self.blink:
            if now_ms - self.blink_start > BLINK_DURATION:
                self.blink = False
                self._blink_effect()
        elif now_ms - self.last_blink > BLINK_INTERVAL:
            self.blink = True
            self.blink_start = now_ms
            self.last_blink = now_ms
            self._blink_effect()

        # ── Redesenho (só se dirty) ──────────────────────────────
        if self.dirty:
            self._draw()

        return None

    def cleanup(self):
        """Prepara para sair do modo pet."""
        pass