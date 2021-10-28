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
    all_containers = client.containers.list(all=True)
    containers_status = { i.name:i.status for i in all_containers }
    return containers_status


@app.get('/redis-info')
def redis_info():
    keys = subprocess.Popen('redis-cli keys \*', shell=True, stdout=subprocess.PIPE)
    k_output = keys.stdout.read().decode('utf-8').replace('\n',' ')
    values = subprocess.Popen(f'redis-cli mget {k_output}', shell=True, stdout=subprocess.PIPE)
    v_output = values.stdout.read().decode('utf-8')
    k_arr = k_output.split(' ')
    v_arr = v_output.split('\n')

    for idx,i in enumerate(v_arr):
        v_arr[idx] = None if len(i) == 0 else i

    redis_output = {k:v for k,v in zip(k_arr, v_arr) if v is not None}
    return redis_output


@app.post('/docker-action')
def docker_action(request: Dict[str,str]):
    cntr = client.containers.get(request['container'])
    if request['action'] == 'start':
        cntr.start()
        return {'action': 'started'}
    elif request['action'] == 'stop':
        cntr.stop()
        return {'action': 'stopped'}


@app.get('/mqtt-handler')
def mqtt_handler():
    cmd = 'docker logs mqtt_handler -n20000 2>&1 | grep \'"topic":"zigbee2mqtt/Termometr"\''
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    text = p.stdout.read().decode('utf-8').strip()
    str_obj = str(text.split('\n'))
    formatted_str = str_obj.replace("['","[").replace("']","]").replace('}"',"}").replace('"{',"{").replace("'","")
    obj = json.loads(formatted_str)
    for i in obj:
        date_val = datetime.strptime(i['timestamp'],'%Y-%m-%d %H:%M:%S,%f')
        i['timestamp'] = date_val.timestamp()
    return obj


@app.get('/mqtt-handler-new')
def mqtt_handler_new():
    #ctr = list(filter(lambda x: x.name == 'mqtt_handler', client.containers.list(all=True)))[0]
    ctr = [i for i in client.containers.list(all=True) if 'mqtt_handler' in i.name][0]
    log_content = ctr.logs().decode('utf-8')
    all_lines = log_content.split('\n')
    filtered = [line for line in all_lines if '"topic":"zigbee2mqtt/Termometr"' in line]
    json_output = str(filtered)
    json_str = json_output.replace("'","").replace('\\','')
    obj = json.loads(json_str)
    for i in obj:
        date_val = datetime.strptime(i['timestamp'],'%Y-%m-%d %H:%M:%S,%f')
        i['timestamp'] = date_val.timestamp()
    return obj


@app.get('/door-state')
def door_state():
    try:
        state = r.get('door_state').decode('utf-8')
    except:
        return {'door_state': 'unknown'}
    return { 'door_state': state }
