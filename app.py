from fastapi import FastAPI, Response, status
from config import stations, media_log, q, r
import tasks
import subprocess
import re


app = FastAPI()

@app.get('/stop')
def stop_radio():
    q.enqueue(tasks.stop_radio)
    return {'radio':'stopped'}


@app.get('/play/{station}')
def play_station(station: str, response: Response):
    if station in stations:
        cmd = stations[station]["cmd"]
        app_name = cmd.split(' ')[0]
        station_name = stations[station]["name"]
        q.enqueue(tasks.play_station, cmd, app_name, media_log)
        r.set('station', station_name)
        return {'playing': station_name}
    response.status_code = status.HTTP_404_NOT_FOUND
    return {'playing': False, 'station':'not found'}


@app.get('/change-volume/')
def change_volume(volume: str, response: Response):
    if volume in ['up','down','mute','unmute']:
        q.enqueue(tasks.change_volume, volume)
        return {'volume option': volume}
    response.status_code = status.HTTP_400_BAD_REQUEST
    return { 'valid query parameters': ['up','down','mute','unmute']}


@app.get('/get-title')
def get_title():
    cmd = f"cat {media_log} | grep -a StreamTitle | tail -n1 | cut -d ';' -f1 | cut -d '=' -f2 | cut -d ':' -f2,3,4"
    # cmd = f"cat {media_log} | grep -a StreamTitle | tail -n1 | cut -d '=' -f2 | cut -d ':' -f2,3,4"
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    title = p.stdout.read().decode('utf-8').strip()
    title = title.replace("';","'")
    station = r.get('station').decode('utf-8')
    print(title)
    if re.match('.*[a-zA-Z]+', title):
        return {'title': title, 'station': station}
    return {'title': 'unknown', 'station': station}


# mosquitto handler:
@app.get('/mosquitto-restart')
def mosquitto_restart():
    q.enqueue(tasks.mosquitto_restart)
    return {'mosquitto restarting': True}