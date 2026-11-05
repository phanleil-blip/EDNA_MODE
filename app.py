from flask import Flask, request, jsonify, redirect, url_for
import json
from sampler import run_test, run_sampler, prime_preservative_pumps, run_pump
import os
from hardware.scheduler import schedule_wakeup, WITTY_PI_DIR
from hardware.motors import UNITS
import threading
from hardware.led import set_led

SUB_MAX_SEC = 3600
PRES_MAX_SEC = 20

set_led("on")

app = Flask(__name__)

CONFIG = "config.json"

test_state = {
    "running": False,
    "stop": False
}

def load_config():
    with open(CONFIG, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG, "w") as f:
        json.dump(data, f, indent=4)

# FOR MAKING THE SEQUENCE RUN AFER BEING SCHEDULED
def boot_auto_run():
    config = load_config()

    if config.get("armed", False):

        print("[BOOT] Armed system detected — starting sampler")

        def background_run():
            try:
                test_state["running"] = True
                test_state["stop"] = False

                run_test(config, test_state)

            finally:
                test_state["running"] = False
                test_state["stop"] = False

                config["armed"] = False
                save_config(config)

        threading.Thread(target=background_run, daemon=True).start()

    else:
        clear_witty_pi_schedule()

# For WIPING the schedule after its not needed
def clear_witty_pi_schedule():
    print("[BOOT] Disarmed state detected → clearing Witty Pi schedule")

    schedule_file = f"{WITTY_PI_DIR}/schedule.wpi"

    with open(schedule_file, "w") as f:
        f.write("")  # empty schedule = no future wake/sleep cycle

    os.system(f"cd {WITTY_PI_DIR} && sudo ./runScript.sh")

@app.route("/")
def home():
    config = load_config()

    sample_duration = config.get("sample_duration", 10)
    interval_min = config.get("interval_min", 1)
    pres_duration = config.get("pres_duration", 5.0)
    sample_time = config.get("sample_time", "02:00")

    def pump_forms(kind, default, limit):
        return "".join(f"""
        <form method="POST" action="/pump" style="display:inline-block; margin:4px;">
            <input type="hidden" name="pump" value="{kind}{unit}">
            <label>{unit}</label>
            <input type="number" step=".1" min=".1" max="{limit}" name="duration" value="{default}" style="width:70px;">
            <input type="submit" value="Run">
        </form>""" for unit in UNITS)

    return f"""
    <h1>eDNA Sampler Control Panel</h1>

    <form method="POST" action="/save">
        <label>Scheduled Sample Time (24-hour HH:MM):</label>
        <input type="time" name="sample_time" value="{sample_time}"><br><br>

        <label>Sample Duration (sec):</label>
        <input type="number" step=".1" name="sample_duration" value="{sample_duration}"><br><br>

        <label>Interval (min):</label>
        <input type="number" step=".01" name="interval_min" value="{interval_min}"><br><br>

        <label>Preservative Pump Runtime (max 20 sec):</label>
        <input type="number" step=".1" max="20" name="pres_duration" value="{pres_duration}"><br><br>

        <input type="submit" value="Save">
    </form>

    <br>

    <form method="POST" action="/prime">
        <input type="submit" value="Prime Preservative Pumps">
    </form>

    <form method="POST" action="/test">
        <input type="submit" value="Full Test Run">
    </form>

    <br>

    <form method="POST" action="/stop">
        <input type="submit" value="Stop Priming/Test">
    </form>

    <h2>Sub Pumps (sec)</h2>
    {pump_forms("sub", sample_duration, SUB_MAX_SEC)}

    <h2>Preservative Pumps (sec, max {PRES_MAX_SEC})</h2>
    {pump_forms("pres", pres_duration, PRES_MAX_SEC)}

    <br>

    <form method="POST" action="/arm">
        <input type="submit" value="Prepare for Next Deployment">
    </form>
    """


@app.route("/save", methods=["POST"])
def save():
    data = {
        "sample_duration": float(request.form["sample_duration"]),
        "interval_min": float(request.form["interval_min"]),
        "pres_duration": float(request.form["pres_duration"]),
        "sample_time": request.form["sample_time"],
        "armed": False
    }

    save_config(data)
    return "Settings saved!<br><a href='/'>Back</a>"

@app.route("/prime", methods=["POST"])
def prime():

    if test_state["running"]:
        return "Cannot prime while test is running.<br><a href='/'>Back</a>"

    config = load_config()

    def background_run():
        try:
            test_state["running"] = True
            test_state["stop"] = False

            prime_preservative_pumps(config, test_state)

        finally:
            test_state["running"] = False
            test_state["stop"] = False  

    thread = threading.Thread(target=background_run, daemon=True)
    thread.start()

    return redirect(url_for("home"))


@app.route("/test", methods=["POST"])
def test():

    if test_state["running"]:
        return "Already running.<br><a href='/'>Back</a>"

    config = load_config()

    def background_run():
        try:
            test_state["running"] = True
            test_state["stop"] = False

            run_test(config, test_state)

        finally:
            test_state["running"] = False
            test_state["stop"] = False

    thread = threading.Thread(target=background_run, daemon=True)
    thread.start()

    return redirect(url_for("home"))


@app.route("/pump", methods=["POST"])
def pump():

    if test_state["running"]:
        return "Already running.<br><a href='/'>Back</a>"

    name = request.form["pump"]
    kind, unit = name[:-2], name[-2:]
    limit = SUB_MAX_SEC if kind == "sub" else PRES_MAX_SEC

    if kind not in ("sub", "pres") or unit not in UNITS:
        return "Unknown pump.<br><a href='/'>Back</a>"

    duration = float(request.form["duration"])

    if not 0 < duration <= limit:
        return f"Run time must be between 0 and {limit} sec.<br><a href='/'>Back</a>"

    def background_run():
        try:
            test_state["running"] = True
            test_state["stop"] = False

            run_pump(name, duration, test_state)

        finally:
            test_state["running"] = False
            test_state["stop"] = False

    thread = threading.Thread(target=background_run, daemon=True)
    thread.start()

    return redirect(url_for("home"))


@app.route("/stop", methods=["POST"])
def stop():
    test_state["stop"] = True
    return redirect(url_for("home"))


@app.route("/arm", methods=["POST"])
def arm():
    config = load_config()

    try:
        schedule_wakeup(
            config["sample_time"],
            config["sample_duration"],
            config["pres_duration"],
            config["interval_min"]
        )
    except ValueError as e:
        return f"{e}<br><a href='/'>Back</a>"

    config["armed"] = True
    save_config(config)

    return "System armed for next scheduled sample.<br><a href='/'>Back</a>"


if __name__ == "__main__":
    set_led("on")

    # IMPORTANT: run boot check BEFORE serving web app
    boot_auto_run()

    app.run(host="0.0.0.0", port=5000)
