#!/usr/bin/env python
import pika
import os

from mtda.console.remote import RemoteConsole, RemoteMonitor
from mtda.console.input import ConsoleInput

DEFAULT_PREFIX_KEY = 'ctrl-a'
DEFAULT_PASTEBIN_EP = "http://pastebin.com/api/api_post.php"

class MTDA_AMQP(object):

    def __init__(self):
        self.connection = pika.BlockingConnection(pika.URLParameters('amqp://admin:password@134.86.62.153:5672'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue='mtda-amqp')
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


    def fib(n):
        if n == 0:
            return 0
        elif n == 1:
            return 1
        else:
            return fib(n - 1) + fib(n - 2)

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
        self.mtda.debug(3, "main.target_locked()")

        self._session_check(session)
        return self._check_locked(session)

    def target_owner(self):
        self.mtda.debug(3, "main.target_owner()")

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
        if str(body.decode('UTF-8'))=="target_on":
            print(body,type(body))
            response=self.target_on()
        elif str(body.decode('UTF-8'))=="target_off":
            response=self.target_off()
        else:
            response=self.fib(int(body))
        ch.basic_publish(exchange='',routing_key=props.reply_to,properties=pika.BasicProperties(correlation_id =props.correlation_id),body=str(response))
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def run_server(self):
        self.channel.start_consuming()
