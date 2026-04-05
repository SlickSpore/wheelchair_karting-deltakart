from matplotlib import pyplot as plt
import numpy as np
import pandas
import os
from scipy.ndimage import median_filter

FREQUENCY = 24

def load_data(fname=None):
    if fname is None:
        return
    data = pandas.read_csv(fname)
    return data

def smooth_data(data, kernel_size=100):
    for i in data:
        data[i] = median_filter(data[i], size=kernel_size)

def generate_plot(data: pandas.DataFrame):

    smooth_data(data)

    y = np.linspace(3,len(data["ACC_X"])/FREQUENCY + 3,len(data["ACC_X"]))
    fig, axs = plt.subplots(3,1)

    fig.canvas.manager.set_window_title("Kart_Headset_Data_Analisis")

    axs[0].plot(y, np.array([data["ACC_X"], data["ACC_Y"], data["ACC_Z"]]).T)
    axs[0].set_title("Accelerometer")
    axs[0].grid(True)
    axs[0].legend(["X_ACC", "Y_ACC", "Z_ACC"])

    axs[1].plot(y, np.array([data["ROLL"], data["PITCH"], data["YAW"]]).T)
    axs[1].set_title("Gyroscope")
    axs[1].grid(True)
    axs[1].legend(["ROLL", "PITCH", "YAW"])

    axs[2].plot(y, data["HEAD_A"], color='red')
    axs[2].set_title("Head_Data")
    axs[2].grid(True)
    axs[2].legend(["Head_Tilt"])

    plt.tight_layout()
    plt.show()

def main():
    pname = input("Insert Project Name: ")
    data = load_data(f"data/{pname}/sensor_data.csv")
    generate_plot(data)

if __name__ == "__main__":
    main()