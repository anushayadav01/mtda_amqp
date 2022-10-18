import os
import zerorpc
import socket
import pika 
import uuid

from mtda_amqp.main import MTDA_AMQP

class Client:

    def __init__(self,remote):
        agent=MTDA_AMQP()
        '''
        agent.load_config(host, config_files=config_files)
        if agent.remote is not None:
            uri = "tcp://%s:%d" % (agent.remote, agent.ctrlport)
            self._impl = zerorpc.Client(heartbeat=CONSTS.RPC.HEARTBEAT,
                                        timeout=CONSTS.RPC.TIMEOUT)
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
                    name = name.replace("'s", "")
            elif USER is not None and HOST is not None:
                name = "%s@%s" % (USER, HOST)
            else:
                name = "mtda"
            self._session = os.getenv('MTDA_SESSION', name)
        else:
            self._session = session
        '''
        self._agent = agent
        self.remote=remote
        self.connection = pika.BlockingConnection(pika.URLParameters('amqp://admin:password@%s:5672'%(str(self.remote))))
        self.channel = self.connection.channel()
        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue
        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)
        self.response = None
        self.corr_id = None

    def console_remote(self, host, screen):
        return self._agent.console_remote(host, screen)
    
    def console_getkey(self):
        return self._agent.console_getkey()

    def console_send(self, data, raw=False):
        return self._impl.console_send(data, raw, self._session)

    def console_prefix_key(self):
        return self._agent.console_prefix_key()

    def monitor_remote(self, host, screen):
        return self._agent.monitor_remote(host, screen)

    def monitor_send(self, data, raw=False):
        return self._impl.monitor_send(data, raw, self._session)
        
    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, n):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
              exchange='',
              routing_key='mtda-amqp',
              properties=pika.BasicProperties(
                  reply_to=self.callback_queue,
                  correlation_id=self.corr_id,
            ),
        body=str(n))
        self.connection.process_data_events(time_limit=None)
        return self.response




