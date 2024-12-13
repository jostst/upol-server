import components.thorlabs_apt_protocol as apt
import serial
import threading
import time

class ThorlabsKDC:
    def __init__(self, port="/dev/ttyUSB0", positionCallback=None):
        self.port = port
        self.baud = 115200
        self.rtscts = True
        self.timeout = 0.1
        self.source = 0x01
        self.dest = 0x50
        self.channel = 1
        self.stepspmm = 34555
        self.connected = False

        self.minorStep = 0.1
        self.majorStep = 1.0
        self.jogStep = 0.01

        self._position = 0.0
        self.positionCallback = positionCallback

        self.stopThreads = False
        self.__connect()
        self.home()

    def __del__(self):
        if self.connected:
            self.__disconnect()
    
    def stop(self):
        if self.connected:
            self.__disconnect()

    def __connect(self):
        try:
            self.serial = serial.Serial(self.port, self.baud, rtscts=self.rtscts, timeout=self.timeout)

            # Stop updates
            self.serial.write(apt.hw_stop_updatemsgs(source=self.source, dest=self.dest))
            # Clear the buffers
            self.serial.rts = True
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            self.serial.rts = False

            # This must be sent as part of the protocol!
            self.serial.write(apt.hw_no_flash_programming(source=self.source, dest=self.dest))
            
            # If no exceptions to here, we are connected
            self.connected = True
            
            # Start the reciever in a new thread
            self.reciever = threading.Thread(target=self.serialReciever)
            self.reciever.start()

        except:
            print("Connection failed!")

    def __disconnect(self):
        try:
            print("Disconnecting KDC1001...")
            self.stopThreads = True
            self.reciever.join()
            self.serial.close()
            self.connected = False
            print("KDC1001 disconnected!")
        except:
            print("Closing connection failed!")

    def serialReciever(self):
        unpacker = apt.Unpacker(self.serial)
        while not self.stopThreads:
            try:
                msg = next(unpacker)
                self.serial_handler(msg)
            except StopIteration:
                time.sleep(0.01)

    def serial_handler(self, msg):
        if msg.msg == 'mot_move_homed':
            print("Homed")
            self.position = 0.0
        if hasattr(msg, 'position'):
            self.position = msg.position

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        position = self.fromSteps(value)
        print("Position is now: {}".format(position))
        self._position = position
        if self.positionCallback:
            self.positionCallback(position)

    def toSteps(self, mm):
        return int(self.stepspmm * mm)

    def fromSteps(self, steps):
        return float(steps/self.stepspmm)

    def home(self):
        cmd = apt.mot_move_home(source=self.source, dest=self.dest ,chan_ident=self.channel)
        self.serial.write(cmd)

    def move_to_position(self, position):
        '''Move to aboslute position in mm'''
        pos = self.toSteps(position)
        cmd = apt.mot_move_absolute(source=self.source, dest=self.dest, chan_ident=self.channel, position=pos)
        self.serial.write(cmd)

    def move_relative(self, distance):
        '''Move ralitve distance in mm'''
        dst = self.toSteps(distance)
        cmd = apt.mot_move_relative(source=self.source, dest=self.dest, chan_ident=self.channel, distance=dst)
        self.serial.write(cmd)

    def step_major(self, direction):
        if direction == 1:
            self.move_relative(self.majorStep)
        elif direction == -1:
            self.move_relative(-self.majorStep)
        else:
            print("Error moving major!")

    def step_minor(self, direction):
        if direction == 1:
            self.move_relative(self.minorStep)
        elif direction == -1:
            self.move_relative(-self.minorStep)
        else:
            print("Error moving minor!")

    def step_jog(self, direction):
        if direction == 1:
            self.move_relative(self.jogStep)
        elif direction == -1:
            self.move_relative(-self.jogStep)
        else:
            print("Error moving jog!")

