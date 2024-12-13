import serial
import time
import re
from enum import Enum

class Status(Enum):
    INIT = 0    # Initializing
    WARM = 1    # Warming up
    REDY = 2    # Ready

class Kurios:
    def __init__(self, port='/dev/ttyUSB0', lctfCallback=None):
        self.port = port
        self.baud = 115200
        self.bytesize = serial.EIGHTBITS
        self.parity = serial.PARITY_NONE
        self.stopbits = serial.STOPBITS_ONE
        self.rtscts = False
        self.dsrdtr = False
        self.xonxoff = False

        self.timeout = 1

        self.connected = False
        self.serial = None

        self.WLmax = None
        self.WLmin = None

        self.__black = False
        self.__wl = None
        self.__temperature = None
        self.__status = None

        self.lctfCallback = lctfCallback

        self.__connect()
        self.__initialize()

    def __del__(self):
        self.stop()

    def stop(self):
        if self.connected:
            self.__disconnect()

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
        self.connected = True

    def __initialize(self):
        msg = self.sendCommand('SP?')
        
        max = re.search(r"WLmax=(\d+\.\d+)", msg)
        min = re.search(r"WLmin=(\d+\.\d+)", msg)

        if max and min:
            self.WLmax = float(max.group(1))
            self.WLmin = float(min.group(1))
        else:
            print("Error initializing KURIOS!")

        msg = self.sendCommand('BW=8')

    def __disconnect(self):
        try:
            print("Disconnecting KURIOS...")
            self.serial.close()
            self.connected = False
            print("KURIOS disconnected!")
        except:
            print("KURIOS disconnection failed!")

    def sendCommand(self, msg):
        self.serial.reset_output_buffer()
        self.serial.reset_input_buffer()
        self.serial.write((msg+'\r').encode('utf-8'))
        data = self.serial.read_until(b'\r>').decode("utf-8")
        return data
    
    @property
    def status(self):
        msg = self.sendCommand("ST?")
        
        st = re.search(r"ST=(\d)", msg)

        if st:
            self.__status = Status(int(st.group(1)))
        else:
            print("ERROR: getting status from KURIOS failed!")
        
        return self.__status

    @property
    def temperature(self):
        msg = self.sendCommand("TP?")
        
        tp = re.search(r"TP=(\d+\.\d+)", msg)

        if tp:
            self.__temperature = float(tp.group(1))
        else:
            print("ERROR: getting temperature from KURIOS failed!")
        
        return self.__temperature

    @property
    def black(self):
        return self.__black

    @black.setter
    def black(self, value):
        if isinstance(value, bool):
            if value:
                msg = self.sendCommand('BW=1')
                self.__black = True
            else:
                msg = self.sendCommand('BW=8')
                self.__black = False
            self.report()
        else:
            print("ERROR: wrong black type for KURIOS. Should be bool!")

    @property
    def wl(self):
        msg = self.sendCommand('WL?')

        wl = re.search(r"WL=(\d+\.\d+)", msg)
        
        if wl:
            self.__wl = float(wl.group(1))
        else:
            print("ERROR: getting wavelength from KURIOS failed!")
        
        return self.__wl

    @wl.setter
    def wl(self, value):
        if value > self.WLmin and value < self.WLmax:
            msg = self.sendCommand(f"WL={value:.3f}")
            time.sleep(0.05)
            self.report()
        else:
            print("ERROR: KURIOS wavelength out of range")

    def report(self):
        self.lctfCallback(self.wl, self.black, f"{self.status.name}", self.temperature, self.WLmin, self.WLmax)