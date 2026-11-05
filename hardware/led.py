import RPi.GPIO as GPIO
import time
import threading

LED_PIN = 27  # GPIO27 (physical pin 13), GPIO17 IS USED BY THE WITTY PI

GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)

_blink_thread = None
_stop_blink = threading.Event()


def _blink_loop():
    while not _stop_blink.is_set():
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(0.5)

        GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(0.5)


def set_led(state):
    """
    States:
    - "on"       -> solid ON
    - "off"      -> OFF
    - "sampling" -> blinking
    """

    global _blink_thread

    print(f"[LED] Setting state: {state}")

    # stop existing blink thread
    _stop_blink.set()

    if _blink_thread and _blink_thread.is_alive():
        _blink_thread.join(timeout=1)

    _blink_thread = None

    if state == "on":
        GPIO.output(LED_PIN, GPIO.HIGH)

    elif state == "off":
        GPIO.output(LED_PIN, GPIO.LOW)

    elif state == "sampling":

        # clear stop flag
        _stop_blink.clear()

        # start blink thread
        _blink_thread = threading.Thread(
            target=_blink_loop,
            daemon=True
        )

        _blink_thread.start()

    else:
        print(f"[LED] Unknown state: {state}")

if __name__ == "__main__":

    print("Testing LED ON")
    set_led("on")
    time.sleep(3)

    print("Testing LED OFF")
    set_led("off")
    time.sleep(3)

    print("Testing LED BLINK")
    set_led("sampling")
    time.sleep(10)

    print("Done")
    set_led("off")

    GPIO.cleanup()
