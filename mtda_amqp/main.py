#!/usr/bin/env python
import pika
import os,sys,time,threading
from mtda_amqp.console.remote import RemoteConsole, RemoteMonitor
import mtda_amqp.constants as CONSTS
from mtda_amqp.console.input import ConsoleInput
import json
DEFAULT_PREFIX_KEY = 'ctrl-a'
DEFAULT_PASTEBIN_EP = "http://pastebin.com/api/api_post.php"

class MTDA_AMQP(object):

    def __init__(self):
        self.connection = pika.BlockingConnection(pika.URLParameters('amqp://admin:password@134.86.62.153:5672'))
        self.channel = self.connection.channel()
        
        self.channel.queue_declare(queue='mtda-amqp')
        self.channel.queue_purge(queue='mtda-amqp')
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue='mtda-amqp', on_message_callback=self.on_request)
        self.monitor = None
        self.monitor_logger = None
        self.monitor_output = None
        self.debug_level = 0
        self.is_remote = False
        self.console_output = None
        self.conport = 5557
        self.ctrlport = 5556
        self.prefix_key = self._prefix_key_code(DEFAULT_PREFIX_KEY)
        self._sessions = {}
        self._session_lock = threading.Lock()
        self._session_timeout=CONSTS.SESSION.MIN_TIMEOUT
        self._lock_owner= None
        self.storage_controller = None

    def debug(self, level, msg):
        if self.debug_level >= level:
            if self.debug_level == 0:
                prefix = "# "
            else:
                prefix = "# debug%d: " % level
            msg = str(msg).replace("\n", "\n%s ... " % prefix)
            lines = msg.splitlines()
            sys.stderr.buffer.write(prefix.encode("utf-8"))
            for line in lines:
                sys.stderr.buffer.write(_make_printable(line).encode("utf-8"))
                sys.stderr.buffer.write(b"\n")
                sys.stderr.buffer.flush()

    def console_prefix_key(self):
        self.mtda.debug(3, "main.console_prefix_key()")
        return self.prefix_key

    def _prefix_key_code(self, prefix_key):
        prefix_key = prefix_key.lower()
        key_dict = {'ctrl-a': '\x01', 'ctrl-b': '\x02', 'ctrl-c': '\x03',
                    'ctrl-d': '\x04', 'ctrl-e': '\x05', 'ctrl-f': '\x06',
                    'ctrl-g': '\x07', 'ctrl-h': '\x08', 'ctrl-i': '\x09',
                    'ctrl-j': '\x0A', 'ctrl-k': '\x0B', 'ctrl-l': '\x0C',
                    'ctrl-n': '\x0E', 'ctrl-o': '\x0F', 'ctrl-p': '\x10',
                    'ctrl-q': '\x11', 'ctrl-r': '\x12', 'ctrl-s': '\x13',
                    'ctrl-t': '\x14', 'ctrl-u': '\x15', 'ctrl-v': '\x16',
                    'ctrl-w': '\x17', 'ctrl-x': '\x18', 'ctrl-y': '\x19',
                    'ctrl-z': '\x1A'}

        if prefix_key in key_dict:
            key_ascii = key_dict[prefix_key]
            return key_ascii
        else:
            raise ValueError("the prefix key specified '{0}' is not "
                             "supported".format(prefix_key))
    

    def _check_locked(self, session):
        #self.mtda.debug(3, "main._check_locked()")
        owner = self.target_owner()
        if owner is None:
            return False
        status = False if session == owner else True
        return status

    def console_init(self):
        self.console_input = ConsoleInput()
        self.console_input.start()

    def console_send(self, data, raw=False, session=None):
        self.mtda.debug(3, "main.console_send()")
        self._session_check(session)
        result = None
        if self.console_locked(session) is False and \
           self.console_logger is not None:
            result = self.console_logger.write(data, raw)

        self.mtda.debug(3, "main.console_send(): %s" % str(result))

    def console_locked(self, session=None):
        self.mtda.debug(3, "main.console_locked()")

        self._session_check(session)
        result = self._check_locked(session)

        self.mtda.debug(3, "main.console_locked(): %s" % str(result))
        return result


    def console_getkey(self):
        self.mtda.debug(3, "main.console_getkey()")
        result = None
        try:
            result = self.console_input.getkey()
        except AttributeError:
            print("Initialize the console using console_init first")
        self.mtda.debug(3, "main.console_getkey(): %s" % str(result))
        return result


    def console_remote(self, host, screen):
        self.mtda.debug(3, "main.console_remote()")

        result = None
        if self.is_remote is True:
            # Stop previous remote console
            if self.console_output is not None:
                self.console_output.stop()
            if host is not None:
                # Create and start our remote console
                self.console_output = RemoteConsole(host, self.conport, screen)
                self.console_output.start()
            else:
                self.console_output = None

        self.mtda.debug(3, "main.console_remote(): %s" % str(result))


    def _session_check(self, session=None):
        #self.mtda.debug(3, "main._session_check(%s)" % str(session))

        events = []
        now = time.monotonic()
        power_off = False
        result = None

        with self._session_lock:
            # Register new session
            if session is not None:
                if session not in self._sessions:
                    events.append("ACTIVE %s" % session)
                self._sessions[session] = now + self._session_timeout

            # Check for inactive sessions
            inactive = []
            for s in self._sessions:
                left = self._sessions[s] - now
                #self.mtda.debug(3, "session %s: %d seconds" % (s, left))
                if left <= 0:
                    inactive.append(s)
            for s in inactive:
                events.append("INACTIVE %s" % s)
                self._sessions.pop(s, "")

                # Check if we should arm the auto power-off timer
                # i.e. when the last session is removed and a power timeout
                # was set
                if len(self._sessions) == 0 and self._power_timeout > 0:
                    self._power_expiry = now + self._power_timeout
                    #self.mtda.debug(2, "device will be powered down in {} "
                    #                   "seconds".format(self._power_timeout))

            if len(self._sessions) > 0:
                # There are active sessions: reset power expiry
                self._power_expiry = None
            else:
                # Otherwise check if we should auto-power off the target
                if self._power_expiry is not None and now > self._power_expiry:
                    self._lock_expiry = 0
                    power_off = True

            # Release device if the session owning the lock is idle
            if self._lock_owner is not None:
                if session == self._lock_owner:
                    self._lock_expiry = now + self._lock_timeout
                elif now >= self._lock_expiry:
                    events.append("UNLOCKED %s" % self._lock_owner)
                    self._lock_owner = None

        # Send event sessions generated above
        for e in events:
            self._session_event(e)

        # Check if we should auto power-off the device
        if power_off is True:
            self._target_off()
            #self.mtda.debug(2, "device powered down after {} seconds of "
            #                   "inactivity".format(self._power_timeout))

        #self.mtda.debug(3, "main._session_check: %s" % str(result))
        return result

    def target_on(self,args=None):
        result=True
        print("The target is powered on")
        os.system("echo 1 > /sys/class/gpio/gpio201/value")
        os.system("echo 1 > /sys/class/gpio/gpio203/value")
        return result
    
    def target_off(self,args=None):
        result=False
        print("The target is powered off")
        os.system("echo 0 >/sys/class/gpio/gpio201/value")
        os.system("echo 0 >/sys/class/gpio/gpio203/value")
        return result
	
    def target_locked(self, session):
        self._session_check(session)
        return self._check_locked(session)

    def target_owner(self):
        #self.mtda.debug(3, "main.target_owner()")
        return self._lock_owner

    def _target_status(self, session=None):
        self.mtda.debug(3, "main._target_status()")

        if self.power_controller is None:
            result = CONSTS.POWER.UNSURE
        else:
            result = self.power_controller.status()

        self.mtda.debug(3, "main._target_status(): {}".format(result))
        return result

    def target_status(self, session=None):
        self.mtda.debug(3, "main.target_status()")

        with self._power_lock:
            result = self._target_status(session)

        self.mtda.debug(3, "main.target_status(): {}".format(result))
        return
    
    def _session_event(self, info):
        result = None
        #if info is not None:
        #    self.notify(CONSTS.EVENTS.SESSION, info)
        return result

    def storage_status(self, session=None):
        #self.mtda.debug(3, "main.storage_status()")

        self._session_check(session)
        print("I am here")
        if self.storage_controller is None:
            #self.mtda.debug(4, "storage_status(): no shared storage device")
            result = CONSTS.STORAGE.UNKNOWN, False, 0
        else:
            status = self.storage_controller.status()
            result = status, self._writer.writing, self._writer.written

        #self.mtda.debug(3, "main.storage_status(): %s" % str(result))
        return result

    def monitor_remote(self, host, screen):
        self.mtda.debug(3, "main.monitor_remote()")

        result = None
        if self.is_remote is True:
            # Stop previous remote console
            if self.monitor_output is not None:
                self.monitor_output.stop()
            if host is not None:
                # Create and start our remote console in paused
                # (i.e. buffering) state
                self.monitor_output = RemoteMonitor(host, self.conport, screen)
                self.monitor_output.pause()
                self.monitor_output.start()
            else:
                self.monitor_output = None

        self.mtda.debug(3, "main.monitor_remote(): %s" % str(result))
        return result

    def monitor_send(self, data, raw=False, session=None):
        self.mtda.debug(3, "main.monitor_send()")

        self._session_check(session)
        result = None
        if self.console_locked(session) is False and \
           self.monitor_logger is not None:
            result = self.monitor_logger.write(data, raw)

        self.mtda.debug(3, "main.monitor_send(): %s" % str(result))
        return result

    def on_request(self,ch, method, props, body):
        body = str(body.decode('UTF-8'))
        cmd_dict = {'target_locked':self.target_locked,
                    'target_on': self.target_on,
                    'target_off' : self.target_off,
                    'storage_status':self.storage_status}
        if ":" in body:
            print(body)
            function_call_dict = eval(body)
            function_name = list(function_call_dict.keys())[0]
            arguments = function_call_dict[function_name]
            response = cmd_dict[function_name](*arguments)
        else:
            response = cmd_dict[body]()
        print("HIiwhdeidheidheihe",response) 
        ch.basic_publish(exchange='',routing_key=props.reply_to,properties=pika.BasicProperties(correlation_id =props.correlation_id),body=str(response))
        #ch.basic_publish(exchange='',routing_key='mtda-amqp',properties=pika.BasicProperties(correlation_id =props.correlation_id),body=str(response))
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def run_server(self):
        self.channel.start_consuming()
