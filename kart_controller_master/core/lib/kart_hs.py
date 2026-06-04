import cv2, numpy, math, time

markers = cv2.aruco

CALIBRATION_FILE = "core/lib/data/camera_distortion.yaml"

MULTIPLIER = 250

def get_center_position(plane_from_four_points: list):
    return numpy.mean(plane_from_four_points, axis=0)

def relative_distance(relative_coordinates, center):
    pos = round(MULTIPLIER * math.sqrt(abs(math.pow(relative_coordinates[0], 2) + math.pow(relative_coordinates[1], 2)))/(center))
    return pos if pos < 100 else (-100 if pos < -100 else 100)

def load_coef():
    cv_file = cv2.FileStorage(CALIBRATION_FILE, cv2.FILE_STORAGE_READ)
    return cv_file.getNode("K").mat(), cv_file.getNode("D").mat()


def kart_ARUCO_init():
    """ Inits CV2's ARUCO Module Detector """
    marker_dict =  markers.getPredefinedDictionary(markers.DICT_4X4_100)
    marker_params = markers.DetectorParameters()

    marker_params.adaptiveThreshWinSizeStep = 15
    marker_params.minMarkerPerimeterRate = 0.1
    marker_params.polygonalApproxAccuracyRate = 0.05

    return markers.ArucoDetector(marker_dict, marker_params)

def load_video_data():
    """ Runs a predefined routine to check for the screen's dimensions, distorsion coeffitients and video capture """
    cap = cv2.VideoCapture(0)

    k, d = load_coef()

    cam_dims = (1920, 1080)

    import platform

    if not "macos" in platform.platform(terse=True).lower():
        import os
        cap.release()

        cam_dims = (1280, 720)

        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        print("Linux Found, Setting Camera Correctly!")
        os.system("v4l2-ctl -d /dev/video0 --set-ctrl=auto_exposure=1")
        os.system("v4l2-ctl -d /dev/video0 --set-ctrl=exposure_time_absolute=150") 

        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_dims[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_dims[1])
        cap.set(cv2.CAP_PROP_FPS, 30)

        print(cv2.get(i) for i in [cv2.CAP_PROP_FOURCC, cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS])

    cam_center = (cam_dims[0]//2, cam_dims[1]//2)

    return cap, k, d, cam_dims, cam_center

class KartHeadsetInput:
    def __init__(self):
        self.detector = kart_ARUCO_init()
        self.cap, self.k, self.d, self.cam_dims, self.cam_center = load_video_data()
        self.map1, self.map2 = cv2.initUndistortRectifyMap(self.k, self.d, None, self.k, self.cam_dims, cv2.CV_16SC2)


    def show_grid(self, frame):
        frame = cv2.line(frame, [self.cam_center[0], 0], [self.cam_center[0], self.cam_dims[1]], (0, 0, 255), 5)
        frame = cv2.line(frame, [0, self.cam_center[1]], [self.cam_dims[0], self.cam_center[1]], (0, 0, 255), 5)
        

    def get_headset_position(self, show=False, undistort=False) -> tuple[int, numpy.int32]:

        ret, frame = self.cap.read()

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if undistort: frame = cv2.remap(frame, self.map1, self.map2, cv2.INTER_LINEAR)

        corners, ids, rejected = self.detector.detectMarkers(frame)

        set_center = False

        if show: 
            self.show_grid(frame)
            cv2.imshow("Headset Viewer", frame)            

            match cv2.waitKey(1):
                case 113:
                    self.stop_driving()
                    return 0, 0
                case 97:
                    print("Setting Center")
                    set_center = True

        if ids is not None:
            if set_center:
                center = get_center_position(corners[0][0]).astype(int);
                self.cam_center = (center[0], center[1]) 
            return ids[0][0], corners[0][0]
        else:   
            return -1, 0
        
    def stop_driving(self):
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    print("=== Running Headset Controller in DEBUG MODE ===")

    headset = KartHeadsetInput()

    center = [0,0]
    ts = 0

    try:
        while 1:

            hs_id, hs_pos = headset.get_headset_position(show=True)

            if hs_id == -1:
                continue
            elif hs_id == 0:
                break
            
            center = get_center_position(hs_pos)-headset.cam_center
            print((1 if center[0] < 0 else -1) * relative_distance(center, headset.cam_center[0]) )


    except KeyboardInterrupt:
        headset.stop_driving()