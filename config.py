from rq import Queue
import redis
import os

r = redis.Redis()
q = Queue(connection=r)

cwd = os.path.dirname(__file__)
media_log = os.path.join(cwd, "logs/media_log.log")

stations = {
    "antyradio": {
        "name":"Antyradio",
        "cmd": "ffplay https://an.cdn.eurozet.pl/ant-waw.mp3 -nodisp"
    },
    "chili-zet": {
        "name":"Chili ZET",
        "cmd": "ffplay https://ch.cdn.eurozet.pl/chi-net.mp3 -nodisp"
    },
    "radio-kampus": {
        "name":"Radio Kampus",
        "cmd": "mpg123 http://193.0.98.66:8005"
    },
    "radio-kolor": {
        "name":"Radio Kolor",
        "cmd": "ffplay http://stream.radiojar.com/xt0cf1v8938uv -nodisp"
    },
    "radio-eska": {
        "name":"Radio Eska",
        "cmd": "mpg123 http://waw01-01.ic.smcdn.pl:8000/2380-1.mp3"
    },
    "newonce-radio": {
        "name":"newonce.radio",
        "cmd": "ffplay https://streamer.radio.co/s93b51ccc1/listen -nodisp"
    },
    "zet-80": {
        "name":"Zet 80",
        "cmd": "ffplay https://zt.cdn.eurozet.pl/ZET080.mp3 -nodisp"
    },
    "zet-hits": {
        "name":"Zet Hits",
        "cmd": "ffplay https://zt.cdn.eurozet.pl/ZETHIT.mp3 -nodisp"
    },
    "zet-alternative": {
        "name":"Zet alternative",
        "cmd": "ffplay https://zt.cdn.eurozet.pl/ZETALT.mp3 -nodisp"
    },
    "wefunk-radio": {
        "name":"WeFunk radio",
        "cmd": "mpg123 http://s-10.wefunkradio.com:81/wefunk64.mp3"
    }

}
