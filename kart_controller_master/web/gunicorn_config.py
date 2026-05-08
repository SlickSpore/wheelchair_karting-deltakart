def on_starting(server):
    import subprocess
    subprocess.run(["bash", "web/access_point/ap_start.sh"])
