import websockets
import threading
from websockets.sync.server import serve

class WebSocketServer(threading.Thread):
    def __init__(self, ctx, host="localhost", port=1234, password="", handler=None, ssl_context=None):
        super().__init__()
        self.host = host
        self.port = port
        self.password = password
        self.handler = handler
        self.ssl_context = ssl_context
        self.server = None
        self.connections = set()
        # Context binding
        self.ctx = ctx
        self.ctx.server = self

    def run(self):
        self.server = serve(self.handle_client, self.host, self.port, ssl_context=self.ssl_context, max_size=10**7)
        print("Server started.")
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()
    
    def broadcast(self, data):
        # Iterate through available clients and send the data
        for socket in self.connections:
            socket.send(data)
    
    def authenticate(self, ws, addr):
        # Receive the password from the client
        password = ws.recv()
        if password == self.password:
            print(f"[{addr[0]}] Authentication successful.")
            ws.send("Authenticated")
            # Add client to the set
            self.connections.add(ws)
            # Return True for successful authentication
            return True
        else:
            print(f"[{addr[0]}] Authentication failed.")
            # Authentication failed, close the connection
            ws.close(code=1008, reason="Authentication failed")
            # Return False on failed authentication
            return False


    def handle_client(self, websocket):
        ip = websocket.remote_address
        print(f"[{ip[0]}] Client connected.")
        # Compare the received password with the expected password
        if self.authenticate(websocket, ip):
            # Listen for messages!
            try:
                while True:
                    message = websocket.recv()
                    if not message:
                        break
                    # Process using the handler and send response
                    response = self.handler.handle_request(message, ip[0])
                    websocket.send(response)
            # Notify abrupt connection drop
            except websockets.exceptions.ConnectionClosedError:
                print(f"[{ip[0]}] Connection stopping abnormally!")
            except websockets.exceptions.ConnectionClosedOK:
                print(f"[{ip[0]}] Connection stopping gracefully!")
            # Notify connection stop
            finally:
                print(f"[{ip[0]}] Connection closed.")
                # remove client from the set
                self.connections.remove(websocket)