import threading, collections, imutils, mmap, subprocess, os, platform, cv2, time, numpy, math
from imutils.video import VideoStream

is_macos = "macos" in platform.platform(terse=True).lower()

CAMERA_CALIBRATION_INTERVAL = .3#s 
SCREEN_TYPE = cv2.COLOR_BGR2BGR565

def resize_with_pad(image, target_width=1360, target_height=768):
    # 1. Prendi le dimensioni originali
    h, w = image.shape[:2]
    
    # 2. Calcola il fattore di scala mantenendo l'aspect ratio
    # Scegliamo il minimo per assicurarci che l'immagine entri perfettamente nel target
    scale = min(target_width / w, target_height / h)
    
    # Nuove dimensioni speculari al rapporto originale
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    # 3. Ridimensiona l'immagine originale
    resized_image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # 4. Crea una tela completamente nera delle dimensioni target (1360x768)
    # Se l'immagine è a colori, servono 3 canali (RGB)
    channels = image.shape[2] if len(image.shape) > 2 else 1
    padded_image = numpy.zeros((target_height, target_width, channels), dtype=numpy.uint8)
    
    # 5. Calcola le coordinate per centrare l'immagine ridimensionata sulla tela nera
    x_offset = (target_width - new_w) // 2
    y_offset = (target_height - new_h) // 2
    
    # 6. Incolla l'immagine ridimensionata sulla tela nera
    padded_image[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized_image
    
    return padded_image

def get_scr_reso():
    """Returns width and height of the target framebuffer"""
    try:
        mode = subprocess.check_output(['fbset', '-s']).decode().replace('"', '').replace(" ", "").replace("mode", "").split('\n')[1].split('x')
        return (int(mode[0]), int(mode[1]))
    except Exception:
        # Fallback default if fbset fails or isn't present
        return (1920, 1080)

def get_frame_buffer(shape):
    """Returns a frame buffer descriptor fb and the frame buffer pointer, fp"""
    import mmap
    width, height = get_scr_reso()
    fb = os.open("/dev/fb0", os.O_RDWR)
    fb_len = width * height * shape
    fp = mmap.mmap(fb, length=fb_len, flags=mmap.MAP_SHARED, prot=mmap.PROT_WRITE | mmap.PROT_READ)
    return fb, fp, width, height

def kart_ARUCO_init():
    markers = cv2.aruco

    marker_dict =  markers.getPredefinedDictionary(markers.DICT_4X4_100)
    marker_params = markers.DetectorParameters()

    marker_params.adaptiveThreshWinSizeStep = 15
    marker_params.minMarkerPerimeterRate = 0.1
    marker_params.polygonalApproxAccuracyRate = 0.05

    return markers.ArucoDetector(marker_dict, marker_params)

def is_perpendicular(pts):
    l1 = ((pts[2][0]-pts[3][0])**2 + (pts[2][1]-pts[3][1])**2)
    l2 = ((pts[0][0]-pts[3][0])**2 + (pts[0][1]-pts[3][1])**2)

    d1 = ((pts[0][0]-pts[2][0])**2 + (pts[0][1]-pts[2][1])**2)
    d2 = ((pts[1][0]-pts[3][0])**2 + (pts[1][1]-pts[3][1])**2)

    return (max(l1 + l2, d1, d2) - min(l1 + l2, d1, d2)), math.sqrt(l2)

def get_mid_point_from_rect(plane_from_four_points: list, axis=1):
    return numpy.mean(plane_from_four_points, axis=axis).astype(numpy.int32)

def get_headset_bb_from_marker(corners, height, xc=40, yc=80, distance=10):

    ret, l1 = is_perpendicular(corners[0])

    if ret:
        correction = (l1/height)*distance
        center = get_mid_point_from_rect(corners)
        return (int(center[0][0]-(xc*correction)), int(center[0][1] + (50*correction)), int((2*xc * correction)), int(yc*correction))
    else:
        return None
    
def draw_bbox(frame, bbox, type=0):
    p1_ = (int(bbox[0]), int(bbox[1]))
    p2_ = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
    color = (0, 255, 0) if type == 1 else (0, 0, 255)
    cv2.rectangle(frame, p1_, p2_, color, 5, 1)

def draw_marker(frame, marker):
    cv2.polylines(frame, [marker], True, (0,255,0), 8)


def draw_grid(frame, width, height, center):
    return cv2.line(cv2.line(frame, (0, center[1]), (width, center[1]), (255,255,0), 6), (center[0], 0), (center[0], height), (255,255,0), 6)

def convert_bb_to_rect(bbox):
    return (
        (bbox[0], bbox[1]),
        (bbox[0] + bbox[2], bbox[1]),
        (bbox[0], bbox[1] + bbox[3]),
        (bbox[0] + bbox[2], bbox[1] + bbox[3])
    )

def compute_distance(bbox, head_bbox):
    hs_c = get_mid_point_from_rect(convert_bb_to_rect(head_bbox), axis=0)
    bb_c = get_mid_point_from_rect(convert_bb_to_rect(bbox), axis=0)
    return bb_c - hs_c

def compute_steering_value(center, headset_center, max_bounds=350):
    c_x = center[0] if isinstance(center, (list, numpy.ndarray, tuple)) else center
    val = 1 - ((c_x - headset_center[0] - max_bounds) / (c_x - max_bounds))
    return round((-100 if val <= 0 else 100) * (abs(val) if abs(val) < 1 else 1),2)

def draw_max_bounds(img, home, value, width, height):

    center = get_mid_point_from_rect(convert_bb_to_rect(home), axis=0)[0]

    cv2.line(img, (center-value, 0), (center-value, height), (255,0,0), 2)
    cv2.line(img, (center+value, 0), (center+value, height), (255,0,0), 2)

class KartHeadsetInput:
    def bbox_finder_helper(self):

        time.sleep(1)

        while self.__running:
            if self.captures is not None:
                try:
                    with self.lock:
                        current_img = self.captures[-1].copy() if len(self.captures) > 0 else None

                    if current_img is not None:
                        detected_markers_list = self.detector.detectMarkers(current_img)[0]

                        marker_corners = detected_markers_list[0].astype(numpy.int32)

                        with self.lock:
                            self.current_hs_center.append(marker_corners)

                        if len(detected_markers_list) > 0 and (self.speed < 0.01 or self.tracker_lost):
                            self.tracker_correct(marker_corners)
                except Exception as e:
                    ...
            time.sleep(CAMERA_CALIBRATION_INTERVAL)

    def show_frame(self):
        ...
    
    def tracker_correct(self, corners):
        with self.lock:
            if hasattr(self, 'frame_gray') and self.frame_gray is not None:
                self.tracker.append(cv2.legacy.TrackerMOSSE_create())
                self.tracker[-1].init(self.frame_gray, get_headset_bb_from_marker(corners, self.video_height))
                self.tracker_lost = False

    def __init__(self, disp_fb=False):
        self.lock = threading.Lock()
        self.captures = collections.deque(maxlen=10)
        self.current_hs_center = collections.deque(maxlen=10)
        self.detector = kart_ARUCO_init()
        self.position = numpy.array([0, 0])
        self.last_position = self.position
        self.tracker = collections.deque(maxlen=10)
        self.tracker.append(cv2.legacy.TrackerMOSSE_create())
        self.frame_interval = 0
        self.max_bounds = 350
        self.video_width, self.video_height = 1920, 1080
        self.fb_w, self.fb_h = self.video_width, self.video_height
        self.disp_fb = disp_fb
        self.speed = 0 
        self.frame_gray = None 
        self.frame_buffer = None
        self.time_previous = 0
        
        self.video_stream = cv2.VideoCapture(0)

        if not is_macos:

            self.video_stream = None
            
            print("Linux Found, Setting Camera...")
            os.system("v4l2-ctl -d /dev/video0 --set-ctrl=auto_exposure=1")
            os.system("v4l2-ctl -d /dev/video0 --set-ctrl=exposure_time_absolute=50") 
            print("Done!")

            print("Initializing Frame Buffer...")
            self.frame_buffer_handle, self.frame_buffer, self.fb_w, self.fb_h = get_frame_buffer(2)
            self.video_width, self.video_height = 1280, 720
            print(f"Frame Buffer Initialized at {self.fb_w}x{self.fb_h}")
            self.video_stream = cv2.VideoCapture(0, cv2.CAP_V4L2)
            self.video_stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            self.video_stream.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.video_stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.video_stream.set(cv2.CAP_PROP_FPS, 30)

            

        #self.video_stream = VideoStream(src=0, usePiCamera=False, resolution=(self.video_width, self.video_height), framerate=30).start()

        self.__running = True

        time.sleep(1)

        print("waiting for aruco")
        while 1:
            ret, img = self.video_stream.read()
            if img is None:
                print("Camera Error!")
                exit()
            detected_markers_list, _, _ = self.detector.detectMarkers(img)

            if len(detected_markers_list):
                break

        calibration_marker_corners = detected_markers_list[0].astype(numpy.int32)
        self.home_position = get_headset_bb_from_marker(calibration_marker_corners, self.video_height)
        self.tracker[-1].init(img, self.home_position)

        self.camera_helper = threading.Thread(target=self.bbox_finder_helper, daemon=True)
        self.camera_helper.start()

    def yield_hs_position(self):
        try:
            while self.__running:
                self.time_now = time.time()
                self.frame_interval += 1
                ret, self.img = self.video_stream.read()

                if self.img is None:
                    continue
                
                with self.lock:
                    self.captures.append(self.img.copy())
                    self.frame_gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
                    ret, headset_bbox = self.tracker[-1].update(self.frame_gray)

                if ret:
                    self.position = compute_distance(self.home_position, headset_bbox)
                    self.speed = abs(self.last_position[0] - self.position[0]) * (1/30)
                    self.last_position = self.position
                    sv = compute_steering_value(self.home_position, self.position, max_bounds=self.max_bounds)
                else:
                    print("lost")
                    self.tracker_lost = True
                    sv = 0
                    
                if self.disp_fb:
                    with self.lock:
                        if self.current_hs_center:
                            draw_marker(self.img, self.current_hs_center[-1])
                    
                    # steering value
                    cv2.putText(self.img, f"FPS:{int(1/(self.time_now-self.time_previous))}", (30, 120), cv2.FONT_HERSHEY_COMPLEX, 1, (0,255,255), 3)
                    cv2.putText(self.img, f"Steering Value: {sv}", (30, 90), cv2.FONT_HERSHEY_COMPLEX, 1, (0,255,255), 3)
                    
                    # max bound
                    draw_max_bounds(self.img, self.home_position, self.max_bounds, self.fb_w, self.fb_h)
                    draw_bbox(self.img, headset_bbox, type=0)
                    draw_grid(self.img, self.fb_w, self.fb_h, get_mid_point_from_rect(convert_bb_to_rect(self.home_position), axis=0))

                    if is_macos:
                        cv2.imshow("Headset Viewer", self.img)
                        # FIX: Se premi ESC, chiudi tutto correttamente prima di uscire
                        if cv2.waitKey(1) == 27:
                            cv2.destroyAllWindows()
                            self.stop_driving()
                            return

                    else:
                        if self.frame_buffer is not None:
                            self.frame_buffer.seek(0)
                            resized = resize_with_pad(self.img)
                            self.frame_buffer.write(cv2.cvtColor(resized, SCREEN_TYPE).tobytes())

                self.time_previous=self.time_now
                yield sv
        except KeyboardInterrupt:
            self.stop_driving()

    def stop_driving(self):
        if not self.__running:
            return
        print("Stopping driver and releasing resources...")
        self.__running = False
        self.video_stream.stop()
        if hasattr(self, 'camera_helper') and self.camera_helper.is_alive():
            self.camera_helper.join()
        if self.frame_buffer is not None:
            self.frame_buffer.close()
        print("Clean exit done.")

if __name__ == "__main__":
    ks = KartHeadsetInput(disp_fb=True)

    for position in ks.yield_hs_position():
        print(position)

    ks.stop_driving()