from flask import render_template, Flask, jsonify, request
import subprocess, threading, enum, json
import core.lib.kart_status as k_s


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

PYTHON_CORE = "core/core.py"
PYTHON_CORE_CONFIG = "core/config/kart_config.py"

app = Flask(__name__)
runner = None
thread = None
core_status = StatusCodes.CORE_IDLE
core_presets = None
leds = k_s.StatusLeds()

def check_core_failure(): 
    """
    Checks for a core failure and catches the core's exit code.
    
    Returns: Core Status in a StatusCodes instance
    """
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
    """
    Index Page
    """
    return render_template("index.html")

@app.route("/index")
def index():
    """
    Index Page Alias
    """
    return render_template("index.html")

# Takes a snapshot of the camera view
@app.route("/camera")
def camera():
    """
    Camera Viewing Page
    Takes a snapshot from the driver's camera in order to 
    calibrate and center the headset position.

    Renders the snapshot to a webpage.
    """
    import core.lib.kart_hs as hs

    detector = hs.kart_ARUCO_init()

    cap, k, d, dim, cent = hs.load_video_data()

    hs.time.sleep(1)

    _, frame = cap.read()

    frame = hs.cv2.undistort(frame, k, d)

    _, ids, _ = detector.detectMarkers(frame)

    cap.release()

    frame = hs.cv2.line(frame, [cent[0], 0], [cent[0], dim[1]], (0, 0, 255), 5)
    frame = hs.cv2.line(frame, [0, cent[1]], [dim[0], cent[1]], (0, 0, 255), 5)

    if ids is not None:
        frame = hs.cv2.putText(frame, f"Headset Found! id/s: {ids}", (40, 40), hs.cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 0, 255), 2)

    hs.cv2.imwrite("web/static/camera/img.png", frame)

    return render_template("camera.html")

# Core Start Routine
@app.route("/core_start", methods=["POST"])
def core_start():
    """
    Tells the core to start, sets the status to 
    running and starts the check core failure thread
    """
    global runner, core_status, thread
    print("starting go kart")

    leds.set_status(k_s.LedStatus.SET)

    # Starts the runner and sets the status page
    if runner and runner.poll() is None:
        core_status = StatusCodes.CORE_ALREADY_RUNNING
        return jsonify(
            {
                "kart_signal": "error"
            }
        )

    runner = subprocess.Popen(
        ["python3", PYTHON_CORE],
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

# Renders Preset Page
@app.route('/config')
def kart_config():
    """
    Renders kart_config.py web page
    """
    return render_template("config.html")

# Opens Status Api Page With The relative Statuses
@app.route('/status')
def status():
    """
    Returns core's status to the webpage
    """

    match (core_status):
        case StatusCodes.JOYSTICK_HAS_FAILED:
            return jsonify(
                {
                "kart_status"    :"error",
                "web_message"    :"Joystick Error! Check Connections."
                }
            )
        case StatusCodes.SERIAL_HAS_FAILED:
            return jsonify(
                {
                "kart_status"           :"error",
                "web_message"           :"Serial Error! Check Connections."
                }
            )
        case StatusCodes.CORE_RUNNING:
            return jsonify(
                {
                    "kart_status":      "sig_started",
                    "web_message":      "Running!"
                }
            )
        case StatusCodes.CORE_SHUTDOWN:
            return jsonify(
                {
                    "kart_status":      "sig_shutdown",
                    "web_message":      "Shutting Down!"
                }
            )
        case StatusCodes.CORE_ALREADY_RUNNING:
            return jsonify(
                {
                    "kart_status":      "error",
                    "web_message":      "Kart Already Running!"
                }
            )
        case StatusCodes.CORE_IDLE:
            return jsonify(
                {
                    "kart_status":      "sig_ready",
                    "web_message":      "Checking Readiness..."
                }
            )

# Terminates the core
@app.route("/core_stop", methods=["POST"])
def core_stop():
    global core_status
    print("stopping go kart")

    core_status = StatusCodes.CORE_IDLE
    leds.set_status(k_s.LedStatus.READY)

    runner.terminate()
    runner.wait()
    thread.join()
    
    return jsonify(
        {
            "kart_signal": "sig_stop"
        }
    )

# Shuts Down the Whole Machine
@app.route("/core_shutdown", methods=["POST"])
def core_shutdown():
    global core_status
    core_status = StatusCodes.CORE_SHUTDOWN
    leds.turn_off()
    process = subprocess.Popen(["shutdown", "now"])
    stdin, stderr = process.communicate()

    return jsonify (
        {
           "kart_status":"sig_poweroff"
        }
    )

# Set a Param of the core's configuration file
def core_config(args):
    subprocess.Popen((["python3", PYTHON_CORE_CONFIG] + args))

# Sets a particular Preset
@app.route('/set_preset', methods=["POST"])
def set_preset():
    preset = request.data.decode()
    core_config(core_presets[preset]["args"])
    return jsonify({"core_preset_mode":preset})

# Renders all presets with relative names
@app.route('/preset_names')
def preset_names():
    global core_presets
    with open("web/static/presets.json", "r") as jsf:
        core_presets = json.load(jsf)
    return jsonify(core_presets)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
