import os
import zipfile
import time
from fs.zipfs import ZipFS  # pyfilesystem2 library
from components.handler import MsgTypes
import json
import h5py
import numpy as np
from PIL import Image

class AcquisitionRunner:
    def __init__(self, acquisition_parser, pwd, system):
        self.acquisition_parser = acquisition_parser
        self.pwd = pwd
        self.mounted_fs = None
        self.cam_busy = False
        self.frame = None
        self.system = system
        self.idx = 0

    def image_acquire_callback(self, data):
        # Ensure the array is in np.float32 format
        data = data.astype(np.float32)
        
        # Save the raw data as HDF5
        raw_filename = f"raw/frame_{self.idx:03d}.h5"
        with self.mounted_fs.open(raw_filename, "wb") as raw_file:
            with h5py.File(raw_file, "w") as hdf:
                hdf.create_dataset("image", data=data, dtype="float32")

        # Save the PNG
        png_filename = f"png/frame_{self.idx:03d}.png"
        image = Image.fromarray((data * 255 / np.max(data)).astype(np.uint8))
        with self.mounted_fs.open(png_filename, "wb") as png_file:
            image.save(png_file, format="PNG")
        
        # Notify
        print("Image acquired")
        self.cam_busy = False

    def run(self):
        try:
            # Create filesystem - ZIP
            self.prepare_acquisition_directory()
            # Perform operations on the mounted filesystem
            print("ZIP filesystem is ready for acquisition.")
        
            # Extract acquisition data
            acquisition_data = {
                "project": self.acquisition_parser.acquisition.project,
                "experiment": self.acquisition_parser.acquisition.experiment,
                "path": self.acquisition_parser.acquisition.path,
                "date": self.acquisition_parser.acquisition.date,
                "operator": self.acquisition_parser.acquisition.operator,
                "metadata": self.acquisition_parser.acquisition.metadata,
                "num_steps": self.acquisition_parser.acquisition.num_steps,
                "steps": [
                    {
                        "step": step.step,
                        "t_int": step.t_int,
                        "gain": step.gain,
                        "z_pos": step.z_pos,
                        "lam": step.lam,
                        "phi_g": step.phi_g,
                        "phi_a": step.phi_a,
                        "flt_a": step.flt_a,
                    }
                    for step in self.acquisition_parser.steps
                ],
            }

            # Write the JSON data to meta.json
            with self.mounted_fs.open("meta.json", "w") as meta_file:
                json.dump(acquisition_data, meta_file, indent=4)
            print("meta.json created in the ZIP filesystem.")

            # Initialize camera
            self.system.cam.mode = self.system.cam.CameraModes.ACQUISITION

            # Iterate over images (one per step)
            for idx, step in enumerate(self.acquisition_parser.steps):
                self.idx = idx
                # Send message to client - step parameters
                self.system.sendMessage(repr(step))
                # Set step parameters and sleep
                self.system.hs.wl = float(step.lam)
                self.system.cam.exposure = float(step.t_int)
                self.system.cam.gain = float(step.gain)
                self.system.pol.rot1.positionDeg = float(step.phi_a)
                self.system.pol.rot2.positionDeg = float(step.phi_g)
                self.system.pol.flt1.positionPos = float(step.flt_a)
                #self.system.focus.move_relative(float(step.z_pos))
                #time.sleep(0.2)
                # Acquire image and save
                self.system.cam.triggerAcquisition()
                self.cam_busy = True
                while self.cam_busy:
                    time.sleep(0.01)
                
                # Send message
                self.system.sendMessage("{}: OK".format(idx))
        finally:
            self.cleanup()

    def prepare_acquisition_directory(self):
        # Resolve the absolute path for the ZIP file
        relative_path = self.acquisition_parser.acquisition.path
        zip_file_path = os.path.join(self.pwd, relative_path)
        print(self.pwd)
        print(relative_path)
        print(zip_file_path)

        # Ensure the directory for the ZIP file exists
        os.makedirs(os.path.dirname(zip_file_path), exist_ok=True)

        # Create the ZIP file if it doesn't exist
        if not os.path.exists(zip_file_path):
            with zipfile.ZipFile(zip_file_path, 'w') as zipf:
                pass  # Create an empty ZIP file

        # Mount the ZIP file as a filesystem
        self.mounted_fs = ZipFS(zip_file_path, write=True)
        print(f"Mounted ZIP filesystem at: {zip_file_path}")
        
        # Create required folders in the ZIP filesystem
        self.mounted_fs.makedirs("raw", recreate=True)
        self.mounted_fs.makedirs("png", recreate=True)

    def cleanup(self):
        # Close the mounted filesystem if open
        if self.mounted_fs is not None:
            self.mounted_fs.close()
            print("Unmounted ZIP filesystem.")