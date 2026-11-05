import atexit

import board
import busio
from adafruit_mcp230xx.mcp23017 import MCP23017

SUB_ADDRESS = 0x20
PRES_ADDRESS = 0x21
ACTIVE_LOW = True  # SET FALSE IF THE RELAYS TURN ON WITH A HIGH SIGNAL
IDLE = 0xFFFF if ACTIVE_LOW else 0x0000

UNITS = [f"{n}{s}" for n in range(1, 9) for s in "AB"]

i2c = busio.I2C(board.SCL, board.SDA)
SUB_CHIP = MCP23017(i2c, address=SUB_ADDRESS)
PRES_CHIP = MCP23017(i2c, address=PRES_ADDRESS)

# 5A-8B ARE WIRED TO PB7..PB0, BUT THE LIBRARY NUMBERS PB0..PB7 AS PINS 8-15
def pin_index(i):
    return i if i < 8 else 23 - i

MOTOR_PINS = {}
for i, unit in enumerate(UNITS):
    MOTOR_PINS[f"sub{unit}"] = SUB_CHIP.get_pin(pin_index(i))
    MOTOR_PINS[f"pres{unit}"] = PRES_CHIP.get_pin(pin_index(i))

def all_off():
    for chip in (SUB_CHIP, PRES_CHIP):
        chip.gpio = IDLE

# LATCH THE IDLE LEVEL BEFORE SWITCHING TO OUTPUTS SO THE RELAYS DON'T PULSE AT STARTUP
all_off()
for chip in (SUB_CHIP, PRES_CHIP):
    chip.iodir = 0x0000
atexit.register(all_off)

def set_motor(name, state):
    MOTOR_PINS[name].value = state != ACTIVE_LOW
