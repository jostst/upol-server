import serial
import struct

class ThorlabsELL:
    def __init__(self, port="/dev/ttyUSB0"):
        self.port = port
        self.baud = 9600
        self.bytesize = serial.EIGHTBITS
        self.parity = serial.PARITY_NONE
        self.stopbits = serial.STOPBITS_ONE
        self.rtscts = False
        self.dsrdtr = False
        self.xonxoff = False
        self.timeout = 3

        self.connected = False
        self.serial = None

        self.__connect()

    def __del__(self):
        if self.connected:
            self.__disconnect()

    def stop(self):
        if self.connected:
            self.__disconnect()

    def sendCommand(self, msg):
        self.serial.reset_output_buffer()
        self.serial.reset_input_buffer()
        self.serial.write(msg.encode('utf-8'))
        data = self.serial.read_until(b'\r\n')
        return data.decode('utf-8')

    def __connect(self):
        self.serial = serial.Serial(port=self.port, 
                                    baudrate=self.baud, 
                                    bytesize=self.bytesize, 
                                    parity=self.parity, 
                                    stopbits=self.stopbits,
                                    timeout=self.timeout,
                                    xonxoff=self.xonxoff,
                                    rtscts=self.rtscts,
                                    dsrdtr=self.dsrdtr)

    def __disconnect(self):
        try:
            print("Disconnecting ELLB...")
            self.serial.close()
            self.connected = False
            print("ELLB disconnected!")
        except:
            print("ELLB disconnection failed!")

class ThorlabsELLx:
    def __init__(self, parent, channel):
        self.parent = parent
        self.channel = channel
        
        # These properties are generic and are in encoder units!
        self.__position = None
        self.__jogStep = None

    def execute(self, msg):
        rsp = self.parent.sendCommand(msg)
        self.parser(rsp)

    def parser(self, rsp):
        ch = rsp[0:1]
        co = rsp[1:3]
        va = rsp[3:]

        if co == "PO":
            self.__position = self.decode(va)
        elif co == "GJ":
            self.__jogStep = self.decode(va)
        else:
            print("CH: {}, COM: {}, VAL: {}".format(ch, co, va))

    def home(self, direction):
        ''' Home. 0 - forward, 1 - backward'''
        msg="{}ho{}".format(self.channel, direction)
        self.execute(msg)
    
    def jog(self, direction):
        '''Jog. 0 - forward, 1-backward'''
        if direction == 0:
            msg="{}fw".format(self.channel)
        elif direction == 1:
            msg="{}bw".format(self.channel)
        else:
            return -1
        self.execute(msg)
    
    @property
    def jogStep(self):
        msg = "{}gj".format(self.channel)
        self.execute(msg)
        return self.__jogStep

    @jogStep.setter
    def jogStep(self, value):
        msg ="{}sj{}".format(self.channel, self.encode(value))
        self.execute(msg)

    @property
    def position(self):
        msg = "{}gp".format(self.channel)
        self.execute(msg)
        return self.__position

    @position.setter
    def position(self, value):
        msg = "{}ma{}".format(self.channel, self.encode(value))
        self.execute(msg)

    def decode(self, hex_str):
        # Convert hex to an integer
        num = int(hex_str, 16)
        
        # Check if the number is greater than the max positive value for a 32-bit signed integer
        if num >= 0x80000000:  # 2^31
            num -= 0x100000000  # Subtract 2^32
        
        return num

    def encode(self, num):
        # Adjust if the number is negative
        if num < 0:
            num += 0x100000000  # 2^32

        # Convert the integer to a hexadecimal string
        hex_str = format(num, '08X')  # Ensures the string is padded to represent all 32 bits

        return hex_str


class ThorlabsELL9(ThorlabsELLx):
    def __init__(self, parent, channel, callback):
        super().__init__(parent, channel)
        self.positions = [0, 32, 64, 96]
        self.callback = callback

    @property
    def positionPos(self):
        pos = self.position
        closest = min(self.positions, key=lambda x: abs(x - pos))
        return self.positions.index(closest)

    @positionPos.setter
    def positionPos(self, value):
        if value > 3:
            print("Illegal position requested!")
        else:
            pos = int(value)
            self.position = self.positions[pos]
            if self.callback:
                self.callback(self.positionPos)

class ThorlabsELL14(ThorlabsELLx):
    def __init__(self, parent, channel, callback):
        super().__init__(parent, channel)
        self.pulses_deg = 143360/360
        self.callback = callback
       
    @property
    def positionDeg(self):
        return self.position / self.pulses_deg

    @positionDeg.setter
    def positionDeg(self, value):
        if value > 360:
            print("Illegal position requested!")
        else:
            pos = int(value * self.pulses_deg)
            self.position = pos
            if self.callback:
                self.callback(self.positionDeg)
            else:
                print("Position is: {}".format(self.positionDeg))

    @property
    def jogStepDeg(self):
        return int(self.jogStep / self.pulses_deg)

    @jogStepDeg.setter
    def jogStepDeg(self, value):
        if value > 360:
            print("Illegal position requested!")
        else:
            jog = int(value * self.pulses_deg)
            self.jogStep = jog

class PolController:
    def __init__(self, port="/dev/ttyUSB0", rot1callback=None, rot2callback=None, flt1callback=None):
        self.port = port
        self.connection = ThorlabsELL(self.port)
        self.rot1 = ThorlabsELL14(self.connection, 1, rot1callback)
        self.rot2 = ThorlabsELL14(self.connection, 2, rot2callback)
        self.flt1 = ThorlabsELL9(self.connection, 3, flt1callback)

    def stop(self):
        self.connection.stop()