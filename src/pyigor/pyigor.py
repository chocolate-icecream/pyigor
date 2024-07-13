import os
import logging
import threading
import queue
import uuid
import subprocess
import re, ast, json, glob, platform
from typing import List

import flask
from flask import Flask
import h5py
import numpy as np

my_platform = "mac" if platform.platform(terse=True).startswith("macOS") else ("windows" if platform.platform(terse=True).startswith("Windows") else None)

def alphanumeric_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key, reverse=True)

##### OS dependent codes #####
def find_executable_path():
    exe_path_dict = {"mac": os.path.join("/Applications", "Igor Pro * Folder", "Igor64.app", "Contents", "MacOS", "Igor64"),
                    "windows": os.path.join(os.environ.get("ProgramFiles"), "WaveMetrics", "Igor Pro * Folder", "IgorBinaries_x64", "Igor64.exe")}

    path_candidates = glob.glob(exe_path_dict[my_platform])
    assert len(path_candidates) > 0, "Cannot find Igor Pro"

    exe_path = alphanumeric_sort(path_candidates)[0] # get the newest version
    return exe_path

def execute_command_on_my_platform(command, executable_path):
    if my_platform == "mac":
        subprocess.run([executable_path, "-Q", "-X", command])
    if my_platform == "windows":
        temp = subprocess.list2cmdline([executable_path, "-Q", "-X"])
        subprocess.run(f"{temp} {command}")

def convert_to_igor_path(path):
    return path.replace(os.path.sep, ":")
##### OS dependent codes #####


class Connection:
    TIMEOUT = 3
    ### security_hole options makes it possible to execute any Python code by HTTP requests. Do not use unless you are sure of it.
    def __init__(self, port=15556, security_hole=False, timeout=3):
        self._app = Flask(__name__)
        self._task_queue = queue.Queue(maxsize=1) # set of (command, uid)
        self._queue = queue.Queue(maxsize=1) # set of (status, uid, data_dict or None)
        self._port = port
        self._registered_functions = {"get": self.get, "put": self.put, "print": print}
        self._basepath = os.getcwd()
        self._executable_path = find_executable_path()
        self._security_hole = security_hole
        self.TIMEOUT = timeout
        
        self._register_route()
        threading.Thread(target=self._run_server, daemon=True).start()

    def reset(self):
        try:
            self._queue.put_nowait(("error", 0, None))
        except:
            pass
        try:
            self._queue.get_nowait()
        except:
            pass
        try:
            self._task_queue.get_nowait()
        except:
            pass

    def __call__(self, commands):
        if isinstance(commands, str):
            commands = [commands]
        for c in commands:
            c = c.replace("'", "\"")
            self.execute_command(c)    
    
    def get(self, wavename):
        uid = uuid.uuid1().hex
        try:
            self._task_queue.put(("get", uid), timeout=self.TIMEOUT)
        except queue.Full:
            return
        
        self.execute_command(f"PyIgorOutputWave({self._port}, \"{uid}\", \"{wavename}\", \"{self._temp_path(True)}\")")
        result = None
        try:
            reply = self._queue.get(timeout=self.TIMEOUT)
            if reply[0] == "ok":
                assert reply[1] == uid, "Error: Request-response ID does not match."
                result = Wave.from_dict(reply[2])
            
        except queue.Empty:
            pass
        assert self._task_queue.get_nowait() == ("get", uid)
        return result

    def put(self, wave, wavename="", x0=0, dx=1):
        uid = uuid.uuid1().hex
        try:
            self._task_queue.put(("put", uid), timeout=self.TIMEOUT)
        except queue.Full:
            return
        with h5py.File(self._temp_path(), "w") as f:
            dset = f.create_dataset(uid, data=wave)
        self.execute_command(f"PyIgorLoadWave({self._port}, \"{uid}\", \"{wavename}\", \"{self._temp_path(True)}\", 0)")
        try:
            result = self._queue.get(timeout=self.TIMEOUT)
        except queue.Empty:
            result = None
        assert self._task_queue.get_nowait() == ("put", uid)
        return result

    def _run_server(self):
        log = logging.getLogger('werkzeug') 
        log.setLevel(logging.ERROR)
        flask.cli.show_server_banner = lambda *args: None
        self._app.run(port=self._port)
        
    def _register_route(self):
        @self._app.route("/")
        def index():
            return "<p>Bridging Igor and Python</p>"

        @self._app.route("/msg/<string:msg>/<string:uid>")
        def got_message(msg, uid):
            if msg == "get":
                result = self._process_get(uid)
                self._queue.put_nowait(result)
            if msg == "put":
                self._queue.put_nowait(("ok", uid, None))
            if msg == "error":
                self._queue.put_nowait(("error", uid, None))
            return "<p>Bridging Igor and Python</p>"

        @self._app.route("/call/<string:commands>")
        def call_command(commands):
            result_list = []
            p = re.compile(r"([\w]+)\(([^\)]*)\)")
            for command in commands.split(";"):
                try:
                    if self._security_hole:
                        result_list.append(eval(command)) # eval is used to execute any Python code.
                    else:
                        m = re.match(p, command)
                        if m is None:
                            continue
                        fname, args = m.groups()
                        args = ast.literal_eval(f"[{args}]")
                        if fname in self._registered_functions:
                            result_list.append(self._registered_functions[fname](*args))
                except Exception as e:
                    print(e)
                    result_list.append(f"error:{command}")
            return ";".join([str(x) for x in result_list if x is not None])

    def _process_get(self, uid):
        with h5py.File(self._temp_path(), mode="r") as f:
            result_dict = {"array": f[uid][...]}
            attrs = f[uid].attrs
            if "IGORWaveScaling" in attrs:
                result_dict["offsets"] = list(attrs["IGORWaveScaling"][1:, 1])
                result_dict["deltas"] = list(attrs["IGORWaveScaling"][1:, 0])
            else: # IGORWaveScaling is omitted for default parameters
                result_dict["offsets"] = [0.0] * len(result_dict["array"].shape)
                result_dict["deltas"] = [1.0] * len(result_dict["array"].shape)
        return ("ok", uid, result_dict)
    
    def _temp_path(self, for_igor=False):
        path = os.path.join(self._basepath, f"temp_pyigor_{self._port}.h5")
        if for_igor:
            path = convert_to_igor_path(path)
        return path

    
    def execute_command(self, command):
        execute_command_on_my_platform(command, self._executable_path)

    def wait_done(self):
        try:
            while True:
               if input("Input q to finish:") == "q":
                   break
        except KeyboardInterrupt:
            pass
    
    ### Wrapper functions ###
    def function(self, f):
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)
        self._registered_functions[f.__name__] = f
        return wrapper

class Wave:
    def __init__(self, array, offsets: List[float], deltas: List[float], units: str=""):
        if isinstance(array, list):
            array = np.array(list)
        self.array = array
        self.offsets = offsets
        self.deltas = deltas
        self.units = units
    
    @classmethod
    def from_dict(cls, d):
        wave = Wave(**d)
        return wave

    @property
    def shape(self):
        return self.array.shape

    @property
    def numpnts(self):
        return self.array.size
    
    @property
    def deltax(self):
        return self.deltas[0]

    @property
    def leftx(self):
        return self.offsets[0]

    @property
    def x(self):
        return np.linspace(self.leftx, self.leftx+self.deltax*self.shape[0], self.shape[0], endpoint=False)

    def __repr__(self):
        return f"<pyigor.Wave shape: {self.shape}, data_type: {self.array.dtype}>"

