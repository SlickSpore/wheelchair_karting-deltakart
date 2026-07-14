import headset_run.HeadsetRun as hs
import time

runner = hs.HeadsetRun()
print(runner.connect_camera())

while KeyboardInterrupt:
    ts = time.time()
    pos = runner.get_headset_position()
    if pos[0] == -1:
        break
    print(pos, time.time()-ts)