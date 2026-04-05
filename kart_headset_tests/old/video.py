import cv2, time

def set_camera_and_video(fname):
    cap = cv2.VideoCapture(1)

    if not cap.isOpened():
        print("[!] Unable to open Webcam! Quitting")
        exit(-1)

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(fname, fourcc, 20.0, (frame_width, frame_height))

    return cap, out

def write_frame(cap, out):
    ret, frame = cap.read()
    # cv2.imshow('Webcam', frame)
    out.write(frame)

def check_quit():
    if cv2.waitKey(1) & 0xFF == ord('q'):
        return True
    return False
    

def close_videos(cap, out):
    cap.release()
    out.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    video_capture, video_output = set_camera_and_video("output.avi")

    while True:
        ts = time.time()
        write_frame(video_capture, video_output)
        te = time.time()

        print(ts-te)

        if check_quit():
            break

    close_videos(video_capture, video_output)
