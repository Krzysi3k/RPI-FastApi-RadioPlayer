from fastapi import FastAPI, Response, status
import uvicorn
from config import stations, media_log, q, r
from dataclasses import dataclass, field
import tasks
import subprocess
import re


@dataclass(frozen=True)
class Station:
    uri_name: str
    name: str = field(init=False)
    cmd: str = field(init=False)
    app_name: str = field(init=False)

    def __post_init__(self):
        try:
            object.__setattr__(self, 'name', stations[self.uri_name]["name"])
            object.__setattr__(self, 'cmd', stations[self.uri_name]["cmd"])
            object.__setattr__(self, 'app_name', self.cmd.split(' ')[0])
        except KeyError:
            object.__setattr__(self, 'name', None)
            object.__setattr__(self, 'cmd', None)
            object.__setattr__(self, 'app_name', None)


app = FastAPI()


@app.get('/play/{station}')
def play_station(station: str, response: Response):
    radio = Station(station)
    print(123)
    if radio.name is not None:
        q.enqueue(tasks.play_station, radio.cmd, radio.app_name, media_log)
        r.set('station', radio.name)
        return {'playing': radio.name}
    response.status_code = status.HTTP_404_NOT_FOUND
    return {'playing': False, 'station':'not found'}


@app.get('/change-volume/')
def change_volume(volume: str, response: Response):
    if volume in ['up','down','mute','unmute']:
        q.enqueue(tasks.change_volume, volume)
        return {'volume option': volume}
    response.status_code = status.HTTP_400_BAD_REQUEST
    return { 'valid query parameters': ['up','down','mute','unmute']}


@app.get('/stop')
def stop_radio():
    q.enqueue(tasks.stop_radio)
    return {'radio':'stopped'}


@app.get('/get-title')
def get_title():
    cmd = f"cat {media_log} | grep -a StreamTitle | tail -n1 | cut -d ';' -f1 | cut -d '=' -f2 | cut -d ':' -f2,3,4"
    # cmd = f"cat {media_log} | grep -a StreamTitle | tail -n1 | cut -d '=' -f2 | cut -d ':' -f2,3,4"
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    title = p.stdout.read().decode('utf-8').strip()
    title = title.replace("';","'")
    station = r.get('station').decode('utf-8')
    # print(title)
    if re.match('.*[a-zA-Z]+', title):
        return {'title': title, 'station': station}
    return {'title': 'unknown', 'station': station}


# mosquitto handler:
@app.get('/mosquitto-restart')
def mosquitto_restart():
    q.enqueue(tasks.mosquitto_restart)
    return {'mosquitto restarting': True}