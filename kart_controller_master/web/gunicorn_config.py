# Web Server's Configuration File

ACCESS_POINT_STARTUP_ROUTINE_PATH = "web/access_point/ap_start.sh"
BACKUP_ACCESS_POINT_STARTUP_ROUTINE_PATH = "/usr/local/bin/ap_start.sh"

def on_starting(server):
    import subprocess
    subprocess.run(["bash", ACCESS_POINT_STARTUP_ROUTINE_PATH])
    subprocess.run(["bash", BACKUP_ACCESS_POINT_STARTUP_ROUTINE_PATH])
