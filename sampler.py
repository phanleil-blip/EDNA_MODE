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


###################### MOTOR SEQUENCE ############################

MOTOR_SEQUENCE = [(f"sub{u}", f"pres{u}") for u in UNITS]


###################### HELPERS ###################################

def safe_stop(main=None, pres=None):
    """Ensure all motors are OFF safely."""
    if main:
        set_motor(main, False)
    if pres:
        set_motor(pres, False)
    log_event("STOP_REQUESTED")
    set_led("on")


def interruptible_sleep(duration, state):
    """Sleep but allow interruption."""
    start = time.time()
    while time.time() - start < duration:
        if state and state.get("stop"):
            return False
        time.sleep(0.1)
    return True


###################### CORE SEQUENCE ENGINE ######################

def run_sequence(sample_duration, pres_duration, interval_min, state=None):

    set_led("sampling")
    log_event("START_SEQUENCE")

    start_time = time.time()

    try:
        for main, pres in MOTOR_SEQUENCE:

            # -------- STOP CHECK --------
            if state and state.get("stop"):
                safe_stop(main, pres)
                return

            # -------- MAIN MOTOR --------
            log_event("MAIN_START", motor=main, duration=sample_duration)

            set_motor(main, True)
            if not interruptible_sleep(sample_duration, state):
                safe_stop(main, pres)
                return
            set_motor(main, False)

            log_event("MAIN_STOP", motor=main, duration=sample_duration)

            if not interruptible_sleep(2, state):
                safe_stop(main, pres)
                return

            # -------- STOP CHECK --------
            if state and state.get("stop"):
                safe_stop(main, pres)
                return

            # -------- PRES MOTOR --------
            log_event("PRES_START", motor=pres, duration=pres_duration)

            set_motor(pres, True)
            if not interruptible_sleep(pres_duration, state):
                safe_stop(main, pres)
                return
            set_motor(pres, False)

            log_event("PRES_STOP", motor=pres, duration=pres_duration)

            # -------- STOP CHECK --------
            if state and state.get("stop"):
                safe_stop(main, pres)
                return

            # -------- INTERVAL --------
            interval_sec = interval_min * 60
            log_event(
                "INTERVAL_WAIT",
                duration=interval_sec,
                notes="Between sample stages"
            )

            if not interruptible_sleep(interval_sec, state):
                safe_stop(main, pres)
                return

    except Exception as e:
        log_event("ERROR", notes=str(e))
        set_led("on")
        raise

    total_time = time.time() - start_time
    log_event("END_SEQUENCE", notes=f"Total runtime: {total_time:.1f} sec")
    set_led("on")


###################### JSON ENTRY POINT ###########################

def run_sampler(config):

    sample_duration = config.get("sample_duration", 10)
    pres_duration = config.get("pres_duration", 5)
    interval = config.get("interval_min", 1)

    run_sequence(sample_duration, pres_duration, interval, state=None)

    config["armed"] = False
    return config


###################### TEST MODE #################################

def run_test(config, state=None):
    """
    Run a single test sampling cycle using the provided configuration.
    """

    sample_duration = config.get("sample_duration", 10)
    pres_duration = config.get("pres_duration", 5)
    interval_min = config.get("interval_min", 1)

    try:
        run_sequence(
            sample_duration=sample_duration,
            pres_duration=pres_duration,
            interval_min=interval_min,
            state=state
        )
    finally:
        set_led("on")


###################### PRIME MODE #################################

def prime_preservative_pumps(config, state=None):
    """
    Run preservative pumps in sequence for priming.
    """

    pres_duration = config.get("pres_duration", 5)

    set_led("sampling")
    log_event("PRIME_START", notes="Priming preservative pumps")

    try:
        for _, pres in MOTOR_SEQUENCE:

            if state and state.get("stop"):
                safe_stop(None, pres)
                return

            log_event("PRES_PRIME_START", motor=pres, duration=pres_duration)

            set_motor(pres, True)
            if not interruptible_sleep(pres_duration, state):
                safe_stop(None, pres)
                return
            set_motor(pres, False)

            log_event("PRES_PRIME_STOP", motor=pres, duration=pres_duration)

            if not interruptible_sleep(1, state):
                safe_stop(None, pres)
                return

    except Exception as e:
        log_event("ERROR", notes=str(e))
        set_led("on")
        raise

    log_event("PRIME_END")
    set_led("on")


###################### SINGLE PUMP #################################

def run_pump(name, duration, state=None):
    """
    Run one pump for a set duration.
    """

    set_led("sampling")
    log_event("PUMP_START", motor=name, duration=duration)

    try:
        set_motor(name, True)
        finished = interruptible_sleep(duration, state)
    finally:
        set_motor(name, False)
        set_led("on")

    log_event("PUMP_STOP" if finished else "PUMP_ABORT", motor=name, duration=duration)


###################### MAIN #################################

if __name__ == "__main__":
    print("Running standalone test with default values")
    test_config = {
        "sample_duration": 10,
        "pres_duration": 5,
        "interval_min": 1
    }
    run_test(test_config)
