import json

class Context:
    def __init__(self):
        self.handler = None
        self.server = None
        self.system = None

    def sender(self, data):
        self.server.broadcast(data)

    def reciever(self, data):
        self.system.parseCommand(data)