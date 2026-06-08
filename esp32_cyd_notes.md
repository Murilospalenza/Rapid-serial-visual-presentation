# ESP32-2432S028 — Cheap Yellow Display (CYD)

## Informações da Placa

| Item          | Detalhe                          |
|---------------|----------------------------------|
| Modelo        | ESP32-2432S028 (CYD)             |
| Chip          | ESP32-D0WD-V3                    |
| Flash         | 16 MB                            |
| Firmware      | MicroPython v1.24.1              |
| Porta USB     | `/dev/ttyUSB0`                   |
| SO de dev     | CachyOS (Arch Linux)             |
| IDE           | VS Code + MicroPico              |

## Display

- Tela colorida com touch **XPT2046** resistivo (qualidade baixa, mas funcional)
- Resolução: **240×320** (retrato)
- Controlador: **ILI9341** ou **ST7789** (provavelmente ILI9341)
- Conexão: **SPI** (display + touch compartilham o mesmo barramento SPI)
- Backlight funcional (pino BL)

## Alimentação e Bateria

O CYD **NÃO tem circuito de bateria onboard** — não tem conector JST, não tem carregador, não tem step-up. A alimentação é exclusivamente via USB.

### Opções de Alimentação

| Opção | Como | Vantagem | Desvantagem |
|-------|------|----------|-------------|
| **USB direto** | Cabo micro-USB no computador ou carregador 5V/1A | Mais simples, já testado | Fica preso no cabo |
| **Power bank** | Power bank 5V → USB do CYD | Portátil, fácil | Power bank é maior que o CYD |
| **Bateria LiPo 18650 + TP4056 + Step-up** | Bateria 3.7V → TP4056 (carrega) → Step-up 5V → USB CYD | Barato (~R\$20), pequeno | Precisa soldar |
| **Bateria LiPo 3.7V direto no 5V** | **NÃO RECOMENDADO** — 3.7V não é suficiente para o regulador 5V | — | Placa não liga ou fica instável |

### Circuito recomendado para bateria

```
Bateria LiPo 18650 (3.7V)
    │
    ├── TP4056 (módulo carregador USB-C)
    │   └── Carrega via USB quando disponível
    │
    └── MT3608 (step-up boost conversor)
        └── 3.7V → 5V / 1A
            │
            └── Pino 5V do CYD (ou conector USB)
```

- **TP4056**: módulo de carregamento de LiPo (R\$3-5 no Mercado Livre)
- **MT3608**: step-up boost que eleva 3.7V para 5V (R\$5-8)
- **Bateria 18650**: 3.7V, 2000-3000mAh (R\$20-30)
- **Autonomia estimada**: ~10-15 horas (CYD consome ~80mA com display ligado, ~150mA com Wi-Fi)
- Com **deep sleep** (~10µA): meses

### ⚠️ Importante

- **Nunca** conecte bateria LiPo diretamente sem proteção (TP4056) — risco de explosão
- **Nunca** conecte 5V no pino 3.3V — queima o ESP32
- **I2C não serve para alimentação** — I2C é um barramento de dados (SDA/SCL), não fornece energia
- O CYD tem um **regulador AMS1117-3.3** onboard que converte 5V USB para 3.3V. A entrada dele é o pino **5V** (ou USB)

### Consumo estimado

| Modo | Consumo | Autonomia com 18650 (2500mAh) |
|------|---------|------------------------------|
| Display ligado, sem Wi-Fi | ~80mA | ~31 horas |
| Display ligado, lendo RSVP | ~80mA | ~31 horas |
| Display ligado, com Wi-Fi | ~150-200mA | ~12-16 horas |
| Deep sleep (backlight OFF) | ~10µA | ~28 anos (teórico) |
| Desligado (sem bateria) | 0 | — |

## Pinagem Atual (confirmada no HW real)

### Display SPI

| Função | Pino GPIO |
|--------|-----------|
| SCK    | 14        |
| MOSI   | 13        |
| DC     | 2         |
| CS     | 15        |
| RST    | 12        |
| BL     | 21        |

### Touch XPT2046

| Função    | Pino GPIO | Detalhe                                |
|-----------|-----------|----------------------------------------|
| T_IRQ     | 36        | Interrupção (active low, detecta toque) |
| T_CS      | 33        | Chip Select do touch                   |
| T_CLK     | 14        | Compartilhado com SCK do display       |
| T_MOSI    | 13        | Compartilhado com MOSI do display      |
| T_MISO    | 19        | Não usado (display usa só MOSI)        |

## Códigos

### `main.py` — Bichinho Animado + Leitura RSVP (ATUAL)

Sistema completo com dois modos:

#### Modo Pet 🐣 (padrão)
- Bichinho virtual azul animado na tela:
  - **Respiração**: corpo expande/contrai suavemente (ciclo de ~2.5s)
  - **Piscada**: olhos fecham a cada ~20 ciclos de respiração
  - **Sono**: futuramente dormirá após inatividade prolongada
- Eficiência energética:
  - Só redesenha a área do pet (não a tela inteira)
  - Delay de 80ms entre frames
  - Não usa SPI desnecessariamente
- Transição para Modo Leitura: **3 toques rápidos (dentro de 1.5s)**

#### Modo Leitura RSVP 📖
- **RSVP** = Rapid Serial Visual Presentation
  - Mostra **uma palavra por vez** no centro da tela
  - Velocidade: **300 WPM** (palavras por minuto) — ajustável
  - Fonte bitmap 8x8 com escala 3 (letras grandes)
- Controles por toque:
  - **Toque 1x** durante leitura: pausa/continua
  - **Toque 1x** no fim: volta ao modo Pet
- Barra de progresso: `"123/456"`
- Texto demo incluso (conto infantil)

### `main.py` original — Troca de cores a cada 3s (arquivado)

- `cyd_cores.py` — versão anterior, apenas alternava entre 8 cores fixas
- Mantido como referência de que o display SPI funciona

## Biblioteca de Fonte Bitmap

O código inclui uma **fonte bitmap 8x8** embutida (sem usar framebuffer da memória):

- Caracteres suportados: A-Z, a-z (case-insensitive, mapeia pra maiúscula), 0-9, pontuação comum
- Desenho via `fill_rect` com escala ajustável (1x, 2x, 3x)
- Suporte a quebra de linha, centralização, cores customizadas

## Consumo, Bateria e Modo Hibernação

- Display com backlight é o maior consumidor (o backlight fica ligado mesmo com tela preta)
- Estratégias já implementadas:
  - Redesenho parcial (só área que muda — dirty flag)
  - SPI idle quando não precisa atualizar
  - `time.sleep_ms(5-50ms)` no loop principal (CPU dorme entre ciclos)
- **Consumo estimado:** ~80mA com display ligado, ~10µA em deep sleep

### Modo Hibernação — Deep Sleep com Wake por Touch

Funcionamento:
1. Se não houver interação (toque) por **1 minuto**, entra em deep sleep automático
2. Acorda automaticamente ao **tocar na tela** (GPIO 36 = RTC)
3. Após acordar, reinicia o `main.py` do zero (tela volta ao normal)
4. Se ficar mais 1 min sem toque, dorme de novo

```python
import machine
import time

def enter_deep_sleep(timeout_ms=60000):
    """Entra em deep sleep. Acorda ao tocar na tela (GPIO 36) ou por timer."""
    # Desliga backlight
    bl = machine.Pin(21, machine.Pin.OUT)
    bl.value(0)  # backlight OFF → economia máxima

    print(f"[sleep] Dormindo por {timeout_ms}ms ou até toque no GPIO 36")

    # Configura wake-up sources
    # GPIO 36 (IRQ do touch) como wake-up por nível LOW
    wake_pin = machine.Pin(36, machine.Pin.IN, machine.Pin.PULL_UP)
    machine.wake_on_ext0(pin=wake_pin, level=machine.Pin.WAKE_LOW)

    # Timer wake-up (fallback: acorda depois de 1 minuto mesmo sem toque)
    # machine.deepsleep(timeout_ms)  # ou deepsleep com timer

    # Deep sleep de fato
    machine.deepsleep()
    # O código NUNCA continua daqui — o ESP32 reinicia completamente


def main_loop():
    """Loop principal com timeout de inatividade."""
    last_activity = time.ticks_ms()
    IDLE_TIMEOUT = 60_000  # 1 minuto

    while True:
        now = time.ticks_ms()
        # ... lógica normal do código ...

        # Detecta toque
        if touch.read_taps():
            last_activity = now
            # processa toque...

        # Verifica se passou 1 min sem atividade
        if now - last_activity > IDLE_TIMEOUT:
            print("[sleep] 1 min sem toque — hibernando")
            enter_deep_sleep()
```

**Como funciona o wake:**
- `machine.wake_on_ext0(pin=Pin(36), level=machine.Pin.WAKE_LOW)` — acorda quando o pino IRQ do touch vai para LOW (toque)
- Ao acordar, o ESP32 **reinicia completamente** — executa `boot.py` → `main.py` do zero
- O display e periféricos são reinicializados normalmente

**Observações:**
- GPIO 36 é um **RTC GPIO** (funciona durante deep sleep)
- O touch XPT2046 puxa o IRQ para LOW quando pressionado → nível LOW acorda o ESP32
- Após acordar, o boot é completo (~200ms até começar a executar código)
- Se o touch estiver pressionado no momento do wake, o debounce vai ignorar esse primeiro toque

### Botões físicos da placa

O CYD tem dois botões:

| Botão | Nome | GPIO | Função |
|-------|------|------|--------|
| **RST** | EN / Reset | — | Reinicia a placa (como desligar e ligar) |
| **BOOT** | GPIO 0 | 0 | Segurar + RST = modo flash (atualizar firmware) |

- **RST apenas:** aperte RST por 1s → placa reinicia, executa `main.py` de novo
- **BOOT + RST:** segure BOOT, aperte RST, solte RST, solte BOOT → entra em **modo download** (para gravar firmware novo via serial)
- **Após deep sleep:** só RST ou wake por GPIO acorda (BOOT não acorda)

## Referência: RSVP Nano

Projeto clonado em: `/home/murilospalenza/esp/rsvpnano/`  
[ionutdecebal/rsvpnano](https://github.com/ionutdecebal/rsvpnano)

### O que o RSVP Nano tem (e nós ainda não)

A análise do código-fonte (C++) revelou várias features que podemos portar para MicroPython:

| Feature | Status no CYD | Prioridade |
|---------|---------------|------------|
| **Timing por palavra** (comprimento + pontuação) | ✅ Já temos básico | — |
| **Formato .rsvp** com metadados (@title, @author, @chapter, @para) | ❌ Não temos | Alta |
| **Capítulos** navegáveis | ❌ Não temos | Média |
| **Seleção de livros** (menu/biblioteca) | ❌ Não temos | Alta |
| **Persistência de progresso** (salvar posição) | ❌ Não temos | Alta |
| **Múltiplas fontes** (Atkinson, Serif, OpenDyslexic) | ❌ Só 1 fonte | Baixa |
| **Botões físicos** (anterior/próximo, menu, WPM) | ❌ Só touch | Média |
| **Ajuste de WPM** durante leitura | ❌ Fixo em 300 | Média |
| **Suporte a cartão SD** (biblioteca de livros) | ❌ Não temos | Alta |
| **Wi-Fi sync** com servidor | ❌ Não temos | Futuro |
| **Timer de foco** (Pomodoro) | ❌ Não temos | Futuro |
| **Leitura de RSS feeds** | ❌ Não temos | Futuro |
| **Conversor EPUB on-device** | ❌ Só PC | Média |
| **Mass Storage USB** (montar como pendrive) | ❌ Não temos | Futuro |

### Algoritmo de Timing do RSVP Nano (para portar)

O `ReadingLoop` calcula a duração de cada palavra assim:

```
base_delay_ms = 60000 / WPM        # 300 WPM → 200ms por palavra

# Bônus por comprimento (palavras longas ganham mais tempo)
if len(palavra) > 6:  bonus += base_delay_ms * 0.06 * (len - 6)
if len(palavra) > 10: bonus += base_delay_ms * 0.09 * (len - 10)
if len(palavra) > 14: bonus += base_delay_ms * 0.12 * (len - 14)
# Cap: bonus_comprimento <= base_delay_ms * 1.70

# Bônus por pontuação final
if palavra termina com '.', '!', '?':  bonus += base_delay_ms * 0.50
if palavra termina com ',', ';', ':',  bonus += base_delay_ms * 0.20

# Bônus por parágrafo (palavra após @para)
if início_de_parágrafo: bonus += base_delay_ms * 0.30

# Duração final
duration_ms = base_delay_ms + sum(bonus)
duration_ms = max(duration_ms, 80ms)  # mínimo 80ms
```

### Formato .rsvp (para implementar leitura de arquivo)

Arquivo texto puro com diretivas `@`:

```
@rsvp 1
@title: O Nome do Livro
@author: Nome do Autor
@chapter: Título do Capítulo 1
@para
palavra1 palavra2 palavra3...
@para
palavra4 palavra5...
@chapter: Capítulo 2
...
```

Regras:
- `@rsvp 1` = versão do formato (opcional)
- `@title:` e `@author:` = metadados
- `@chapter:` = marcador de capítulo (navegação)
- `@para` = quebra de parágrafo (mais tempo na última palavra)
- Linhas sem `@` = palavras, separadas por espaços
- Arquivos `.txt` também são aceitos (sem diretivas)

### BookContent (estrutura de dados para portar)

```python
class BookContent:
    def __init__(self):
        self.title = ""
        self.author = ""
        self.words = []          # lista de strings
        self.chapters = []       # lista de (nome_capitulo, indice_primeira_palavra)
        self.paragraph_starts = set()  # índices de palavras que iniciam parágrafo
```

### Próximos passos para implementação

1. **Criar parser de .rsvp** em Python (já temos o formato definido)
2. **Adicionar seleção de livros** (menu na tela: lista de arquivos)
3. **Salvar progresso** em arquivo JSON na flash (`posicao.json`)
4. **Portar o algoritmo de timing** do ReadingLoop (já temos esboço no `rsvp.py`)
5. **Adicionar SD card** para biblioteca (futuro)
6. **Ajuste de WPM** via toque (deslizar para cima/baixo)

## Comandos Úteis

```bash
# Upload via rshell
rshell -p /dev/ttyUSB0 cp main.py /pyboard/main.py

# Upload de arquivo específico
rshell -p /dev/ttyUSB0 cp main.py /pyboard/

# Monitor serial
screen /dev/ttyUSB0 115200

# Listar arquivos no ESP32 via rshell
rshell -p /dev/ttyUSB0 ls /pyboard
```

## Referências Técnicas

- [ESP32-2432S028 (CYD) no Github](https://github.com/witnessmenow/ESP32-Cheap-Yellow-Display)
- [XPT2046 Touch Controller Datasheet](https://www.bing.com/search?q=xpt2046+datasheet)
- [ILI9341 Datasheet](https://cdn-shop.adafruit.com/datasheets/ILI9341.pdf)
- [RSVP Nano — leitor RSVP open source](https://github.com/ionutdecebal/rsvpnano)
- [MicroPython SPI Documentation](https://docs.micropython.org/en/latest/library/machine.SPI.html)