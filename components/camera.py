import gxipy as gx
import time
import numpy as np
from enum import Enum

class GetCamerasCamera:
    class CameraModes(Enum):
        ''' Camera modes contain a list of configuration to perform specific tasks.'''
        SNAPSHOT = 1
        LIVE = 2            
        ACQUISITION = 3

    def __init__(self, live_callback, snapshot_callback, acquire_callback, maxFPS = 10.0, exposureCallback=None, gainCallback=None):
        self.live_callback = live_callback
        self.snapshot_callback = snapshot_callback
        self.acquire_callback = acquire_callback

        self.maxFPS = maxFPS

        self.connected = False
        self.stream = None

        self.exposureCallback = exposureCallback
        self.gainCallback = gainCallback

        self.__gain = 1.0
        self.__exposure = 100.0
        self.__frameRate = 10.0
        self.__mode = None

        self.__connect()
        self.__initialize()

    def __del__(self):
        if self.connected:
            self.__disconnect()

    def stop(self):
        if self.connected:
            self.__disconnect()

    @property
    def gain(self):
        if self.connected:
            self.__gain = self.__device.Gain.get()
        return self.__gain

    @gain.setter
    def gain(self, value: float):
        # TODO: TYPE and VALUE CHECKING!!!
        self.__gain = value
        if self.connected:
            print("Setting gain to: {}".format(self.__gain))
            self.__device.Gain.set(self.__gain)
        if self.gainCallback:
            self.gainCallback(value)

    @property
    def exposure(self):
        if self.connected:
            self.__exposure = self.__device.ExposureTime.get()/1000
        return self.__exposure

    @exposure.setter
    def exposure(self, value: float):
        # TODO: TYPE and VALUE CHECKING!!!
        self.__exposure = value
        if self.connected:
            print("Setting exposure to [ms]: {}".format(self.__exposure))
            self.__device.ExposureTime.set(self.__exposure*1000.0)
            self.frameRate = self.maxFPS
        if self.exposureCallback:
            self.exposureCallback(value)

    @property
    def frameRate(self):
        if self.connected:
            self.__frameRate = self.__device.AcquisitionFrameRate.get()
        return self.__frameRate
    
    @frameRate.setter
    def frameRate(self, fps: float):
        # TODO: TYPE and VALUE CHECKING!!!
        self.__frameRate = min(fps, 1000/self.exposure)
        if self.connected:
            print("Setting FrameRate to: {}".format(self.__frameRate))
            self.__device.AcquisitionFrameRate.set(self.__frameRate)

    @property
    def mode(self):
        return self.__mode
    
    @mode.setter
    def mode(self, mode: CameraModes):
        # TODO: TYPE and VALUE CHECKING!!!
        # If new mode is the same as the current, do nothing!
        if mode == self.__mode:
            return

        # If we have a stream, stop it
        if self.stream:
            self.__device.stream_off()
            self.stream = None
        
        # Configure for snapshot mode. This is the default.
        if mode == self.CameraModes.SNAPSHOT:
            # Notify the terminal
            print("Entering SNAPSHOT mode...")
            # Define the callback
            def callback(raw_image):
                data = raw_image.get_numpy_array()
                self.snapshot_callback(data)

            # Set software trigger
            self.__device.TriggerMode.set(gx.GxSwitchEntry.ON)
            self.__device.TriggerSource.set(gx.GxTriggerSourceEntry.SOFTWARE)
            self.__device.AcquisitionFrameRateMode.set(gx.GxSwitchEntry.OFF)

            # Get the stream
            self.stream = self.__device.data_stream[0]

            # Register the callback
            self.stream.register_capture_callback(callback)

            # Start streaming
            self.__device.stream_on()
            time.sleep(0.1)
        
        # Configure for live streaming.
        if mode == self.CameraModes.LIVE:
            # Notify the terminal
            print("Entering LIVE mode...")
            # Define the callback
            def callback(raw_image):
                data = raw_image.get_numpy_array()
                self.live_callback(data)

            # Disable trigger and enable framerate mode
            self.__device.TriggerMode.set(gx.GxSwitchEntry.OFF)
            self.__device.AcquisitionFrameRateMode.set(gx.GxSwitchEntry.ON)
            self.frameRate = self.maxFPS

            # Get the stream
            self.stream = self.__device.data_stream[0]
        
            # Register the callback
            self.stream.register_capture_callback(callback)

            # Start the stream
            self.__device.stream_on()
            time.sleep(0.1)
            self.__device.AcquisitionStart.send_command()
        
        # Configure for acquisition.
        if mode == self.CameraModes.ACQUISITION:
            # Notify the terminal
            print("Entering ACQUISITION mode...")
            # Define the callback
            def callback(raw_image):
                data = raw_image.get_numpy_array()
                self.acquire_callback(data)
            
            # Set software trigger
            self.__device.TriggerMode.set(gx.GxSwitchEntry.ON)
            self.__device.TriggerSource.set(gx.GxTriggerSourceEntry.SOFTWARE)
            self.__device.AcquisitionFrameRateMode.set(gx.GxSwitchEntry.OFF)

            # Get the stream
            self.stream = self.__device.data_stream[0]

            # Register the callback
            self.stream.register_capture_callback(callback)

            # Start streaming
            self.__device.stream_on()
            time.sleep(0.1)

        # Finally, set the property to the now active mode
        self.__mode = mode

    def __initialize(self):
        # Configure default values for the camera
        print("Setting default settings...")
        
        # Set MONO16 mode
        self.__device.PixelFormat.set(gx.GxPixelFormatEntry.MONO12)

        # Disable corrections
        self.__device.SharpnessMode.set(gx.GxSwitchEntry.OFF)
        self.__device.NoiseReductionMode.set(gx.GxSwitchEntry.OFF)

        # Disabble gamma
        self.__device.GammaEnable.set(False)

        # Set digital shift to 0
        self.__device.DigitalShift.set(0)

        # Disable LUT
        self.__device.LUTEnable.set(False)

        # Disable binning
        self.__device.BinningHorizontalMode.set(gx.GxBinningHorizontalModeEntry.SUM)
        self.__device.BinningHorizontal.set(1)
        self.__device.BinningVerticalMode.set(gx.GxBinningVerticalModeEntry.SUM)
        self.__device.BinningVertical.set(1)
        
        # Disable all delays
        self.__device.TriggerDelay.set(0.0)
        self.__device.ExposureDelay.set(0.0)

        # Set gain manual and default
        self.__device.GainAuto.set(gx.GxAutoEntry.OFF)
        self.__device.Gain.set(self.__gain)
        print("...Setting gain: {}".format(self.gain))

        # Set exposure manual and default
        self.__device.ExposureAuto.set(gx.GxAutoEntry.OFF)
        self.__device.ExposureMode.set(gx.GxExposureModeEntry.TIMED)
        self.__device.ExposureTime.set(self.__exposure*1000.0)
        print("...Setting exposure time [ms]: {}".format(self.__exposure))

        self.mode = self.CameraModes.SNAPSHOT

        print("Camera set up with default values!")

        return 0

    def __connect(self):
        print("Connecting camera...")

        if self.connected:
            print("...Already connected!")
            return -1

        # Create a device manager and find devices
        self.__device_manager = gx.DeviceManager()
        dev_num, dev_info_list = self.__device_manager.update_device_list()
        
        # Verify that devices are found
        if dev_num == 0:
            print("...No cameras found!")
            return None
        print("...Found {} camera(s)!".format(dev_num))

        # Open the device
        self.__device = self.__device_manager.open_device_by_index(1)
        print("Camera connected!")

        # Set connected to true
        self.connected = True

        return 0

    def __disconnect(self):
        print("Disconnecting camera...")

        if not self.__device:
            print("...No camera found!")
            return -1

        # Close the connection
        self.__device.close_device()
        self.__device = None
        print("Camera disconnected!")

        # Set connected to false
        self.connected = False

        return 0

    def triggerSnapshot(self):        
        # This just assures snapshot mode
        self.mode = self.CameraModes.SNAPSHOT

        # Send an actual trigger
        self.__device.TriggerSoftware.send_command()
        print("Snapshot triggered...")

    def triggerAcquisition(self):
        # Send an actual trigger
        self.__device.TriggerSoftware.send_command()
        print("Frame triggered...")