"""
touch_test.py — Diagnóstico do Touch XPT2046
ESP32-2432S028 (Cheap Yellow Display) | MicroPython

Mostra na tela:
  - Círculo vermelho quando NÃO tocado
  - Círculo verde quando tocado
  - Coordenadas XY do toque (se conseguir ler)
  - Estado do pino IRQ

NÃO depende de boot.py nem screen.py — é 100% autocontido.
Basta enviar este ÚNICO arquivo para o ESP32 e apertar RST.

Como usar:
  rshell -p /dev/ttyUSB0 cp touch_test.py /pyboard/main.py
  (aperte RST manualmente após o upload)
"""

import time
import struct
import machine


# ═══════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DE PINOS
# ═══════════════════════════════════════════════════════════════════

PIN_SCK     = 14
PIN_MOSI    = 13
PIN_DC      = 2
PIN_CS      = 15
PIN_RST     = 12
PIN_BL      = 21

PIN_T_IRQ   = 36
PIN_T_CS    = 33

WIDTH       = 240
HEIGHT      = 320
SPI_BAUD    = 40_000_000

# ═══════════════════════════════════════════════════════════════════
# INICIALIZAÇÃO DO DISPLAY (cópia inline do boot.py)
# ═══════════════════════════════════════════════════════════════════

def _cmd(spi, dc, cs, c):
    dc.value(0); cs.value(0)
    spi.write(bytes([c]))
    cs.value(1)

def _dat(spi, dc, cs, d):
    dc.value(1); cs.value(0)
    spi.write(d if isinstance(d, (bytes, bytearray)) else bytes([d]))
    cs.value(1)

def init_display():
    spi = machine.SPI(1, baudrate=SPI_BAUD, polarity=0, phase=0,
                      sck=machine.Pin(PIN_SCK), mosi=machine.Pin(PIN_MOSI))
    dc  = machine.Pin(PIN_DC,  machine.Pin.OUT)
    cs  = machine.Pin(PIN_CS,  machine.Pin.OUT)
    rst = machine.Pin(PIN_RST, machine.Pin.OUT)
    bl  = machine.Pin(PIN_BL,  machine.Pin.OUT)
    cs.value(1)
    bl.value(1)

    # Reset
    rst.value(0); time.sleep_ms(50)
    rst.value(1); time.sleep_ms(100)

    # Init sequence (ILI9341 / ST7789 compatible)
    _cmd(spi, dc, cs, 0x01); time.sleep_ms(100)
    _cmd(spi, dc, cs, 0x11); time.sleep_ms(100)
    _cmd(spi, dc, cs, 0x3A); _dat(spi, dc, cs, 0x55)
    _cmd(spi, dc, cs, 0x36); _dat(spi, dc, cs, 0x08)
    _cmd(spi, dc, cs, 0x29); time.sleep_ms(50)

    print("[touch_test] Display OK")
    return spi, dc, cs


# ═══════════════════════════════════════════════════════════════════
# DISPLAY WRAPPER
# ═══════════════════════════════════════════════════════════════════

class Display:
    def __init__(self, spi, dc, cs):
        self.spi = spi
        self.dc = dc
        self.cs = cs
        self.width = WIDTH
        self.height = HEIGHT

    def _win(self, x0, y0, x1, y1):
        _cmd(self.spi, self.dc, self.cs, 0x2A)
        _dat(self.spi, self.dc, self.cs, struct.pack(">HH", x0, x1))
        _cmd(self.spi, self.dc, self.cs, 0x2B)
        _dat(self.spi, self.dc, self.cs, struct.pack(">HH", y0, y1))
        _cmd(self.spi, self.dc, self.cs, 0x2C)

    def fill(self, r, g, b):
        c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        px = struct.pack(">H", c)
        chunk = px * 64
        total = WIDTH * HEIGHT
        n, rem = divmod(total, 64)
        self._win(0, 0, WIDTH - 1, HEIGHT - 1)
        self.dc.value(1); self.cs.value(0)
        for _ in range(n):
            self.spi.write(chunk)
        if rem:
            self.spi.write(px * rem)
        self.cs.value(1)

    def fill_rect(self, x, y, w, h, r, g, b):
        if x < 0: w += x; x = 0
        if y < 0: h += y; y = 0
        if x + w > WIDTH:  w = WIDTH - x
        if y + h > HEIGHT: h = HEIGHT - y
        if w <= 0 or h <= 0:
            return
        c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        px = struct.pack(">H", c)
        row = px * w
        self._win(x, y, x + w - 1, y + h - 1)
        self.dc.value(1); self.cs.value(0)
        for _ in range(h):
            self.spi.write(row)
        self.cs.value(1)


# ═══════════════════════════════════════════════════════════════════
# FONTE MÍNIMA (só dígitos e letras que precisamos)
# ═══════════════════════════════════════════════════════════════════

FONT6 = {
    '0': (0x3C,0x46,0x4A,0x52,0x62,0x3C), '1': (0x18,0x38,0x18,0x18,0x18,0x7E),
    '2': (0x3C,0x42,0x0C,0x30,0x40,0x7E), '3': (0x3C,0x42,0x1C,0x02,0x42,0x3C),
    '4': (0x08,0x18,0x28,0x48,0x7E,0x08), '5': (0x7E,0x40,0x7C,0x02,0x42,0x3C),
    '6': (0x3C,0x40,0x7C,0x42,0x42,0x3C), '7': (0x7E,0x02,0x04,0x08,0x10,0x10),
    '8': (0x3C,0x42,0x3C,0x42,0x42,0x3C), '9': (0x3C,0x42,0x3E,0x02,0x42,0x3C),
    ' ': (0,0,0,0,0,0),
    'T': (0x7E,0x18,0x18,0x18,0x18,0x18), 'O': (0x3C,0x42,0x42,0x42,0x42,0x3C),
    'U': (0x42,0x42,0x42,0x42,0x42,0x3C), 'C': (0x3C,0x42,0x40,0x40,0x42,0x3C),
    'H': (0x42,0x42,0x7E,0x42,0x42,0x42), 'E': (0x7E,0x40,0x7C,0x40,0x40,0x7E),
    'D': (0x78,0x44,0x42,0x42,0x44,0x78), 'N': (0x42,0x62,0x52,0x4A,0x46,0x42),
    'S': (0x3C,0x42,0x30,0x0C,0x42,0x3C), 'R': (0x7C,0x42,0x7C,0x44,0x42,0x42),
    'P': (0x7C,0x42,0x7C,0x40,0x40,0x40), 'X': (0x42,0x24,0x18,0x18,0x24,0x42),
    'Y': (0x42,0x24,0x18,0x18,0x18,0x18), ':': (0,0x18,0,0,0x18,0),
    '/': (0x02,0x04,0x08,0x10,0x20,0x40), 'A': (0x18,0x24,0x42,0x7E,0x42,0x42),
    'G': (0x3C,0x42,0x40,0x4E,0x42,0x3C), '.': (0,0,0,0,0,0x18),
    '-': (0,0,0x7E,0,0,0), 'I': (0x7E,0x18,0x18,0x18,0x18,0x7E),
    'Q': (0x3C,0x42,0x42,0x4A,0x44,0x3A), 'B': (0x7C,0x42,0x7C,0x42,0x42,0x7C),
    'F': (0x7E,0x40,0x7C,0x40,0x40,0x40), 'L': (0x40,0x40,0x40,0x40,0x40,0x7E),
    '!': (0x18,0x18,0x18,0x18,0x00,0x18), 'V': (0x42,0x42,0x42,0x42,0x24,0x18),
}

def draw_text(d, text, x, y, scale, r, g, b):
    cx, cy = x, y
    for c in text:
        if c == '\n':
            cx, cy = x, cy + 8 * scale + 2
            continue
        bitmap = FONT6.get(c, FONT6.get(c.upper(), (0,)*6))
        for row in range(6):
            bits = bitmap[row]
            for col in range(8):
                if bits & (0x80 >> col):
                    d.fill_rect(cx + col * scale, cy + row * scale,
                                scale, scale, r, g, b)
        cx += 8 * scale


def draw_circle(d, cx, cy, r, color):
    for dy in range(-r, r + 1):
        half = int((r * r - dy * dy) ** 0.5)
        if half:
            d.fill_rect(cx - half, cy + dy, half * 2 + 1, 1,
                        color[0], color[1], color[2])


# ═══════════════════════════════════════════════════════════════════
# LEITURA DO TOUCH XPT2046
# ═══════════════════════════════════════════════════════════════════

def read_xpt2046_raw(spi, cs, channel):
    """Lê ADC do XPT2046: channel=1 → X, channel=0 → Y. Retorna 12-bit."""
    cs.value(0)
    cmd = 0x90 | (channel << 4)
    spi.write(bytes([cmd]))
    raw = spi.read(2)
    cs.value(1)
    if len(raw) == 2:
        return ((raw[0] << 8) | raw[1]) >> 3
    return 0


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    print("=== Touch Test CYD (autocontido) ===")

    # Inicializa display
    try:
        spi, dc, cs = init_display()
        d = Display(spi, dc, cs)
    except Exception as e:
        print(f"Falha no display: {e}")
        return

    # Inicializa touch (usa a mesma SPI do display)
    irq = machine.Pin(PIN_T_IRQ, machine.Pin.IN, machine.Pin.PULL_UP)
    cs_touch = machine.Pin(PIN_T_CS, machine.Pin.OUT)
    cs_touch.value(1)

    cx, cy = WIDTH // 2, HEIGHT // 2 - 30
    dot_r = 40
    last_touched = False
    press_count = 0
    frame = 0

    # Dirty flag: só redesenhando quando o estado muda
    last_state = None  # 'touched' ou 'released'
    dirty = True

    # Coordenadas guardadas (última leitura)
    last_xr, last_yr = 0, 0

    print("Encoste na tela! IRQ=0 → tocado")

    # Primeira renderização estática
    d.fill(5, 5, 15)
    draw_circle(d, cx, cy, dot_r, (220, 40, 40))  # vermelho inicial
    draw_text(d, "SOLTO", cx - 40, cy - 4, 2, 200, 200, 200)
    draw_text(d, "IRQ=1", 20, cy + dot_r + 24, 1, 200, 200, 200)
    draw_text(d, "--- livre ---", 20, cy + dot_r + 36, 1, 180, 180, 100)
    draw_text(d, "Toques: 0", 20, cy + dot_r + 48, 1, 100, 200, 255)
    draw_text(d, "Encoste na tela", 20, cy + dot_r + 60, 1, 100, 100, 100)

    while True:
        irq_val = irq.value()
        is_touched = (irq_val == 0)

        # Nova borda de descida/subida?
        state_changed = False
        current_state = 'touched' if is_touched else 'released'
        if current_state != last_state:
            state_changed = True
            last_state = current_state
            dirty = True

            if is_touched:
                press_count += 1
                # Lê coordenadas na hora do toque
                last_xr = read_xpt2046_raw(spi, cs_touch, 1)
                last_yr = read_xpt2046_raw(spi, cs_touch, 0)

        frame += 1

        # ── Se não mudou, NÃO mexe na tela ──────────────────
        if not dirty:
            time.sleep_ms(50)
            continue

        # ── Redesenha só o que mudou ────────────────────────
        if is_touched:
            dot_color = (0, 220, 0)
            xs = (last_xr * WIDTH) // 4095
            ys = (last_yr * HEIGHT) // 4095
            coord = f"X:{last_xr:4d}({xs:3d}) Y:{last_yr:4d}({ys:3d})"
            status = "TOCADO!"
        else:
            dot_color = (220, 40, 40)
            coord = "--- livre ---"
            status = "SOLTO"

        # Círculo (só ele muda de cor)
        draw_circle(d, cx, cy, dot_r, dot_color)

        # Status no centro (limpa antes)
        d.fill_rect(cx - 44, cy - 6, 88, 12, 5, 5, 15)
        draw_text(d, status, cx - 40, cy - 4, 2,
                  255 if is_touched else 200,
                  255 if is_touched else 200,
                  255 if is_touched else 200)

        # Coordenadas (limpa antes)
        info_y = cy + dot_r + 24
        if is_touched:
            d.fill_rect(20, info_y + 12, 200, 12, 5, 5, 15)
            draw_text(d, coord, 20, info_y + 12, 1, 180, 180, 100)

        # IRQ
        d.fill_rect(20, info_y, 80, 12, 5, 5, 15)
        draw_text(d, f"IRQ={irq_val}", 20, info_y, 1, 200, 200, 200)

        # Toques
        d.fill_rect(20, info_y + 24, 120, 12, 5, 5, 15)
        draw_text(d, f"Toques: {press_count}", 20, info_y + 24, 1, 100, 200, 255)

        dirty = False
        time.sleep_ms(50)


main()