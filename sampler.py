import datetime
import csv
import time
import os

from hardware.led import set_led
from hardware.motors import set_motor, UNITS

###################### CONFIG ###################################
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_FILE = os.path.join(BASE_DIR, "logs", "data.csv")
TEXT_LOG_FILE = os.path.join(BASE_DIR, "logs", "Sampler_log.txt")

os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)

###################### LOGGING ################################
def log_event(event, motor="", duration=0, notes=""):
    dtnow = datetime.datetime.now()

    # CSV log
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            dtnow.date(),
            dtnow.time(),
            event,
            motor,
            duration,
            notes
        ])

    # Text log
    with open(TEXT_LOG_FILE, "a") as f:
        f.write(
            f"[{dtnow.strftime('%Y-%m-%d %H:%M:%S')}] "
            f"{event} | motor={motor} | duration={duration}s | {notes}\n"
        )

    print(f"LOG | {event} | motor={motor} | duration={duration}s | {notes}")


###################### MOTOR SEQUENCE
