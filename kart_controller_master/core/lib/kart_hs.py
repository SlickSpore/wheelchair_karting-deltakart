import cv2, os, mmap, sys, time, numpy, math, subprocess, platform, imutils
from imutils.video import VideoStream
  
bbox = (300, 100, 150, 200)
markers = cv2.aruco

this_os = platform.platform(terse=True).lower()

CALIBRATION_FILE = "core/lib/data/camera_distortion.yaml"
MARKER_DISTANCE_FACTOR = 7
CAMERA_WIDTH = 720
BYTES_PER_PIXEL = 4

FB_HEIGHT = 1920
FB_WIDTH = 1080

SCREEN_TYPE = cv2.COLOR_BGR2BGR565

MAX_OUT_BOUNDS = 500

def get_scr_reso():
    mode = subprocess.check_output(['fbset','-s']).decode().replace('"', '').replace(" ", "").replace("mode", "").split('\n')[1].split('x')
    return (int(mode[0]), int(mode[1])) 

def init_frame_buffer():
    global FB_HEIGHT, FB_WIDTH
    FB_WIDTH, FB_HEIGHT = get_scr_reso()
    fb = os.open("/dev/fb0", os.O_RDWR)
    fb_len = FB_WIDTH * FB_HEIGHT * BYTES_PER_PIXEL
    return fb, mmap.mmap(fb, length=fb_len, flags=mmap.MAP_SHARED, prot=mmap.PROT_WRITE | mmap.PROT_READ)

def draw_bbox(frame, bbox, type=0):
    p1_ = (int(bbox[0]), int(bbox[1]))
    p2_ = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
    color = (0, 255, 0) if type == 1 else (0, 0, 255)
    cv2.rectangle(frame, p1_, p2_, color, 2, 1)

def get_center_position(plane_from_four_points: list, axis=1):
    return numpy.mean(plane_from_four_points, axis=axis).astype(numpy.int32)

def kart_ARUCO_init():
    marker_dict =  markers.getPredefinedDictionary(markers.DICT_4X4_100)
    marker_params = markers.DetectorParameters()

    marker_params.adaptiveThreshWinSizeStep = 15
    marker_params.minMarkerPerimeterRate = 0.1
    marker_params.polygonalApproxAccuracyRate = 0.05

    return markers.ArucoDetector(marker_dict, marker_params)

def is_perpendicular(corners):
    base = ((corners[2][0]-corners[3][0])**2 + (corners[2][1]-corners[3][1])**2)
    height = ((corners[0][0]-corners[3][0])**2 + (corners[0][1]-corners[3][1])**2)

    diag1 = ((corners[0][0]-corners[2][0])**2 + (corners[0][1]-corners[2][1])**2)
    diag2 = ((corners[1][0]-corners[3][0])**2 + (corners[1][1]-corners[3][1])**2)

    return (max(base + height, diag1, diag2) - min(base + height, diag1, diag2)), math.sqrt(height)

def get_bounding_box_from_marker(corners, xc=70, yc=150):
    pts = corners[0].astype(numpy.int32)
    ret, height = is_perpendicular(pts[0])

    if ret:
        distance_factor = (height/CAMERA_WIDTH)*MARKER_DISTANCE_FACTOR
        center = get_center_position(corners[0])
        return (int(center[0][0]-(xc*distance_factor)), int(center[0][1] + (50*distance_factor)), int((2*xc * distance_factor)), int(yc*distance_factor))
    else:
        return None
    
def cvt_bb_to_rect(bbox):
    return (
        (bbox[0], bbox[1]),
        (bbox[0] + bbox[2], bbox[1]),
        (bbox[0], bbox[1] + bbox[3]),
        (bbox[0] + bbox[3], bbox[1] + bbox[3])
    )
            
def compute_distance(bbox, head_bbox):
    hs_c = get_center_position(cvt_bb_to_rect(head_bbox), axis=0)
    bb_c = get_center_position(cvt_bb_to_rect(bbox), axis=0)
    return bb_c - hs_c

def compute_steering_value(center, headset_center):
    val = 1-((center[0]-headset_center[0]-MAX_OUT_BOUNDS)/(center[0]-MAX_OUT_BOUNDS))
    return (1 if val >= 0 else -1) * (abs(val) if abs(val) < 1 else 1)

class KartHeadsetInput:
    def __init__(self, disp_fb = False):
        print("Loading KartHeadsetInput")
        if not "macos" in this_os:
            import os
            print("Linux Found, Setting Camera...")
            os.system("v4l2-ctl -d /dev/video0 --set-ctrl=auto_exposure=1")
            os.system("v4l2-ctl -d /dev/video0 --set-ctrl=exposure_time_absolute=150") 
            print("Done!")

            print("Initializing Frame Buffer")
            self.fd, self.fb = init_frame_buffer()
            print("Done!")

        self.show = disp_fb

        print("Loading Tracker")
        self.tracker = cv2.legacy.TrackerMOSSE_create()
        print("Done!")

        print("Loading ARUCO Detector")
        self.detector = kart_ARUCO_init()
        print("Done!")

        print("Starting Video Stream")
        self.vs = VideoStream(src=0, resolution=(1280, 720), framerate=30).start()
        print("Done!")

        time.sleep(1)
        corners = 0

        print("Waiting For ARUCO")

        while not corners:
            frame = self.vs.read()
            if frame is None:
                exit(-1)
            corners, _, _ = self.detector.detectMarkers(frame)
            
        print("Calib Done!")
        pts = corners[0].astype(numpy.int32)

        print("Getting Bounding Box")
        self.zero_bbox = get_bounding_box_from_marker(corners)

        self.position = numpy.array([0, 0])
        self.last_position = numpy.array([0, 0])
        
        self.frame_counter = 0
        self.correction_interval = 20  

        if self.zero_bbox is None:
            exit(-1)

        print("Drawing BBox")        
        draw_bbox(frame, self.zero_bbox, type=0)
        
        print("Drawing Marker")
        cv2.polylines(frame, [pts], True, (0,0,0), 8)

        print("Init Tracking")
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.tracker.init(frame_gray, self.zero_bbox)

    def tracker_correct(self, frame_gray):
        corners, _, _ = self.detector.detectMarkers(frame_gray)
        if corners is not None and len(corners) > 0:
            corrected = get_bounding_box_from_marker(corners)
            if corrected is not None:
                self.tracker = cv2.legacy.TrackerMOSSE_create()
                self.tracker.init(frame_gray, corrected)
                return corrected

    def drift_correction(self, frame_gray):
        self.frame_counter += 1
        if self.frame_counter % self.correction_interval != 0:
            return None

        speed = numpy.round((abs(self.last_position - self.position)) * (1/30), 2)
        if speed[0] > 0.10:
            return None

        self.tracker_correct(frame_gray)
        return None

    def get_center(self):
        return get_center_position(cvt_bb_to_rect(self.zero_bbox), axis=0)

    def get_head_position(self):
        frame = self.vs.read()
        if frame is None:
            return frame, -1, None
        
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        ret, headset_bbox = self.tracker.update(frame_gray)
        
        if ret:
            self.position = compute_distance(self.zero_bbox, headset_bbox)

            correction = self.drift_correction(frame_gray)
            if correction is not None:
                headset_bbox = correction
                self.position = compute_distance(self.zero_bbox, headset_bbox)

            self.last_position = self.position
            
            draw_bbox(frame, headset_bbox, type=1)
            return frame, headset_bbox, self.position
        else:
            self.tracker_correct(frame_gray)
            return frame, -1, None

    def stop_driving(self):
        if "macos" in this_os:
            cv2.destroyAllWindows()
        self.vs.stop()
        try:
            self.fd.close()
        except:
            pass

    def show_frame(self, frame):
        if not "macos" in this_os and self.show:
            self.fb.seek(0)
            resized = imutils.resize(frame, width=FB_WIDTH)
            self.fb.write(cv2.cvtColor(resized, SCREEN_TYPE).tobytes())
            return 0
        return 1

if __name__ == "__main__":
    hs = KartHeadsetInput(disp_fb=True, disp_calib=False)
    center = get_center_position(cvt_bb_to_rect(hs.zero_bbox), axis=0)

    while True:
        try:
            frame, headset_bbox, headset_center = hs.get_head_position()

            if headset_bbox == -1 or headset_center is None: 
                continue
            
            print(compute_steering_value(center, headset_center))

            if hs.show_frame(frame):
                cv2.imshow("headset", frame)
                if cv2.waitKey(1) == 27:
                    break
        except KeyboardInterrupt:
            break

    hs.stop_driving()