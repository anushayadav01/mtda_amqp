import os
import zerorpc
import socket

from mtda_mqtt.main import MTDAMqtt
import mtda_mqtt.constants as CONSTS

class Client:

    def __init__(self, host=None, session=None):
        agent = MTDAMqtt()
        agent.load_config(host)
        if agent.remote is not None:
            uri = "tcp://%s:%d" %(agent.remote, agent.ctrlport)
            self._impl = zerorpc.Client(heartbeat=CONSTS.RPC.HEARTBEAT, timeout=CONSTS.RPC.TIMEOUT)
            self._impl.connect(uri)

        else:
            self._impl = agent
        self._agent = agent

        if session is None:
            HOST = socket.gethostname()
            USER = os.getenv("USER")
            WORDS = "/usr/share/dict/words"
            if os.path.exists(WORDS):
                WORDS = open(WORDS).read().splitlines()
                name = random.choice(WORDS)
                if name.endswith("'s"):
                    name = name.replace("'s"," ")
            elif USER is not None and HOST is not None:
                name = "%s@%s" % (USER, HOST)
            else:
                name = "mtda-mqtt"
            self._session = os.getenv('MTDA_SESSION', name)
        else:
            self._session = session


    def start(self):
        return self._agent.start()


    def remote(self):
        return self._agent.remote




