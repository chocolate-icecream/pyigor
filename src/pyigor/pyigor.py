import os
import logging
import threading
import queue
import uuid
import subprocess
import re, ast, json, glob

import flask
from flask import Flask
import h5py

class Connection:
    def __init__(self, port=15556):
        self._app = Flask(__name__)
        self._task_queue = queue.Queue(maxsize=1)
        self._queue = queue.Queue(maxsize=1)
        self._port = port
        self._registered_functions = {"get": self.get, "put": self.put, "print": print}
        self._basepath = os.getcwd()
        self._executable_path = self._find_executable_path()
        
        self._register_route()
        threading.Thread(target=self._run_server, daemon=True).start()
    
    def _find_executable_path(self):
        # config_path = os.path.join(os.path.dirname(__file__), "config", "config.json")
        exe_path = None
        # config = {}
        # try:
        #     with open(config_path, "r") as f:
        #         config = json.load(f)
        #     if "executable_path" in config and len(config["executable_path"]) > 0:
        #         exe_path = config["executable_path"]
        # except:
        #     pass
        # if exe_path is None:
        path_candidates = glob.glob("/Applications/Igor Pro*/Igor64.app/Contents/MacOS/Igor64")
        assert len(path_candidates) > 0, "Cannot find Igor Pro"
        exe_path = path_candidates[0]
            # config["executable_path"] = exe_path
            # with open(config_path, "w") as f:
            #     json.dump(config, f)
        return exe_path
    
    def get(self, wavename):
        uid = uuid.uuid1().hex
        try:
            self._task_queue.put(("get", uid), timeout=10)
        except queue.Full:
            return
        
        self.execute_command(f"PyIgorOutputWave({self._port}, \"{uid}\", \"{wavename}\", \"{self._temp_path(True)}\")")
        result = None
        try:
            reply = self._queue.get(timeout=10)
            if reply[0] == "ok":
                assert reply[1] == uid, "Error: Request-response ID does not match."
                result = Wave.from_dict(reply[2])
            
        except queue.Empty:
            pass
        assert self._task_queue.get_nowait() == ("get", uid)
        return result

    def put(self, wave, wavename=""):
        uid = uuid.uuid1().hex
        try:
            self._task_queue.put(("put", uid), timeout=10)
        except queue.Full:
            return
        with h5py.File(self._temp_path(), "w") as f:
            dset = f.create_dataset(uid, data=wave)
        self.execute_command(f"PyIgorLoadWave({self._port}, \"{uid}\", \"{wavename}\", \"{self._temp_path(True)}\", 0)")
        try:
            result = self._queue.get(timeout=10)
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
                self._queue.put_nowait(("ok", uid))
            if msg == "error":
                self._queue.put_nowait(("error", uid))
            return "<p>Bridging Igor and Python</p>"

        @self._app.route("/call/<string:commands>")
        def call_command(commands):
            result_list = []
            p = re.compile(r"([\w]+)\(([^\)]*)\)")
            for command in commands.split(";"):
                try:
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
        return ("ok", uid, result_dict)
    
    def _temp_path(self, for_igor=False):
        path = os.path.join(self._basepath, f"temp_pyigor_{self._port}.h5")
        if for_igor:
            path = path.replace(os.path.sep, ":")
        return path

    
    def execute_command(self, command):
        subprocess.run([self._executable_path, "-Q", "-X", command])

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
        self._registered_functions[f.__name__] == f
        return wrapper

class Wave:
    def __init__(self, array):
        self.array = array
    
    @classmethod
    def from_dict(cls, d):
        wave = Wave(d["array"])
        return wave
    
    def __str__(self):
        return f"<Wave shape:{self.array.shape}, data_type:{self.array.dtype}>"

if __name__ == "__main__":
    igor = Connection()
    igor.wait_done()

