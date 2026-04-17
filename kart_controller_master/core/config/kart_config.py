import json, argparse, os


global_variables = {}
FNAME = "core/config/kart_defaults.json"
parser = argparse.ArgumentParser("Kart_Settings_Editor v1")

parser.add_argument("-gd", '--generate_defaults', action="store_true")
parser.add_argument("--verbose")
parser.add_argument("--baud_rate")
parser.add_argument("--serial_port")
parser.add_argument("--reading_speed")
parser.add_argument("--writing_speed")
parser.add_argument("--packet_header")
parser.add_argument("--packet_footer")
parser.add_argument("--packet_ok")
parser.add_argument("--motor_left")
parser.add_argument("--motor_right")
parser.add_argument("--motor_maxangle")
parser.add_argument("--js_threshold")
parser.add_argument("--js_axes")
parser.add_argument("--js_dtzn")

args = parser.parse_args()

class Kart_Settings():
    def __init__(self):
        settings_json = load_settings()
        self.BAUD_RATE = settings_json["baud_rate"]    
        self.SERIAL_PORT = settings_json["serial_port"]  
        self.READING_SPEED = settings_json["reading_speed"]
        self.WRITING_SPEED = settings_json["writing_speed"]
        self.PACKET_HEADER = settings_json["packet_header"]
        self.PACKET_FOOTER = settings_json["packet_footer"]
        self.PACKET_OK = settings_json["packet_ok"]    
        self.MOTOR_LEFT = settings_json["motor_left"]   
        self.MOTOR_RIGHT = settings_json["motor_right"]  
        self.MOTOR_MAXANGLE = settings_json["motor_maxangle"]
        self.JS_THRESHOLD = settings_json["js_threshold"] 
        self.JS_AXES = settings_json["js_axes"]      
        self.JS_DTZN = settings_json["js_dtzn"]      
        self.VERBOSE = settings_json["verbose"] 


def generate_defaults():
    if FNAME in os.listdir():
        selection = input(f"CONFIG FILE {FNAME}, ALREADY IN FOLDER, OVERWRITE? [y/n]: ")
        if selection.lower() != 'y':
            exit(0)

    global_variables["baud_rate"]       = 115200
    global_variables["serial_port"]     = '/dev/driver_serial'
    global_variables["reading_speed"]   = 1//100
    global_variables["writing_speed"]   = 1//100
    global_variables["packet_header"]   = 0x4545
    global_variables["packet_footer"]   = 0x4646
    global_variables["packet_ok"]       = '47470a'
    global_variables["motor_left"]      = 1
    global_variables["motor_right"]     = 0
    global_variables["js_threshold"]    = 25
    global_variables["js_axes"]         = [3,3,3]
    global_variables["js_dtzn"]         = 10
    global_variables["verbose"]         = False
    global_variables["motor_maxangle"]  = 120

    save_changes()
    exit(0)

def save_changes():
    with open(FNAME, "w+") as default_file:
        default_file.write(json.dumps(global_variables, indent=2))
    default_file.close()

def set(x, y):
    global_variables[x] = y

def load_settings():
    with open(FNAME, 'r') as f:
        return json.loads(f.read())

if __name__ == "__main__":
    if args.generate_defaults: generate_defaults()

    global_variables = load_settings()
    
    for arg, value in vars(args).items():
        if value is not None:
            if arg == "js_axes": value = [int(i) for i in value.split(',')]
            if arg == "verbose": value = bool(value.lower()=="true")
            try:
                set(str(arg), int(value))
            except Exception as e:
                set(str(arg), value)
        
    save_changes()
