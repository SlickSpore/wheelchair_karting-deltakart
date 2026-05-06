import serial, enum, struct, math, time

class PacketDataTypes(enum.Enum):
    AGM_DATA = 0x1704
    QTR_DATA      = 0x1516
    ATT_DATA      = 0x1126

PACKET_BEGIN    = 0x7e23
ACC_SCALE       = 16/32767.0
GYRO_SCALE      = (2000/32767.0)*(math.pi/180.0)
MAG_SCALE       = 800/32767.0


def connect_headset(port):
    return serial.Serial(port, baudrate=115200)

def get_byte(x):
    return int(x.read().hex(),16)

def to_word(x, y):
    return ((x << 8) | y)

def get_packet_type(header) -> PacketDataTypes:
    match header:
        case PacketDataTypes.AGM_DATA.value:
            return PacketDataTypes.AGM_DATA
        case PacketDataTypes.QTR_DATA.value:
            return PacketDataTypes.QTR_DATA
        case PacketDataTypes.ATT_DATA.value:
            return PacketDataTypes.ATT_DATA

def get_data(packet_type: PacketDataTypes, headset):
    match packet_type:
        case PacketDataTypes.AGM_DATA:
            return struct.unpack("hhhhhhhhhc", headset.read(19))
        case PacketDataTypes.QTR_DATA:
            return struct.unpack("ffffc", headset.read(17))
        case PacketDataTypes.ATT_DATA:
            return struct.unpack("fffc", headset.read(13))

def convert_data(packet_type, data):
    match packet_type:
        case PacketDataTypes.AGM_DATA:
            ax, ay, az, gx, gy, gz, mx, my, mz, _ = data
            return ax*ACC_SCALE, ay*ACC_SCALE, az*ACC_SCALE, gx*GYRO_SCALE, gy*GYRO_SCALE, gz*GYRO_SCALE, mx*MAG_SCALE, my*MAG_SCALE, mz*MAG_SCALE
        case PacketDataTypes.QTR_DATA:
            q0, q1, q2, q3, _ = data
            return q0, q1, q2, q3
        case PacketDataTypes.ATT_DATA:
            roll, pitch, yaw, _ = data
            return roll, pitch, yaw

def set_sensor_speed(sensor: serial.Serial, speed):
    hf = "hhhB"
    data = struct.pack(hf, 0x237e, 0x6007, (0x5f<<8)|speed, 0xff)
    time.sleep(1)
    for i in range(200):
        sensor.write(data)
        time.sleep(1/200)


class KartHeadset:
    def __init__(self):
        self.hs = connect_headset("/dev/tty.usbserial-11210")
        self.last_packet = 0
        self.data = None
        self.ptype = None

        set_sensor_speed(self.hs, 10)

    def update(self):
        packet = get_byte(self.hs)
        if to_word(self.last_packet, packet) == PACKET_BEGIN:
            header = to_word(get_byte(self.hs), get_byte(self.hs))
            self.ptype = get_packet_type(header)
            if self.ptype is PacketDataTypes.AGM_DATA:
                raw_data = get_data(self.ptype, self.hs)
                self.data = convert_data(self.ptype, raw_data)
        self.last_packet = packet
            
    def get_accelerometer_data(self):
        if self.ptype is PacketDataTypes.AGM_DATA:
            ax, ay, az, _, _, _, _, _, _ = self.data
            return ax, ay, az
        else:
            return -1
        
    def get_gyroscope_data(self):
        if self.ptype is PacketDataTypes.AGM_DATA:
            _, _, _, gx, gy, gz, _, _, _ = self.data
            return gx, gy, gz
        else:
            return -1

if __name__ == "__main__":
    hs = KartHeadset()
    old_time = time.time()
    while KeyboardInterrupt:
        t_now = time.time()
        hs.update()
        if hs.ptype is PacketDataTypes.AGM_DATA:
            hs.get_accelerometer_data()
        print(t_now-old_time)
        old_time = t_now
