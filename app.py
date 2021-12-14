from typing import Dict
from fastapi import FastAPI, Response, status
from config import stations, media_log, r, q
from dataclasses import dataclass, field
import tasks
import subprocess
import re
import json
import docker
from datetime import datetime


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
client = docker.from_env()


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
    try:
        cmd = f"cat {media_log} | grep -a StreamTitle | tail -n1 | cut -d ';' -f1 | cut -d '=' -f2 | cut -d ':' -f2,3,4"
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        title = p.stdout.read().decode('utf-8').strip()
        title = title.replace("';","'")
        station = r.get('station').decode('utf-8')
    except AttributeError:
        return {'title': 'unknown', 'station': 'unknown'}
    else:
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
def docker_info(items: str):
    if items == 'containers':
        ctrs = client.containers.list(all=True)
        return { i.name:i.status for i in ctrs }
    elif items == 'images':
        imgs = client.images.list()
        output = []
        [ output.extend(i.tags) for i in imgs ]
        return { 'images': output }


@app.get('/redis-info')
def redis_info():
    keys = r.keys()
    values = r.mget(keys)
    output = {}
    for k, v in zip(keys, values):
        if v is None:
            continue
        key = k.decode('utf-8')
        val = v.decode('utf-8')
        if "{" in val:
            obj = json.loads(val)
            if type(obj) is list:
                obj = obj[len(obj) - 1]
            output.update({key: obj})
        else:
            output.update({key: val})
    return output


@app.get('/get-redis-data')
def get_redis_data(data: str):
    try:
        payload = r.get(data).decode('utf-8')
    except:
        return { data: 'Not found' }
    if '{' in payload:
        return Response(content=payload, media_type='application/json')
    return { 'payload': payload }