import subprocess


def stop_radio():
    kill_proc = subprocess.Popen(['pkill', '(mpg123|ffplay)'])
    kill_proc.communicate()


def play_station(cmd: str, app_name:str, media_log: str):
    stop_radio()
    if app_name == 'mpg123':
        subprocess.Popen(f"{cmd} > {media_log} 2>&1", shell=True)
    elif app_name == 'ffplay':
        subprocess.Popen(f"/bin/bash -c '{cmd} 2> >( stdbuf -oL awk /StreamTitle/ | tee {media_log} )'", shell=True)


def change_volume(volume: str):
    cmd = "amixer -c 0 | egrep '\[[0-9]+%\]' -o | cut -d '[' -f2 | cut -d '%' -f1"
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    current_volume = int(p.stdout.read().decode('utf-8').strip())
    volume_option = {
        'up': current_volume +1,
        'down': current_volume -1,
        'unmute': 95,
        'mute': 0
    }
    set_option = volume_option.get(volume, None)
    cmd = f"amixer set -c 0 Headphone {set_option}%"
    subprocess.Popen(cmd, shell=True)

# mosquitto handler:
def mosquitto_restart():
    subprocess.Popen("docker restart mosquitto 2>&1 > /dev/null", shell=True)