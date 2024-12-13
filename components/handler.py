import json
from enum import Enum

class MsgTypes(Enum):
    MSG = 1     # Text message to the client
    CON = 2     # Connection message
    VAL = 3     # Value changed
    IMG = 4     # Image frame
    HRB = 5     # Heartbeat
    ACQ = 6     # Acquisition script

class Handler:
    def __init__(self, ctx):
        # Context binding
        self.ctx = ctx
        self.ctx.handler = self

    def handle_request(self, payload, peer):
        try:
            data = json.loads(payload)
            # Process the received JSON data here
            print(f"[{peer}] Received vaid JSON:", data)
            self.ctx.reciever(data)
            # Acknowledge
            response = {"type":MsgTypes.MSG.value, "status": "success", "data": "Received"}
            # Return the response
            return json.dumps(response)
        except json.JSONDecodeError:
            print(f"[{peer}] Received invalid JSON:", payload)
            # Example error response
            response = {"status": "error", "message": "Invalid JSON format"}
            return json.dumps(response)