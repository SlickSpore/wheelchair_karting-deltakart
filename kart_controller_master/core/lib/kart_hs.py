import threading
import collections
import subprocess
import os
import platform
import cv2
import time
import numpy
import math

IS_MACOS = "macos" in platform.platform(terse=True).lower()

CAMERA_CALIBRATION_INTERVAL = 0.5
SCREEN_TYPE = cv2.COLOR_BGR2BGR565


def resize_with_pad(image, target_width=1360, target_height=768):
    h, w = image.shape[:2]
    scale = min(target_width / w, target_height / h)
    new_w, new_h = int(w * scale), int(h * scale)
    
    resized_image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    channels = image.shape[2] if len(image.shape) > 2 else 1
    padded_image = numpy.zeros((target_height, target_width, channels), dtype=numpy.uint8)
    
    x_offset = (target_width - new_w) // 2
    y_offset = (target_height - new_h) // 2
    padded_image[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized_image
    return padded_image


def get_scr_reso():
    try:
        mode = subprocess.check_output(['fbset', '-s']).decode().replace(' ', '').split('\n')[1].split('x')
        return int(mode[0].split('-')[-1]), int(mode[1].split('geometry')[-1])
    except Exception:
        return 1920, 1080


def get_frame_buffer(shape):
    import mmap
    width, height = get_scr_reso()
    fb = os.open("/dev/fb0", os.O_RDWR)
    fb_len = width * height * shape
    fp = mmap.mmap(fb, length=fb_len, flags=mmap.MAP_SHARED, prot=mmap.PROT_WRITE | mmap.PROT_READ)
    return fb, fp, width, height


def kart_ARUCO_init():
    markers = cv2.aruco
    marker_dict = markers.getPredefinedDictionary(markers.DICT_4X4_100)
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
        correction = (l1 / height) * distance
        center = get_mid_point_from_rect(corners)
        return (int(center[0][0] - (xc * correction)), int(center[0][1] + (50 * correction)), 
                int(2 * xc * correction), int(yc * correction))
    return None


def draw_bbox(frame, bbox, type_box=0):
    p1_ = (int(bbox[0]), int(bbox[1]))
    p2_ = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
    color = (0, 255, 0) if type_box == 1 else (0, 0, 255)
    cv2.rectangle(frame, p1_, p2_, color, 5, 1)


def draw_marker(frame, marker):
    cv2.polylines(frame, [marker], True, (0, 255, 255), 8)


def draw_grid(frame, width, height, center):
    cv2.line(frame, (0, center[1]), (width, center[1]), (0, 255, 0), 6)
    cv2.line(frame, (center[0], 0), (center[0], height), (0, 255, 0), 6)
    return frame


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


def compute_steering_value(center, headset_center, max_bounds=40):
    val = headset_center[0]/max_bounds
    return round((-100 if val <= 0 else 100) * (abs(val) if abs(val) < 1 else 1), 2)


def draw_max_bounds(img, home, value, width, height):
    center = get_mid_point_from_rect(convert_bb_to_rect(home), axis=0)[0]
    cv2.line(img, (center - value, 0), (center - value, height), (0, 255, 0), 2)
    cv2.line(img, (center + value, 0), (center + value, height), (0, 255, 0), 2)


def load_logo(path="web/static/logo.jpg"):
    logo = cv2.imread(path)

    logo = cv2.resize(logo, (1400//4, 434//4))

    return logo


def apply_logo(img, logo):
    h_logo, w_logo, _ = logo.shape
    h_bg, w_bg, _ = img.shape

    x_offset = (w_bg//2) - (w_logo//2)
    y_offset = 10

    img[y_offset:y_offset + h_logo, x_offset:x_offset + w_logo] = logo

    return img


class KartHeadsetInput:
    def __init__(self, cam_ex=50, disp_fb=False):
        self.lock = threading.Lock()
        self.__running = True
        
        self.current_img = None
        self.frame_gray = None
        self.tracker_lost = False
        self.speed = 0
        self.cam_ex = cam_ex
        
        self.current_hs_center = collections.deque(maxlen=10)
        self.detector = kart_ARUCO_init()
        self.position = numpy.array([0, 0])
        self.last_position = self.position
        
        self.tracker = collections.deque(maxlen=10)
        self.tracker.append(cv2.legacy.TrackerMOSSE_create())

        self.max_bounds = 150
        self.video_width, self.video_height = 1920, 1080
        self.fb_w, self.fb_h = self.video_width, self.video_height
        self.disp_fb = disp_fb
        self.frame_buffer = None
        self.time_previous = time.time()

        self.logo = load_logo()

        if not IS_MACOS:
            print("Linux Found, Setting Camera...")
            os.system("v4l2-ctl -d /dev/video0 --set-ctrl=auto_exposure=1")
            os.system(f"v4l2-ctl -d /dev/video0 --set-ctrl=exposure_time_absolute={self.cam_ex}")
            print("Initializing Frame Buffer...")
            self.frame_buffer_handle, self.frame_buffer, self.fb_w, self.fb_h = get_frame_buffer(2)
            self.video_width, self.video_height = 1280, 720
            self.video_stream = cv2.VideoCapture(0, cv2.CAP_V4L2)
            self.video_stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        else:
            self.video_stream = cv2.VideoCapture(0)

        self.video_stream.set(cv2.CAP_PROP_FRAME_WIDTH, self.video_width)
        self.video_stream.set(cv2.CAP_PROP_FRAME_HEIGHT, self.video_height)
        self.video_stream.set(cv2.CAP_PROP_FPS, 30)

        time.sleep(1)

        print("Waiting for ArUco calibration...")
        while True:
            ret, img = self.video_stream.read()
            if not ret or img is None:
                print("Camera Error during calibration!")
                exit()
            detected_markers_list, _, _ = self.detector.detectMarkers(img)
            if len(detected_markers_list) > 0:
                break

        calibration_marker_corners = detected_markers_list[0].astype(numpy.int32)
        self.home_position = get_headset_bb_from_marker(calibration_marker_corners, self.video_height)
        self.tracker[-1].init(img, self.home_position)

        self.camera_reader_thread = threading.Thread(target=self._frame_reader_worker, daemon=True)
        self.camera_reader_thread.start()

        self.aruco_helper_thread = threading.Thread(target=self._bbox_finder_worker, daemon=True)
        self.aruco_helper_thread.start()

    def _frame_reader_worker(self):
        while self.__running:
            ret, img = self.video_stream.read()
            if ret and img is not None:
                # OPTIMIZATION: Do the color conversion *outside* of the lock to prevent blocking other threads
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                with self.lock:
                    self.current_img = img
                    self.frame_gray = gray
            else:
                time.sleep(0.001)

    def _bbox_finder_worker(self):
        while self.__running:
            img_to_process = None
            gray_to_process = None
            
            with self.lock:
                if self.current_img is not None:
                    img_to_process = self.current_img # No .copy() here, just point to array
                    gray_to_process = self.frame_gray
                current_speed = self.speed
                is_lost = self.tracker_lost

            if img_to_process is not None:
                try:
                    corners_list, _, _ = self.detector.detectMarkers(img_to_process)
                    if len(corners_list) > 0:
                        marker_corners = corners_list[0].astype(numpy.int32)

                        if (current_speed < 0.1 and abs(self.position[0]) < 10) or is_lost:
                            print("Resetting position:", self.position[0], current_speed, is_lost)
                            if gray_to_process is not None:
                                new_tracker = cv2.legacy.TrackerMOSSE_create()
                                new_bbox = get_headset_bb_from_marker(marker_corners, self.video_height)
                                if new_bbox:
                                    new_tracker.init(gray_to_process, new_bbox)
                                    with self.lock:
                                        self.tracker.append(new_tracker)
                                        self.tracker_lost = False
                        
                        # Kept out of tracker lock to prevent main execution thread stalls
                        with self.lock:
                            self.current_hs_center.append(marker_corners)
                except Exception as e:
                    print(f"Error in ArUco thread: {e}")
            
            time.sleep(CAMERA_CALIBRATION_INTERVAL)

    def yield_hs_position(self):
        try:
            while self.__running:
                time_now = time.time()
                
                img = self.current_img # Removed performance-heavy .copy()

                if img is None:
                    continue

                gray = self.frame_gray
                if len(self.tracker) > 0:
                    active_tracker = self.tracker[-1] 

                # Lock context narrowed strictly down to tracking mathematical update
                ret, headset_bbox = active_tracker.update(gray)

                if ret:
                    self.position = compute_distance(self.home_position, headset_bbox)
                    with self.lock:
                        self.speed = abs(self.last_position[0] - self.position[0]) * (1.0 / 30.0)
                    self.last_position = self.position
                    sv = compute_steering_value(self.home_position, self.position, max_bounds=self.max_bounds)
                else:
                    with self.lock:
                        self.tracker_lost = True
                    sv = 0

                if self.disp_fb:
                    # Work on a local clone *only* if rendering UI to prevent altering the global image pointer
                    ui_img = img.copy() 
                    
                    with self.lock:
                        has_center = len(self.current_hs_center) > 0
                        if has_center:
                            latest_center = self.current_hs_center[-1]
                    
                    if has_center:
                        draw_marker(ui_img, latest_center)

                    draw_max_bounds(ui_img, self.home_position, self.max_bounds, self.fb_w, self.fb_h)
                    
                    if ret:
                        draw_bbox(ui_img, headset_bbox, type_box=0)
                    
                    draw_grid(ui_img, self.fb_w, self.fb_h, get_mid_point_from_rect(convert_bb_to_rect(self.home_position), axis=0))

                    apply_logo(ui_img, self.logo)

                    fps = int(1.0 / (time_now - self.time_previous)) if (time_now - self.time_previous) > 0 else 0
                    cv2.putText(ui_img, f"FPS: {fps}", (30, 120), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 255), 3)
                    cv2.putText(ui_img, f"Steering: {sv}", (30, 90), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 255), 3)

                    if IS_MACOS:
                        cv2.imshow("Headset Viewer", ui_img)
                        if cv2.waitKey(1) == 27:
                            self.stop_driving()
                            return
                    else:
                        if self.frame_buffer is not None:
                            self.frame_buffer.seek(0)
                            resized = resize_with_pad(ui_img)
                            self.frame_buffer.write(cv2.cvtColor(resized, SCREEN_TYPE).tobytes())

                self.time_previous = time_now
                yield sv

        except KeyboardInterrupt:
            self.stop_driving()

    def stop_driving(self):
        if not self.__running:
            return
        
        print("\nStopping driver and releasing resources...")
        self.__running = False
        
        if hasattr(self, 'video_stream') and self.video_stream is not None:
            self.video_stream.release()
            
        if IS_MACOS:
            cv2.destroyAllWindows()
            
        if self.frame_buffer is not None:
            self.frame_buffer.close()

        print("Clean exit done.")


if __name__ == "__main__":
    ks = KartHeadsetInput(disp_fb=True)
    try:
        for position in ks.yield_hs_position():
            print(f"Steering Output: {position}")
    except KeyboardInterrupt:
        pass
    finally:
        ks.stop_driving()
