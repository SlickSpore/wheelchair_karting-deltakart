from flask import render_template, Flask, jsonify, request
import subprocess, threading, enum, json

"""
    Written By Ettore Caccioli 17/04/2026
    © Wheelchair Karting
"""

class StatusCodes(enum.Enum):
    JOYSTICK_HAS_FAILED = 255 
    SERIAL_HAS_FAILED = 254 
    CORE_IDLE = 0
    CORE_RUNNING = 1
    CORE_ALREADY_RUNNING = 2
    CORE_SHUTDOWN = 0xAA 

app = Flask(__name__)

runner = None
thread = None
core_status = StatusCodes.CORE_IDLE

core_presets = None

def check_core_failure(): 
    global core_status
    if runner:
        runner.communicate()
        match(runner.returncode):
            case StatusCodes.JOYSTICK_HAS_FAILED.value:
                core_status = StatusCodes.JOYSTICK_HAS_FAILED
            case StatusCodes.SERIAL_HAS_FAILED.value:
                core_status = StatusCodes.SERIAL_HAS_FAILED
            case _:
                core_status = StatusCodes.CORE_RUNNING


@app.route("/")
def home():
    return render_template("index.html")
@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/core_start", methods=["POST"])
def core_start():
    global runner, core_status, thread
    print("starting go kart")

    if runner and runner.poll() is None:
        core_status = StatusCodes.CORE_ALREADY_RUNNING
        return jsonify(
            {
                "kart_signal": "error"
            }
        )

    runner = subprocess.Popen(
        ["python3", "core/core.py"],
        stderr=subprocess.PIPE,
        text=True
    )

    thread = threading.Thread(target=check_core_failure, daemon=True)
    thread.start()

    core_status = StatusCodes.CORE_RUNNING

    return jsonify(
        {
            "kart_signal": "sig_start"
        }
    )

@app.route('/config')
def kart_config():
    return render_template("config.html")

@app.route('/status')
def status():
    print(core_status)
    match (core_status):
        case StatusCodes.JOYSTICK_HAS_FAILED:
            return jsonify(
                {
                "kart_status"   :"error",
                "web_message"    :"Joystick Error! Check Connections."
                }
            )
        case StatusCodes.SERIAL_HAS_FAILED:
            return jsonify(
                {
                "kart_status"   :"error",
                "web_message"    :"Serial Error! Check Connections."
                }
            )
        case StatusCodes.CORE_RUNNING:
            return jsonify(
                {
                    "kart_status":  "sig_started",
                    "web_message":   "Running!"
                }
            )
        case StatusCodes.CORE_SHUTDOWN:
            return jsonify(
                {
                    "kart_status":  "sig_shutdown",
                    "web_message":   "Shutting Down!"
                }
            )
        case StatusCodes.CORE_ALREADY_RUNNING:
            return jsonify(
                {
                    "kart_status"   :"error",
                    "web_message"    :"Kart Already Running!"
                }
            )
        case StatusCodes.CORE_IDLE:
            return jsonify(
                {
                    "kart_status":  "sig_ready",
                    "web_message":   "Checking Readiness..."
                }
            )

@app.route("/core_stop", methods=["POST"])
def core_stop():
    global core_status
    print("stopping go kart")
    
    runner.terminate()
    runner.wait()
    thread.join()

    core_status = StatusCodes.CORE_IDLE
    
    return jsonify(
        {
            "kart_signal": "sig_stop"
        }
    )

@app.route("/core_shutdown", methods=["POST"])
def core_shutdown():
    global core_status
    core_status = StatusCodes.CORE_SHUTDOWN
    process = subprocess.Popen(["shutdown", "now"])
    stdin, stderr = process.communicate()

    return jsonify (
        {
           "kart_status":"sig_poweroff"
        }
    )

def core_config(args):
    subprocess.Popen((["python3", "core/config/kart_config.py"] + args))

@app.route('/set_preset', methods=["POST"])
def set_preset():
    preset = request.data.decode()
    core_config(core_presets[preset]["args"])
    return jsonify({"core_preset_mode":preset})

@app.route('/preset_names')
def preset_names():
    global core_presets
    with open("web/static/presets.json", "r") as jsf:
        core_presets = json.load(jsf)
    return jsonify(core_presets)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
