import cv2, math
import numpy as np

SRC_PTH = "core/lib/data/marker.png"

MRK_PTH = "core/lib/data/angled_markers"

ALPHA = 10

mrk = cv2.imread(SRC_PTH)

def tilt(angle):
    s = 100/math.cos(math.radians(angle))

    w, h, _ = mrk.shape

    white = np.full((w+100, h+100, 3), 255, dtype=np.uint8)


    t_init = np.float32(
        [[0, 0], [w, 0],
        [0, h], [w, h]]
    )

    t_dest = np.float32(
        [[0, 0], [w, 0],
        [s, h-s+100], [w-s, h-s+100]]
    )

    M = cv2.getPerspectiveTransform(t_init, t_dest)
    t_mrk = cv2.warpPerspective(mrk, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(255,255,255))

    white[50:50+w, 50:50+h] = t_mrk

    cv2.imwrite(f"{MRK_PTH}/mrk_{angle}.png", white)


if __name__ == "__main__":
    for i in [10, 20, 30, 40, 45]:
        tilt(i)