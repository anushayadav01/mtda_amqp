from mtda.console.output import ConsoleOutput
import mtda.constants as CONSTS

class RemoteConsole(ConsoleOutput):

     def __init__(self, host, port, screen):
        ConsoleOutput.__init__(self, screen)
        self.context = None
        self.host = host
        self.port = port
        self.socket = None
        self.topic = CONSTS.CHANNEL.CONSOLE

     def stop(self):
        super().stop()
        if self.context is not None:
            self.context.term()
            self.context = None

class RemoteMonitor(RemoteConsole):

    def __init__(self, host, port, screen):
        super().__init__(host, port, screen)
        self.topic = CONSTS.CHANNEL.MONITOR
