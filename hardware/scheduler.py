from datetime import datetime, timedelta
import os
import math

WITTY_PI_DIR = os.path.expanduser("~/wittypi")
SCHEDULE_FILE = f"{WITTY_PI_DIR}/schedule.wpi"
RUN_SCRIPT = f"{WITTY_PI_DIR}/runScript.sh"

MOTOR_CYCLES = 16
SETTLE_SEC = 2 # MATCHES THE PAUSE BETWEEN SUB AND PRES IN sampler.py

# BREAKS IF YOU TRY TO SCHEDULE AN EVENT UNDER 2 MIN AWAY

def schedule_wakeup(sample_time, sample_duration, pres_duration, interval_min):

    now = datetime.now()

    # -------- WAKE TIME --------
    wake = datetime.strptime(sample_time, "%H:%M").replace(
        year=now.year,
        month=now.month,
        day=now.day
    )

    # SETS IT TO BE TOMORROW AT THE DESIRED TIME IF TODAY IS ALREADY PAST THIS TIME.
    if wake <= now:
        wake += timedelta(days=1)

    # -------- SAMPLE RUNTIME --------
    interval_sec = interval_min*60
    cycle_sec = sample_duration + SETTLE_SEC + pres_duration + interval_sec
    runtime_sec = MOTOR_CYCLES * cycle_sec + 180 # Adds 3 min for transitions and startup
    runtime_hrs, runtime_min = divmod(math.ceil(runtime_sec / 60), 60)

    wake_offset_sec = int((wake - now).total_seconds())

    if wake_offset_sec < 120:
        raise ValueError("Sample time must be at least 2 minutes away")

    # THE PI STAYS ON FOR THE FIRST 2 MIN (ON M2), THEN SLEEPS UNTIL THE WAKE TIME
    sleep_hrs, sleep_rem = divmod(wake_offset_sec - 120, 3600)
    sleep_min, sleep_sec = divmod(sleep_rem, 60)

    # -------- FIXED WITTY PI SCHEDULE --------      BREAKS IF YOU TRY TO SCHEDULE AN EVENT UNDER 2 MIN AWAY
    schedule_text = f"""BEGIN {now.strftime('%Y-%m-%d %H:%M:%S')}
END   2035-12-31 23:59:59

ON M2
OFF H{sleep_hrs} M{sleep_min} S{sleep_sec}

ON H{runtime_hrs} M{runtime_min}
OFF M15 WAIT
"""

    with open(SCHEDULE_FILE, "w") as f:
        f.write(schedule_text)

    # ---------------- APPLY TO WITTY PI ----------------
    os.system(f"cd {WITTY_PI_DIR} && sudo ./runScript.sh")

    print("[Scheduler] Witty Pi schedule applied")
