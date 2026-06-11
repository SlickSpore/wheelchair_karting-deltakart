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

SCREEN_TYPE = cv2.COLOR_GRAY2BGR565

MAX_OUT_BOUNDS = 500

def get_scr_reso():
    """
    Requires fbctl
    """
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
    cv2.rectangle(frame, p1_, p2_, (255 * type,0,255*(not type)), 2, 1)

def get_center_position(plane_from_four_points: list, axis=1):
    return numpy.mean(plane_from_four_points, axis=axis).astype(numpy.int32)

def kart_ARUCO_init():
    """ Inits CV2's ARUCO Module Detector """
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
    def __init__(self, disp_calib = False, disp_fb = False):
        print("Loading KartHeadsetInput")
        if not "macos" in this_os:
            disp_calib = False
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

        if self.zero_bbox is None:
            exit(-1)

        print("Drawing BBox")        
        draw_bbox(frame, self.zero_bbox, type=0)
        print("Drawing Marker")
        cv2.polylines(frame, [pts], True, (0,0,0), 8)

        print("Showing Data")
        if disp_calib:
            while 1:
                cv2.imshow("headset_view", frame)
                k = cv2.waitKey(1) & 0xff
                if k == 27 : 
                    break
        
        print("Init Tracking")
        self.tracker.init(frame, self.zero_bbox)

    def get_head_position(self):
        frame = self.vs.read()

        if frame is None:
            return frame, -1, None
        
        draw_bbox(frame, self.zero_bbox, type=0)

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        ret, headset_bbox = self.tracker.update(frame)
        
        if ret:
            draw_bbox(frame, headset_bbox, type=1)
            return frame, headset_bbox, compute_distance(self.zero_bbox, headset_bbox)
        else:
            return frame, -1, None

    def stop_driving(self):
        if "macos" in this_os:
            cv2.destroyAllWindows()
        self.vs.stop()
        self.fd.close()

    def show_frame(self, frame):
        if not "macos" in this_os and self.show:
            self.fb.seek(0)
            self.fb.write(cv2.cvtColor(imutils.resize(frame, width=FB_WIDTH), SCREEN_TYPE).tobytes())
            return 0
        return 1

if __name__ == "__main__":

    hs = KartHeadsetInput(disp_fb=True, disp_calib=False)

    center = get_center_position(cvt_bb_to_rect(hs.zero_bbox), axis=0)

    while KeyboardInterrupt:
        frame, headset_bbox, headset_center = hs.get_head_position()

        if headset_bbox == -1: 
            continue
        
        print(compute_steering_value(center, headset_center))

        if hs.show_frame(frame):
            cv2.imshow("headset", frame)
            if cv2.waitKey(1) == 27:
                break

    hs.stop_driving()

def old():

    tracker = cv2.legacy.TrackerMOSSE_create()

    video = cv2.VideoCapture(0)
 
    if not video.isOpened():
        print ("Could not open video")
        sys.exit()
 
    ret, frame = video.read()
    ret, frame = video.read()
    ret, frame = video.read()
    ret, frame = video.read()
    frame = cv2.resize(frame, (1280,720))
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    if not ret:
        print ('Cannot read video file')
        sys.exit()

    #bbox = cv2.selectROI(frame, False) 

    tracker.init(frame, bbox)
 
    while True:
        ret, frame = video.read()

        frame = cv2.resize(frame, (1280,720))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


        ret, bbox = tracker.update(frame)

        if not ret:
            break
 
        if ret:
            p1 = (int(bbox[0]), int(bbox[1]))
            p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
            cv2.rectangle(frame, p1, p2, (255,0,0), 2, 1)
        else :
            cv2.putText(frame, "Tracking failure detected", (100,80), cv2.FONT_HERSHEY_SIMPLEX, 0.75,(0,0,255),2)
 
        cv2.imshow("Tracking", frame)
 
        k = cv2.waitKey(1) & 0xff
        if k == 27 : break