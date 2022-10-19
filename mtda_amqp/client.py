import os
import zerorpc
import socket
import pika 
import uuid
import random

from mtda_amqp.main import MTDA_AMQP
import mtda_amqp.constants as CONSTS

class Client:

    def __init__(self,remote,session=None):
   
        agent=MTDA_AMQP()
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
        self._agent = agent
        self._impl= self.call
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

    def console_dump(self):
        return self._impl.console_dump(self._session)

    def console_print(self, data):
        return self._impl.console_print(data, self._session)

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

    def pastebin_api_key(self):
        return self._agent.pastebin_api_key()

    def start(self):
        return self._agent.start()

    def stop(self):
        if self._agent.remote is not None:
            self._impl.close()
        else:
            self._agent.stop()

    def storage_close(self):
        return self._impl.storage_close(self._session)

    def storage_locked(self):
        return self._impl.storage_locked(self._session)

    def storage_mount(self, part=None):
        return self._impl.storage_mount(part, self._session)

    def storage_open(self):
        tries = 60
        while tries > 0:
            tries = tries - 1
            status = self._impl.storage_open(self._session)
            if status is True:
                return True
            time.sleep(1)
        return False

    def storage_status(self):
        return self._impl.storage_status(self._session)

    def target_locked(self):
        return self._impl("target_locked(%s)"%(self._session))


    def remote(self):
        return self._agent.remote

    def session(self):
        return self._session
        
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




