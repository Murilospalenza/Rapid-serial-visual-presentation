"""
boot.py — Inicialização do hardware (SPI, display, touch)
ESP32-2432S028 (Cheap Yellow Display) | MicroPython

Separa toda a configuração de hardware do resto do código.
Chamado por main.py para obter objetos spi, dc, cs, touch.
"""

import machine
import time
import struct

# ═══ Configuração de pinos ══════════════════════════════════════

PIN_SCK   = 14
PIN_MOSI  = 13
PIN_DC    = 2
PIN_CS    = 15
PIN_RST   = 12
PIN_BL    = 21

PIN_T_IRQ = 36    # Touch IRQ
PIN_T_CS  = 33    # Touch Chip Select

WIDTH        = 240
HEIGHT       = 320
SPI_BAUDRATE = 40_000_000
SPI_ID       = 1

# ═══ Funções internas do display ═══════════════════════════════


def _init_spi():
    return machine.SPI(
        SPI_ID, baudrate=SPI_BAUDRATE,
        polarity=0, phase=0,
        sck=machine.Pin(PIN_SCK),
        mosi=machine.Pin(PIN_MOSI),
    )


def _init_pins():
    dc = machine.Pin(PIN_DC, machine.Pin.OUT)
    cs = machine.Pin(PIN_CS, machine.Pin.OUT)
    rst = machine.Pin(PIN_RST, machine.Pin.OUT)
    bl = machine.Pin(PIN_BL, machine.Pin.OUT)
    cs.value(1)
    bl.value(1)
    return dc, cs, rst


def _cmd(spi, dc, cs, c):
    dc.value(0)
    cs.value(0)
    spi.write(bytes([c]))
    cs.value(1)


def _dat(spi, dc, cs, d):
    dc.value(1)
    cs.value(0)
    spi.write(d if isinstance(d, (bytes, bytearray)) else bytes([d]))
    cs.value(1)


def _hard_reset(rst):
    rst.value(0)
    time.sleep_ms(50)
    rst.value(1)
    time.sleep_ms(100)


def _init_display(spi, dc, cs):
    _cmd(spi, dc, cs, 0x01)
    time.sleep_ms(100)
    _cmd(spi, dc, cs, 0x11)
    time.sleep_ms(100)
    _cmd(spi, dc, cs, 0x3A)
    _dat(spi, dc, cs, 0x55)   # RGB565 16-bit
    _cmd(spi, dc, cs, 0x36)
    _dat(spi, dc, cs, 0x08)   # BGR=1
    _cmd(spi, dc, cs, 0x29)
    time.sleep_ms(50)


# ═══ API pública do display ═════════════════════════════════════

class Display:
    """Abstração do display SPI com operações básicas."""

    def __init__(self, spi, dc, cs):
        self.spi = spi
        self.dc = dc
        self.cs = cs
        self.width = WIDTH
        self.height = HEIGHT

    def cmd(self, c):
        _cmd(self.spi, self.dc, self.cs, c)

    def dat(self, d):
        _dat(self.spi, self.dc, self.cs, d)

    def fill(self, r, g, b):
        """Preenche a tela inteira com uma cor sólida."""
        color = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        pixel = struct.pack(">H", color)
        chunk = pixel * 64
        total = self.width * self.height
        n, rem = divmod(total, 64)

        self._set_window(0, 0, self.width - 1, self.height - 1)
        self.dc.value(1)
        self.cs.value(0)
        for _ in range(n):
            self.spi.write(chunk)
        if rem:
            self.spi.write(pixel * rem)
        self.cs.value(1)

    def fill_rect(self, x, y, w, h, r, g, b):
        """Preenche um retângulo na posição (x,y) com w×h pixels."""
        # Clipping
        if x < 0:
            w += x
            x = 0
        if y < 0:
            h += y
            y = 0
        if x + w > self.width:
            w = self.width - x
        if y + h > self.height:
            h = self.height - y
        if w <= 0 or h <= 0:
            return

        color = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        pixel = struct.pack(">H", color)
        row = pixel * w

        self._set_window(x, y, x + w - 1, y + h - 1)
        self.dc.value(1)
        self.cs.value(0)
        for _ in range(h):
            self.spi.write(row)
        self.cs.value(1)

    def _set_window(self, x0, y0, x1, y1):
        self.cmd(0x2A)
        self.dat(struct.pack(">HH", x0, x1))
        self.cmd(0x2B)
        self.dat(struct.pack(">HH", y0, y1))
        self.cmd(0x2C)


# ═══ Touch ══════════════════════════════════════════════════════


class Touch:
    """Driver XPT2046 — só detecta se está pressionado (leitura via IRQ)."""

    def __init__(self, spi, dc, cs):
        self.spi = spi
        self.dc = dc
        self.cs_display = cs
        self.cs_touch = machine.Pin(PIN_T_CS, machine.Pin.OUT)
        self.irq = machine.Pin(PIN_T_IRQ, machine.Pin.IN, machine.Pin.PULL_UP)
        self._last_press = False
        self._last_time = 0
        self.debounce_ms = 200

    def is_pressed(self):
        """True se o touch está sendo pressionado AGORA."""
        return self.irq.value() == 0

    def read_taps(self):
        """
        Retorna 1 se detectou uma borda de descida (novo toque),
        0 caso contrário. Usa debounce.
        """
        pressed = self.is_pressed()
        now = time.ticks_ms()

        if pressed and not self._last_press:
            if time.ticks_diff(now, self._last_time) > self.debounce_ms:
                self._last_time = now
                self._last_press = True
                return 1

        if not pressed:
            self._last_press = False

        return 0


# ═══ Init ═══════════════════════════════════════════════════════


def init():
    """
    Inicializa todo o hardware.
    Retorna (display, touch).
    """
    print("[boot] Iniciando hardware...")
    spi = _init_spi()
    dc, cs, rst = _init_pins()
    _hard_reset(rst)
    _init_display(spi, dc, cs)
    print("[boot] Display OK")

    d = Display(spi, dc, cs)
    t = Touch(spi, dc, cs)
    print("[boot] Touch OK")

    return d, t