from typing import Dict
from fastapi import FastAPI, Response, status
from config import stations, media_log, r, q
from dataclasses import dataclass, field
import tasks
import subprocess
import re
import docker


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
    if radio.name is not None:
        q.enqueue(tasks.play_station, radio.cmd, radio.app_name, media_log)
        #tsk.add_task(tasks.play_station, radio.cmd, radio.app_name, media_log)
        r.set('station', radio.name)
        return {'playing': radio.name}
    response.status_code = status.HTTP_404_NOT_FOUND
    return {'playing': False, 'station':'not found'}


@app.get('/change-volume/')
def change_volume(volume: str, response: Response):
    if volume in ['up','down','mute','unmute']:
        q.enqueue(tasks.change_volume, volume)
        #tsk.add_task(tasks.change_volume, volume)
        return {'volume option': volume}
    response.status_code = status.HTTP_400_BAD_REQUEST
    return { 'valid query parameters': ['up','down','mute','unmute']}


@app.get('/stop')
def stop_radio():
    q.enqueue(tasks.stop_radio)
    #tsk.add_task(tasks.stop_radio)
    return {'radio':'stopped'}


@app.get('/get-title')
def get_title():
    cmd = f"cat {media_log} | grep -a StreamTitle | tail -n1 | cut -d ';' -f1 | cut -d '=' -f2 | cut -d ':' -f2,3,4"
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    title = p.stdout.read().decode('utf-8').strip()
    title = title.replace("';","'")
    station = r.get('station').decode('utf-8')
    if re.match('.*[a-zA-Z]+', title):
        return {'title': title, 'station': station}
    return {'title': 'unknown', 'station': station}


# mosquitto handler:
@app.get('/mosquitto-restart')
def mosquitto_restart():
    q.enqueue(tasks.mosquitto_restart)
    #tsk.add_task(tasks.mosquitto_restart)
    return {'mosquitto restarting': True}


@app.get('/docker-info')
def docker_info():
    client = docker.from_env()
    all_containers = client.containers.list(all=True)
    containers_status = [{"name":i.name, "status":i.status} for i in all_containers]
    return {'containers': containers_status}


@app.post('/docker-action')
def docker_action(request: Dict[str,str]):
    client = docker.from_env()
    cntr = client.containers.get(request['container'])
    if request['action'] == 'start':
        cntr.start()
        return {'action': 'started'}
    elif request['action'] == 'stop':
        cntr.stop()
        return {'action': 'stopped'}
    