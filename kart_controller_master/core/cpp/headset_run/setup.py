from setuptools import setup, Extension
import pybind11
import subprocess


opencv_cflags = subprocess.check_output(
    ["pkg-config", "--cflags", "opencv4"]
).decode().strip().split()

opencv_libs = subprocess.check_output(
    ["pkg-config", "--libs", "opencv4"]
).decode().strip().split()


ext_modules = [
    Extension(
        "HeadsetRun",
        ["headset_run/headset_run.cpp"],

        include_dirs=[
            pybind11.get_include(),
        ],

        extra_compile_args=[
            "-std=c++17",
        ] + opencv_cflags,

        extra_link_args=[
            "-Wl,-undefined,dynamic_lookup",
        ] + opencv_libs,

        language="c++",
    )
]


setup(
    name="HeadsetRun",
    version="0.1",
    ext_modules=ext_modules,
)