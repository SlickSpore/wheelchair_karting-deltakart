import serial, enum, struct, math, time, numpy

class PacketDataTypes(enum.Enum):
    AGM_DATA      = 0x1704
    QTR_DATA      = 0x1516
    ATT_DATA      = 0x1126
    MPU_RESP      = 0x0781

class IMUCommands(enum.Enum):
    SET_REPORT_SPEED = 0x60
    IMU_CALIB        = 0x70

PACKET_BEGIN    = 0x7e23
ACC_SCALE       = 16/32767.0
GYRO_SCALE      = (2000/32767.0)*(math.pi/180.0)
MAG_SCALE       = 800/32767.0
CAP_SPEED       = 25

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
        case PacketDataTypes.MPU_RESP.value:
            return PacketDataTypes.MPU_RESP

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


def send_command(sensor, command, parameter1, parameter2=0x5f):
    data = [0x7e, 0x23, 0x00, command, parameter1, parameter2]
    data[2] = len(data) + 1
    checksum = 0xff & sum(data)
    data.append(checksum)
    data = bytes(data)
    sensor.write(data)

class KartHeadset:
    def __init__(self, port):
        self.hs = connect_headset(port)
        self.last_packet = 0
        self.data = None
        self.ptype = None

        self.data_frames = []

        send_command(self.hs, IMUCommands.SET_REPORT_SPEED.value, CAP_SPEED)

    def update(self):
        packet = get_byte(self.hs)
        if to_word(self.last_packet, packet) == PACKET_BEGIN:
            header = to_word(get_byte(self.hs), get_byte(self.hs))
            self.ptype = get_packet_type(header)
            if self.ptype is PacketDataTypes.AGM_DATA:
                raw_data = get_data(self.ptype, self.hs)
                self.data = convert_data(self.ptype, raw_data)
        self.last_packet = packet
            
    def get_accelerometer_data(self, precision=2):
        if self.ptype is PacketDataTypes.AGM_DATA:
            ax, ay, az, _, _, _, _, _, _ = self.data
            return [round(i,precision) for i in [ax, ay, az]]
        else:
            return -1
        
    def get_gyroscope_data(self, precision=2):
        if self.ptype is PacketDataTypes.AGM_DATA:
            _, _, _, gx, gy, gz, _, _, _ = self.data
            return [round(i,precision) for i in [gx, gy, gz]]
        else:
            return -1
        
    def smooth_acc_data(self, amount, precision=2):
        x, y, z = self.data
        self.data_frames.append([x, y, z])
        if len(self.data_frames)>amount:
            while len(self.data_frames)>amount:
                del self.data_frames[0]
        x, y, z = 0,0,0

        for i, e in enumerate(self.data_frames):
            x += self.data_frames[i][0]
            y += self.data_frames[i][1]
            z += self.data_frames[i][2]

        del self.data_frames [0]

        return [round(i,precision) for i in ([x, y, z]/amount)]
        

if __name__ == "__main__":
    hs1 = KartHeadset("/dev/tty.usbserial-1210")
    hs2 = KartHeadset("/dev/tty.usbserial-130")
    a1x, a1y, a1z = 0,0,0
    a2x, a2y, a2z = 0,0,0
    while KeyboardInterrupt:
        hs1.update()
        hs2.update()
        if hs1.ptype is PacketDataTypes.AGM_DATA:
            a1x, a1y, a1z = hs1.get_accelerometer_data()
        if hs2.ptype is PacketDataTypes.AGM_DATA:
            a2x, a2y, a2z = hs2.get_accelerometer_data()
        print(f"IMU1:\t{a1x},\t{a1y},\t{a1z}\tIMU2:\t{a2x},\t{a2y},\t{a2z}")
        