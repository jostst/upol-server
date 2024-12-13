import json
import numpy as np
from components.handler import MsgTypes
from components.camera import GetCamerasCamera
from components.focus import ThorlabsKDC
from components.polarization import PolController
from components.kurios import Kurios
from components.acquisitionParser import AcquisitionFileParser
from components.acquisitionRunner import AcquisitionRunner
import pickle
import base64
from PIL import Image
import io
import cv2

class System:
    def __init__(self, ctx):
        # Context binding
        self.ctx = ctx
        self.ctx.system = self
        self.cam = GetCamerasCamera(self.image_send_callback, self.image_send_callback, self.image_acquire_callback, exposureCallback=self.sendExposure, gainCallback=self.sendGain)
        # Setting the port in /etc/udev/rules.d as (adjust serial numbers as needed!)
        #SUBSYSTEM=="tty", ATTRS{manufacturer}=="Thorlabs", ATTRS{serial}=="1234", SYMLINK+="kdc1001"
        self.focus = ThorlabsKDC(port="/dev/kdc1001", positionCallback=self.sendPosition)
        # Setting the port in /etc/udev/rules.d as (adjust serial numbers as needed!)
        #SUBSYSTEM=="tty", ATTRS{manufacturer}=="FTDI", ATTRS{serial}=="1234", SYMLINK+="ellb"
        self.pol = PolController(port="/dev/ellb", rot1callback=self.sendRot1Position, rot2callback=self.sendRot2Position, flt1callback=self.sendFlt1Position)
        # Setting the port in /etc/udev/rules.d as (adjust serial numbers as needed!)
        #SUBSYSTEM=="tty", ATTRS{manufacturer}=="THORLABS", ATTRS{serial}=="1234", SYMLINK+="kurios"
        self.hs = Kurios(port="/dev/kurios", lctfCallback=self.sendHyperspectralStatus)

        # Root data directory
        self.pwd = '/home/user/data'

    def send(self, data):
        self.ctx.sender(json.dumps(data))
    
    def stop(self):
        self.focus.stop()
        self.cam.stop()

    def sendImage(self, img):
        # Convert to copressed TIFF and generate a base64 bytestring
        buffered = io.BytesIO()
        img.save(buffered, format='TIFF', compression='tiff_lzw')
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        # Send the image effectively
        self.send({"type":MsgTypes.IMG.value, "data":img_str})
    
    def sendHeartbeat(self):
        self.send({"type":MsgTypes.HRB.value, "data":"OK"})
    
    def sendMessage(self, text: str):
        self.send({"type":MsgTypes.MSG.value, "data":text})

    def sendPosition(self, pos: float):
        msg = {"type": MsgTypes.VAL.value, "data":{"module":"focus", "field":"positionMM", "value":pos}}
        self.send(msg)

    # TODO: implement this all over
    def sendExposure(self, tint: float):
        msg = {"type": MsgTypes.VAL.value, "data":{"module":"cam", "field":"Exposure", "value":tint}}
        self.send(msg)

    # TODO: implement this all over
    def sendGain(self, gain: float):
        msg = {"type": MsgTypes.VAL.value, "data":{"module":"cam", "field":"Gain", "value":gain}}
        self.send(msg)

    def sendRot1Position(self, pos: float):
        msg = {"type": MsgTypes.VAL.value, "data":{"module":"polarization", "submodule":"rot1", "field":"positionDEG", "value":pos}}
        self.send(msg)

    def sendRot2Position(self, pos: float):
        msg = {"type": MsgTypes.VAL.value, "data":{"module":"polarization", "submodule":"rot2", "field":"positionDEG", "value":pos}}
        self.send(msg)

    def sendFlt1Position(self, pos: float):
        msg = {"type": MsgTypes.VAL.value, "data":{"module":"polarization", "submodule":"flt1", "field":"positionPOS", "value":pos}}
        self.send(msg)

    def sendHyperspectralStatus(self, wl: float, black: bool, status, temperature: float, min, max):
        msg = {"type": MsgTypes.VAL.value, "data":{"module":"hyperspectral", "field":"wavelength", "value":wl}}
        self.send(msg)
        msg = {"type": MsgTypes.VAL.value, "data":{"module":"hyperspectral", "field":"black", "value":black}}
        self.send(msg)
        msg = {"type": MsgTypes.VAL.value, "data":{"module":"hyperspectral", "field":"status", "value":status}}
        self.send(msg)
        msg = {"type": MsgTypes.VAL.value, "data":{"module":"hyperspectral", "field":"temperature", "value":temperature}}
        self.send(msg)
        msg = {"type": MsgTypes.VAL.value, "data":{"module":"hyperspectral", "field":"range", "min":min, "max":max}}
        self.send(msg)

    def run_acquisition(self, data):
        print(f"----------Acquisition script----------")
        print(data)
        # Parse acquisition script
        parser = AcquisitionFileParser(data)
        parser.parse()
        print(f"----------Acquisition parsed----------")
        print("Version:", parser.version)
        print("Acquisition Info:", vars(parser.acquisition))
        print("Steps:")
        for step in parser.steps:
            print(step)
        print(f"--------------------------------------")
        # Create the runner

        runner = AcquisitionRunner(parser, self.pwd, self)
        # Notify client
        self.send({"type":MsgTypes.MSG.value, "data":"Starting acquisition..."})
        # Register runner to get the image
        self.cam.acquire_callback = runner.image_acquire_callback
        # Run the acquisition
        runner.run()
        # Deregister runner callback
        self.cam.acquire_callback = self.image_acquire_callback
        # Notify client
        self.send({"type":MsgTypes.MSG.value, "data":"Acquisition DONE!"})

    def parseCommand(self, data):
        ''' data should be an object, created from a valid request JSON. '''
        if data["type"] == MsgTypes.MSG.value:
            print(f"MSG:", data["data"])
        elif data["type"] == MsgTypes.ACQ.value:
            self.run_acquisition(data["data"])
        elif data["type"] == MsgTypes.VAL.value:
            command = data["data"]
            # Here we parse the commands from the client!
            if command["module"] == "cam":
                if command["field"] == "ExposureTime":
                    self.cam.exposure = float(command["value"])
                elif command["field"] == "Gain":
                    self.cam.gain = float(command["value"])
                elif command["field"] == "Snapshot":
                    self.cam.triggerSnapshot()
                elif command["field"] == "Live":
                    if command["value"]:
                        self.cam.mode = GetCamerasCamera.CameraModes.LIVE
                    else:
                        self.cam.mode = GetCamerasCamera.CameraModes.SNAPSHOT
            elif command["module"] == 'focus':
                if command["field"] == "home":
                    self.focus.home()
                elif command["field"] == "goto":
                    self.focus.move_to_position(float(command["value"]))
                elif command["field"] == "step_major":
                    self.focus.step_major(command["value"])
                elif command["field"] == "step_minor":
                    self.focus.step_minor(command["value"])
                elif command["field"] == "step_jog":
                    self.focus.step_jog(command["value"])
                elif command["field"] == "set_jog":
                    self.focus.jogStep = float(command["value"])
            elif command["module"] == 'polarization':
                if command["submodule"] == 'rot1':
                    if command["field"] == "home":
                        self.pol.rot1.home(1)
                        self.pol.rot1.positionDeg = 0
                    elif command["field"] == "goto":
                        self.pol.rot1.positionDeg = float(command["value"])
                elif command["submodule"] == 'rot2':
                    if command["field"] == "home":
                        self.pol.rot2.home(1)
                        self.pol.rot2.positionDeg = 0
                    elif command["field"] == "goto":
                        self.pol.rot2.positionDeg = float(command["value"])
                elif command["submodule"] == 'flt1':
                    if command["field"] == "home":
                        self.pol.flt1.home(1)
                        self.pol.flt1.positionPos = 0
                    elif command["field"] == "goto":
                        self.pol.flt1.positionPos = float(command["value"])
            elif command["module"] == 'hyperspectral':
                if command["field"] == 'status':
                    self.sendHyperspectralStatus(self.hs.wl, self.hs.black, f"{self.hs.status.name}", self.hs.temperature, self.hs.WLmin, self.hs.WLmax)
                if command["field"] == 'black':
                    self.hs.black = bool(command["value"])
                if command["field"] == 'wavelength':
                    self.hs.wl = float(command["value"])
            else:
                print(f"Unhandled payload: ", command)
        else:
            print(f"Invlaid type: ", data["type"])

    def image_send_callback(self, data):
        # Convert the image to 8 bit MINMAX and produce Pillow image
        img = data.astype(np.float32)
        img = cv2.normalize(img, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
        img = img.astype(np.uint8)
        img = Image.fromarray(img, mode='L')
        # Get original dimensions
        original_width, original_height = img.size
        # Calculate half the size and resize
        new_width = original_width // 2
        new_height = original_height // 2
        img = img.resize((new_width, new_height))
        self.sendImage(img)

    def image_acquire_callback(self, data):
        pass