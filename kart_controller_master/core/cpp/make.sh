python3 headset_run/setup.py build_ext --inplace

rm -rf build/

mv *.so headset_run/

python3 main.py