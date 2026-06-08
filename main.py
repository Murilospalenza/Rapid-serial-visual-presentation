"""
main.py — Orquestrador do CYD (Pet ASCII + RSVP Reader)
ESP32-2432S028 (Cheap Yellow Display) | MicroPython

Modos:
  - Pet: arte ASCII animada (coruja, gato, robô...) — tela de espera
  - RSVP: leitura palavra por palavra

Fluxo:
  Pet → (3 toques) → RSVP → (fim + toque) → Pet

Módulos:
  boot.py   → inicialização do hardware (Display, Touch)
  screen.py → renderização de texto e arte ASCII
  pet.py    → tela de espera com arte ASCII
  rsvp.py   → leitura RSVP
"""

import time
from boot import init
from pet import PetScreen
from rsvp import RSVPScreen

# ═══ Estados ══════════════════════════════════════════════════════

MODE_PET  = 'pet'
MODE_RSVP = 'rsvp'

# ═══ Texto de demonstração ═══════════════════════════════════════

TEXTO_DEMO = (
    "Era uma vez um pequeno grilo que vivia feliz em um jardim. "
    "Ele adorava pular de flor em flor e cantar para a lua. "
    "Cada noite ele aprendia uma nova canção com as estrelas. "
    "Até que um dia ele encontrou um vagalume e os dois "
    "se tornaram grandes amigos. Juntos eles viajaram pelo "
    "mundo espalhando luz e música por onde passavam. "
    "E viveram felizes para sempre."
)

# ═══ Main ═════════════════════════════════════════════════════════


def main():
    print("=== CYD Pet + RSVP ===")

    # Inicializa hardware
    try:
        display, touch = init()
    except Exception as e:
        print(f"[ERRO] Falha na inicialização: {e}")
        return

    # Cria telas
    pet = PetScreen(display, touch)
    rsvp = RSVPScreen(display, touch)
    rsvp.load_text(TEXTO_DEMO)

    # Estado inicial
    mode = MODE_PET
    print("[main] Modo Pet — Toque 3x para ler!")

    # Primeira renderização
    pet.dirty = True
    pet.update(time.ticks_ms())

    # ═══ Loop principal ═══════════════════════════════════════

    while True:
        now = time.ticks_ms()

        if mode == MODE_PET:
            result = pet.update(now)
            if result == 'go_rsvp':
                print("[main] → Modo RSVP")
                mode = MODE_RSVP
                rsvp.last_advance = 0  # força mostrar 1ª palavra
                rsvp.paused = False
                rsvp.finished = False
                rsvp.word_index = 0

        elif mode == MODE_RSVP:
            result = rsvp.update(now)
            if result == 'back_to_pet':
                print("[main] → Modo Pet")
                mode = MODE_PET
                pet.dirty = True

        # Pequeno delay para não sobrecarregar CPU
        time.sleep_ms(5)


main()