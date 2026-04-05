import time
import matplotlib.pyplot as plt
from scipy.ndimage import median_filter
import numpy as np

def load_source():
    with open("recording_1775311857.data", "r") as f:
        return f.readlines()

def print_data(x):
    return '='*(10+(int(x/10))) + "X" + '='*(10-(int(x/10)))

if __name__ == "__main__":
    data = load_source()
    head_position = [float(i.strip().split(":")[1]) for i in data]
    raw_kart_position = [(i.strip().split(":")[0].replace("[", "").replace("]", "").split(" ")) for i in data]

    kart_position = []

    for i, e in enumerate(raw_kart_position):
        s = []
        for j, f in enumerate(e):
            if f != '':
                s.append(float(f))
        kart_position.append(s)

    xs = [kart_position[i][0] for i in range(0,len(kart_position))]
    ys = [kart_position[i][1] for i in range(0,len(kart_position))]
    zs = [kart_position[i][2] for i in range(0,len(kart_position))]

    xs = median_filter(xs, size=100)
    ys = median_filter(ys, size=100)
    zs = median_filter(zs, size=100)
    hs = median_filter(head_position, size=100)

    new_data = []

    for i in range(0,len(kart_position)):
        new_data.append([xs[i], ys[i], zs[i]])

    plt.plot([i for i in range(0, len(kart_position))], [i + [e/250] for i, e in zip(new_data, hs)])
    plt.legend(["x","y","z", "head"])
    plt.grid(True, which="both", axis="both")
    plt.show()

    counter = 0.0

    for i in head_position:
        print(round(counter,2), 's:', print_data(i), end='\r')
        time.sleep(1/100)
        counter += 0.01
    