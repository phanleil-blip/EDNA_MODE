import time
from hardware.motors import UNITS, set_motor

for kind in ("sub", "pres"):
    for unit in UNITS:
        print(kind, unit)
        set_motor(f"{kind}{unit}", True)
        time.sleep(1)
        set_motor(f"{kind}{unit}", False)
