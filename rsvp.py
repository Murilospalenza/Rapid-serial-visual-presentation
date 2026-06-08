"""
rsvp.py — Modo de leitura RSVP (Rapid Serial Visual Presentation)
ESP32-2432S028 (Cheap Yellow Display) | MicroPython

Mostra palavras uma por uma no centro da tela, com timing
calculado baseado no comprimento e pontuação.
Usa dirty flag — só redesenha quando muda de palavra.
"""

import time
from screen import draw_text_center

# ═══ Configuração ════════════════════════════════════════════════

DEFAULT_WPM    = 300       # palavras por minuto
WPM_ADJUST     = 20        # incremento ao tocar no RSVP

# Cores
BG      = (0, 0, 0)
TEXT    = (220, 220, 220)
ACCENT  = (100, 200, 255)
DIM     = (60, 60, 60)


class RSVPScreen:
    """
    Leitura RSVP non-blocking.
    Usa time.ticks_ms() + ticks_diff() para controle de timing.
    """

    def __init__(self, display, touch):
        self.d = display
        self.touch = touch

        self.words = []
        self.word_index = 0
        self.paused = False
        self.finished = False

        self.wpm = DEFAULT_WPM
        self._base_delay_ms = 60000 // self.wpm
        self.last_advance = 0
        self.last_word = ""

        # Touch
        self._last_tap = 0
        self._last_press = False
        self.debounce_ms = 300

    def load_text(self, text):
        """Carrega um texto para leitura."""
        self.words = text.replace('\n', ' ').split()
        self.word_index = 0
        self.paused = False
        self.finished = False
        self.last_advance = 0

    def _word_duration_ms(self, word):
        """
        Calcula o tempo que uma palavra deve ficar na tela.
        Leva em conta comprimento e pontuação final.
        """
        duration = self._base_delay_ms

        # Palavras longas ganham mais tempo
        if len(word) > 6:
            duration += int(self._base_delay_ms * 0.3)
        if len(word) > 10:
            duration += int(self._base_delay_ms * 0.2)

        # Pontuação final = pausa maior
        if word and word[-1] in '.!?':
            duration += int(self._base_delay_ms * 0.5)
        elif word and word[-1] in ',;:':
            duration += int(self._base_delay_ms * 0.2)

        return max(duration, 80)  # mínimo 80ms

    def _show_word(self):
        """Desenha a palavra atual na tela."""
        if self.word_index >= len(self.words):
            self._show_finish()
            return

        word = self.words[self.word_index]
        self.last_word = word

        # Limpa tela
        self.d.fill(BG[0], BG[1], BG[2])

        # Palavra centralizada (grande)
        draw_text_center(self.d, word,
                         self.d.height // 2 - 20, 3,
                         TEXT[0], TEXT[1], TEXT[2])

        # Progresso no rodapé
        progress = f"{self.word_index + 1} / {len(self.words)}"
        draw_text_center(self.d, progress,
                         self.d.height - 30, 1,
                         DIM[0], DIM[1], DIM[2])

        # Instrução
        if self.paused:
            draw_text_center(self.d, "[PAUSADO] toque para continuar",
                             self.d.height - 50, 1, ACCENT[0], ACCENT[1],
                             ACCENT[2])

    def _show_finish(self):
        """Tela de fim de leitura."""
        self.d.fill(BG[0], BG[1], BG[2])
        draw_text_center(self.d, "Fim da leitura!",
                         self.d.height // 2 - 30, 2,
                         ACCENT[0], ACCENT[1], ACCENT[2])
        draw_text_center(self.d, "Toque para voltar",
                         self.d.height // 2 + 10, 1,
                         DIM[0], DIM[1], DIM[2])

    def _handle_tap(self, now_ms):
        """Processa toque: pausa/continua, ou volta."""
        if self.finished:
            return 'back_to_pet'

        self.paused = not self.paused
        if not self.paused:
            # Ao despausar, reseta o timer da palavra atual
            self.last_advance = now_ms
            # Redesenha para tirar o [PAUSADO]
            self._show_word()

        return None

    def set_wpm(self, wpm):
        """Ajusta palavras por minuto."""
        self.wpm = max(100, min(1000, wpm))
        self._base_delay_ms = 60000 // self.wpm

    def update(self, now_ms):
        """
        Atualiza o estado da leitura.
        Retorna None normalmente, 'back_to_pet' se terminou/usuário saiu.
        """
        # ── Touch ──────────────────────────────────────────────
        tap = self.touch.read_taps()
        if tap:
            if now_ms - self._last_tap > self.debounce_ms:
                self._last_tap = now_ms
                result = self._handle_tap(now_ms)
                if result:
                    return result
                # Se despausou, o redesenho já foi feito

        # ── Se pausado ou terminou, não avança ─────────────────
        if self.paused or self.finished:
            return None

        # ── Verifica se é hora de avançar ──────────────────────
        if self.word_index >= len(self.words):
            self.finished = True
            self._show_finish()
            return None

        word = self.words[self.word_index]
        duration = self._word_duration_ms(word)

        if now_ms - self.last_advance >= duration:
            self.word_index += 1
            self.last_advance = now_ms

            if self.word_index >= len(self.words):
                self.finished = True
                self._show_finish()
            else:
                self._show_word()

        return None

    def cleanup(self):
        """Prepara para sair do modo leitura."""
        pass