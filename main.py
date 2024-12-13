import ssl
import time
from components.handler import Handler
from components.system import System
from components.server import WebSocketServer
from components.context import Context
from components.handler import MsgTypes

PASSWORD = "your_password"

def main():
    # Define context that binds function together
    ctx = Context()

    # Define parameters needed for the connection
    host = "0.0.0.0"
    port = 1234
    password = PASSWORD
    handler = Handler(ctx)
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.check_hostname = False
    ssl_context.load_cert_chain("keys/server.crt", "keys/server.key")

    # Create and start the server
    server = WebSocketServer(ctx, host, port, password, handler, ssl_context)
    server.start()

    # Initialize system controll
    # From here on, all things are done in the System!
    system = System(ctx)

    try:
        # Keep sending the heartbeat!
        while True:
            system.sendHeartbeat()
            time.sleep(5)
    # Close connection on keyboard interrupt
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Stopping server...")
        server.stop()
        system.stop()

if __name__ == "__main__":
    main()