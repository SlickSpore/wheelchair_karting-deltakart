from flask import render_template, Flask, jsonify
import subprocess, threading

"""
    Written By Ettore Caccioli 17/04/2026
    © Wheelchair Karting
"""

app = Flask(__name__)

runner = None
thread = None
error_code = 0

def check_status(): 
    global error_code
    runner.communicate()
    error_code = runner.returncode

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/core_start", methods=["POST"])
def core_start():
    global runner, error_code, thread
    print("starting go kart")

    if runner and runner.poll() is None:
        return jsonify(
            {
                "kart_status"   :"error",
                "web_message"    :"Kart Already Running!"
            }
        )

    runner = subprocess.Popen(
        ["python3", "core/core.py"],
        stderr=subprocess.PIPE,
        text=True
    )

    thread = threading.Thread(target=check_status, daemon=True)
    thread.start()

    return jsonify(
        {
            "kart_signal": "sig_start"
        }
    )

@app.route('/status')
def status():
    match (error_code):
        case 255:
            return jsonify(
                {
                "kart_status"   :"error",
                "web_message"    :"Joystick Error! Check Connections."
                }
            )
        case 254:
            return jsonify(
                {
                "kart_status"   :"error",
                "web_message"    :"Serial Error! Check Connections."
                }
            )
        case _:
            return jsonify(
                {
                    "kart_status":  "sig_start",
                    "web_message":   "Running!"
                }
            )

@app.route("/core_stop", methods=["POST"])
def core_stop():
    print("stopping go kart")
    runner.terminate()
    runner.wait()
    thread.join()
    return jsonify(
        {
            "kart_signal": "sig_stop"
        }
    )

if __name__ == "__main__":
    app.run(port=80)
