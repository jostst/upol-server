# upol-server
This is the server component for controlling a hyperspectral polarization microscope. It works by recieving commands from a GUI client through a websockets connection. The connection is NOT SECURE IN THIS IMPLEMENTATION as only password is used.

The main goal behind this project is to eliminate the necessity of screens and peripheral devices connected to experimental setups.

**_NOTE:_**  The software is under active development and might change rapidly. There are probably bugs and/or bad code present, but the software currently serves its purpose.

**_ANOTHER NOTE:_**  Although the code as is might not be directly applicable to many users, the concepts can be used in development of similar projects. Specifically, the wrappers for individual components used in the setup should be reusable without major modification (although not all functions provided by the hardware might be implemented).

## Project outline
### `/main.py`
is the main entry point of the server software. It starts the websocket server and triggers the initialization of the system.

### `components/system.py`
is the main component of the server that binds together different wrappers by providing a unified API. It parses the requests by calling appropriate methods in individual component wrappers as well as defines the callbacks used in the individual wrapperrs.

#### Messaging protocol
##### 1. General Messages (`MSG`)
- **Description**: Used for general communication or logging purposes.
- **Purpose**:
  - Transmit text-based messages.
  - Provide basic communication functionality.
  ```json
  {
    "type": "MSG",
    "data": "Hello, this is a general message."
  }
  ```
---

##### 2. Heartbeat Messages (`HRB`)
- **Description**: Signals the system's heartbeat to indicate connectivity or status.
- **Purpose**:
  - Monitor system health.
  - Ensure active connection between components.
```json
{
  "type": "HRB",
  "data": null
}
```
---

##### 3. Value Updates (`VAL`)
- **Description**: Updates the values of various hardware or system components.
- **Modules and Submodules**:
  - **Focus**:
    - `positionMM`: Current position of the focus system.
    - `set_jog`: Configure jog step size.
    - `home`: Reset focus to the home position.
    - `step_major`: Perform a major step adjustment.
    - `step_minor`: Perform a minor step adjustment.
  - **Camera**:
    - `Exposure`: Update camera exposure time.
    - `Gain`: Update camera gain value.
    - `Live`: Start or stop the live feed.
    - `Snapshot`: Request a camera snapshot.
  - **Polarization**:
    - **Submodules**:
      - `rot1`:
        - `position`: Update rotational position of `rot1`.
        - `home`: Reset `rot1` to the home position.
      - `rot2`:
        - `position`: Update rotational position of `rot2`.
        - `home`: Reset `rot2` to the home position.
      - `flt1`:
        - `position`: Update filter position.
        - `home`: Reset `flt1` to the home position.
  - **Hyperspectral**:
    - `wavelength`: Update or retrieve the current wavelength.
    - `black`: Enable or disable black calibration.
    - `temperature`: Retrieve the current temperature.
    - `status`: Update or retrieve the status of the system.
    - `range`: Update the minimum and maximum wavelength range.
```json
{
  "type": "VAL",
  "data": {
    "module": "focus",
    "field": "positionMM",
    "value": 50.123
  }
}
```
---

##### 4. Image Messages (`IMG`)
- **Description**: Handles the transmission of Base64-encoded images for display or processing.
- **Purpose**:
  - Transmit visual data to be rendered or processed.
  - Enable real-time or snapshot-based image updates.
```json
{
  "type": "IMG",
  "data": "iVBORw0KGgoAAAANSUhEUgAAAAUA..."
}
```
---

### `components/context.py`
a very simple class that makes communication between different modules slightly easier.

### `components/server.py`
the actual WebSockets server that takes care of lower-level communication and authentication through password. Implemented using threading.

### `components/acquisition*.py`
Consisting of a Parser and Runner. Parser parses the text input defining an acquisition sequence and uses the result to construct an `Acquisition` object. This object contains acquisition metadata as well as an array of `Step` objects that define settings for individual acquisition steps. Data from the acquisition is stored in a zip file with the following structure:
```
data.zip
|- meta.json         # Acquisition metadata also containing step settings
|- /raw/
   |- frame_***.h5   # HDF5 containing raw data in dtype="float32"
   ...
|- /png/
   |- frame_***.png # PNG image for visualization
   ...
```

#### Script file format
Acquisition of the system can be scripted in a file. This file is sent to the server as plain text to be processed. An example of an acquisition script is in file `example_script.input`. The file is divided into structured sections, each serving a specific purpose in defining the acquisition metadata, parameters, and steps.

---

##### General Structure
A script file consists of three main sections:
1. **VERSION**: Specifies the script format version.
2. **ACQUISITION**: Defines metadata and general settings for the acquisition.
3. **STEPS**: Specifies detailed parameters for each acquisition step.

---

##### Section: VERSION
The `VERSION` section specifies the version of the script file format for compatibility purposes.

###### Format
VERSION <version_number>

```
VERSION 1.0
```
---

##### Section: ACQUISITION
The `ACQUISITION` section contains metadata and configuration settings for the acquisition process.

###### Format
Key-value pairs describe the general setup. Additional metadata fields can be included as nested key-value pairs under `metadata`.

###### Required Fields
| **Field**       | **Description**                                                                 |
|------------------|---------------------------------------------------------------------------------|
| `project`        | Name of the project.                                                           |
| `experiment`     | Identifier for the experiment.                                                 |
| `path`           | File path for saving the acquisition output.                                   |
| `date`           | Date of the acquisition in `YYYY-MM-DD` format.                                |
| `operator`       | Name of the operator responsible for the acquisition (can include a title).    |
| `metadata`       | Additional metadata as nested key-value pairs (optional but recommended).      |
| `num_steps`      | Total number of acquisition steps defined in the `STEPS` section.              |

```
ACQUISITION  
project: Sample Acquisition  
experiment: EXP_001  
path: testing/test1.zip  
date: 2024-12-10  
operator: Name Surname, Ph.D.  
metadata:  
  description: Test acquisition with variable parameters  
  custom_field1: Value1  
  custom_field2: Value2  
num_steps: 4  
```
---

##### Section: STEPS
The `STEPS` section defines the specific parameters for each acquisition step. Each step is described in a tabular format.

###### Format
- The first row contains comments that describe the column names and expected values.
- Each subsequent row represents an acquisition step, with fields separated by tabs.

###### Required Fields
| **Field**       | **Description**                                                                |
|------------------|--------------------------------------------------------------------------------|
| `step`          | Step number (starting from 0).                                                 |
| `t_int`         | Integration time (in milliseconds).                                            |
| `gain`          | Gain value for the acquisition.                                                |
| `z_pos`         | Z-position (e.g., focus depth) in micrometers.                                 |
| `lam`           | Wavelength (in nanometers).                                                    |
| `phi_g`         | Global angle in degrees.                                                       |
| `phi_a`         | Absolute angle in degrees.                                                     |
| `flt_a`         | Filter selection (1, 2, 3, or 4).                                              |

```
STEPS  
# Columns: step, t_int (integration time), gain, z_pos (z position), lam (wavelength),  
#          phi_g (global angle), phi_a (absolute angle), flt_a (filter: 1, 2, 3, or 4)  
0	100	1.5	0.0	550	45	90	1  
1	110	1.8	0.0	600	50	95	2  
2	120	2.0	0.0	650	55	100	3  
3	130	2.2	0.0	700	60	105	4  
```
---

##### Notes
- **Comments**: Lines starting with `#` are treated as comments and ignored during processing.
- **Tabs**: Use tabs to separate values in the `STEPS` section for clarity.
- **Consistency**: Ensure that the `num_steps` in the `ACQUISITION` section matches the number of rows in the `STEPS` section.

### `components/camera.py`
Provides `GetCamerasCamera` class that implements Daheng Imaging Galaxy API.

#### Features
- **Camera Modes**: 
  - `SNAPSHOT`: Capture single frames on demand.
  - `LIVE`: Stream frames continuously.
  - `ACQUISITION`: Perform triggered acquisitions.
- **Dynamic Configuration**:
  - Adjustable gain, exposure, and frame rate.
  - Callbacks for exposure and gain updates.
- **Automatic Initialization**: Automatically connects to the camera and applies default configurations.
- **Real-Time Streaming**: Utilizes callbacks to handle data in real-time for live or acquisition modes.

---

#### Constructor

##### `__init__(live_callback, snapshot_callback, acquire_callback, maxFPS=10.0, exposureCallback=None, gainCallback=None)`
Initializes the camera and sets up callbacks and default settings.

###### Parameters:
- `live_callback`: Function to process frames in live mode.
- `snapshot_callback`: Function to handle snapshot frames.
- `acquire_callback`: Function to process frames in acquisition mode.
- `maxFPS` (float): Maximum frames per second (default: 10.0).
- `exposureCallback`: Callback for exposure value updates.
- `gainCallback`: Callback for gain value updates.

---

###### Camera Modes
Defined using the `CameraModes` enum:
- `SNAPSHOT`: Mode for single-frame capture.
- `LIVE`: Continuous streaming mode.
- `ACQUISITION`: Triggered frame acquisition mode.

---

#### Properties

##### `gain`
- **Description**: Gets or sets the camera's gain value.
- **Type**: `float`

##### `exposure`
- **Description**: Gets or sets the camera's exposure time in milliseconds.
- **Type**: `float`

##### `frameRate`
- **Description**: Gets or sets the camera's frame rate in frames per second (FPS).
- **Type**: `float`

##### `mode`
- **Description**: Gets or sets the current camera mode (`SNAPSHOT`, `LIVE`, `ACQUISITION`).
- **Type**: `CameraModes`

---

#### Methods

##### `triggerSnapshot()`
- **Description**: Captures a single frame in snapshot mode.

##### `triggerAcquisition()`
- **Description**: Captures a frame in acquisition mode by triggering the camera.

##### `stop()`
- **Description**: Stops the camera and disconnects it safely.

---

#### Internal Methods

##### `__connect()`
- **Description**: Establishes a connection with the camera.

##### `__disconnect()`
- **Description**: Safely disconnects the camera.

##### `__initialize()`
- **Description**: Applies default configurations to the camera.

##### `__del__()`
- **Description**: Ensures the camera is disconnected when the object is deleted.

### `components/focus.py`
The `ThorlabsKDC` class provides an interface for controlling Thorlabs KDC1001 motor controllers via serial communication. It supports movement commands, position updates, and jog functionality.

---

#### Features
- **Serial Communication**: Establishes and manages a serial connection to the KDC1001 controller.
- **Movement Controls**:
  - Absolute and relative positioning.
  - Minor, major, and jog steps for precision movement.
- **Position Updates**: Handles and processes position updates from the controller.
- **Homing**: Automatically homes the motor upon initialization.

---

#### Constructor

##### `__init__(port="/dev/ttyUSB0", positionCallback=None)`
Initializes the motor controller and establishes a connection.

###### Parameters:
- `port` (str): Serial port to connect to (default: `/dev/ttyUSB0`).
- `positionCallback` (function): Optional callback to receive position updates.

---

#### Properties

##### `position`
- **Description**: Gets or sets the current position of the motor in millimeters.
- **Type**: `float`

---

#### Methods

##### Movement Commands
- **`home()`**:
  - Moves the motor to its home position.
- **`move_to_position(position)`**:
  - Moves the motor to an absolute position in millimeters.
  - **Parameters**:
    - `position` (float): Target position in millimeters.
- **`move_relative(distance)`**:
  - Moves the motor by a relative distance in millimeters.
  - **Parameters**:
    - `distance` (float): Distance to move in millimeters.
- **`step_major(direction)`**:
  - Moves the motor by the configured major step size.
  - **Parameters**:
    - `direction` (int): 1 for forward, -1 for backward.
- **`step_minor(direction)`**:
  - Moves the motor by the configured minor step size.
  - **Parameters**:
    - `direction` (int): 1 for forward, -1 for backward.
- **`step_jog(direction)`**:
  - Moves the motor by the configured jog step size.
  - **Parameters**:
    - `direction` (int): 1 for forward, -1 for backward.

---

##### Helper Methods
- **`toSteps(mm)`**:
  - Converts a distance in millimeters to steps.
  - **Parameters**:
    - `mm` (float): Distance in millimeters.
  - **Returns**: `int`
- **`fromSteps(steps)`**:
  - Converts steps to a distance in millimeters.
  - **Parameters**:
    - `steps` (int): Number of steps.
  - **Returns**: `float`

---

##### Connection Management
- **`stop()`**:
  - Stops the motor and disconnects from the controller.
- **Internal Methods**:
  - `__connect()`: Establishes the serial connection.
  - `__disconnect()`: Closes the serial connection.
  - `serialReciever()`: Processes incoming serial messages.

---

#### Internal Attributes
- `port` (str): Serial port for connection.
- `baud` (int): Baud rate for the serial connection.
- `rtscts` (bool): RTS/CTS flow control (default: `True`).
- `timeout` (float): Serial communication timeout.
- `source` (int): APT protocol source ID (default: `0x01`).
- `dest` (int): APT protocol destination ID (default: `0x50`).
- `stepspmm` (int): Steps per millimeter (default: `34555`).
- `minorStep`, `majorStep`, `jogStep` (float): Step sizes for different movements.


### `components/kurios.py`
The `Kurios` class provides an interface for controlling a Kurios Liquid Crystal Tunable Filter (LCTF) device over a serial connection. It supports querying device status, setting wavelength, and managing operational modes like black mode.

---

#### Features
- **Serial Communication**: Establishes and manages a serial connection to the Kurios device.
- **Tunable Wavelength**: Allows setting and querying the wavelength.
- **Device Status**: Retrieves device status, temperature, and operational range.
- **Callbacks**: Supports a callback function for reporting device information.

---

#### Constructor

##### `__init__(port='/dev/ttyUSB0', lctfCallback=None)`
Initializes the Kurios device and establishes a connection.

##### Parameters:
- `port` (str): Serial port to connect to (default: `/dev/ttyUSB0`).
- `lctfCallback` (function): Optional callback for reporting device status and updates.

---

#### Properties

##### `status`
- **Description**: Retrieves the current status of the device.
- **Type**: `Status` (Enum with values: `INIT`, `WARM`, `REDY`).

##### `temperature`
- **Description**: Retrieves the current temperature of the device in degrees Celsius.
- **Type**: `float`

##### `black`
- **Description**: Enables or disables the black mode.
- **Type**: `bool`

##### `wl`
- **Description**: Gets or sets the current wavelength.
- **Type**: `float`

---

#### Methods

##### `sendCommand(msg)`
- **Description**: Sends a command to the Kurios device and retrieves the response.
- **Parameters**:
  - `msg` (str): The command to send.
- **Returns**: `str` - The device response.

##### `report()`
- **Description**: Triggers the `lctfCallback` with the current wavelength, black mode, status, temperature, and operational range.

---

#### Internal Methods
- **`__connect()`**: Establishes a serial connection to the Kurios device.
- **`__initialize()`**: Configures the device and retrieves operational range (`WLmin` and `WLmax`).
- **`__disconnect()`**: Safely closes the serial connection.

---

#### Enums

##### `Status`
Represents the operational status of the device:
- `INIT`: Initializing
- `WARM`: Warming up
- `REDY`: Ready

---

### `components/polarization.py`
The `ThorlabsELL`, `ThorlabsELLx`, `ThorlabsELL9`, `ThorlabsELL14`, and `PolController` classes provide an interface for controlling Thorlabs Elliptec motorized devices, specifically rotation controller and 4 position slider, using serial communication.

---

#### Overview

- **ThorlabsELL**: Manages serial communication with the ELL device.
- **ThorlabsELLx**: Handles commands and properties for a single ELL channel.
- **ThorlabsELL9**: Controls filter wheels with predefined positions.
- **ThorlabsELL14**: Controls rotary stages with angular positioning.
- **PolController**: Combines multiple Thorlabs ELL devices (rotators and filters) into a unified controller.

---

#### 1. `ThorlabsELL` Class

##### Constructor
###### `__init__(port="/dev/ttyUSB0")`
Initializes the serial connection to the Thorlabs ELL device.

###### Parameters:
- `port` (str): Serial port for the device (default: `/dev/ttyUSB0`).

##### Methods
- **`sendCommand(msg)`**:
  - Sends a command string to the device and reads the response.
  - **Parameters**:
    - `msg` (str): Command string to send.
  - **Returns**: `str` - Response from the device.
- **`stop()`**:
  - Stops and disconnects the device.
- **Internal Methods**:
  - `__connect()`: Establishes the serial connection.
  - `__disconnect()`: Closes the serial connection.

---

#### 2. `ThorlabsELLx` Class

##### Constructor
###### `__init__(parent, channel)`
Initializes an ELL channel for controlling specific parameters.

###### Parameters:
- `parent`: Parent `ThorlabsELL` instance.
- `channel` (int): Channel number (e.g., 1, 2, or 3).

##### Properties
- **`position`**:
  - Gets or sets the position in encoder units.
  - **Type**: `int`
- **`jogStep`**:
  - Gets or sets the jog step in encoder units.
  - **Type**: `int`

##### Methods
- **`home(direction)`**:
  - Homes the channel in the specified direction.
  - **Parameters**:
    - `direction` (int): 0 for forward, 1 for backward.
- **`jog(direction)`**:
  - Performs a jog in the specified direction.
  - **Parameters**:
    - `direction` (int): 0 for forward, 1 for backward.
- **`execute(msg)`**:
  - Sends a command and processes the response.
- **`parser(rsp)`**:
  - Parses the response string into components (`channel`, `command`, `value`).

##### Helper Methods
- **`decode(hex_str)`**: Converts a hexadecimal string to an integer.
- **`encode(num)`**: Converts an integer to a padded hexadecimal string.

---

#### 3. `ThorlabsELL9` Class

##### Constructor
###### `__init__(parent, channel, callback)`
Specialized version of `ThorlabsELLx` for filter wheels with predefined positions.

###### Parameters:
- `parent`: Parent `ThorlabsELL` instance.
- `channel` (int): Channel number.
- `callback` (function): Optional callback for position updates.

##### Properties
- **`positionPos`**:
  - Gets or sets the filter position index (0 to 3).
  - **Type**: `int`

---

#### 4. `ThorlabsELL14` Class

##### Constructor
###### `__init__(parent, channel, callback)`
Specialized version of `ThorlabsELLx` for rotary stages with angular positioning.

###### Parameters:
- `parent`: Parent `ThorlabsELL` instance.
- `channel` (int): Channel number.
- `callback` (function): Optional callback for position updates.

##### Properties
- **`positionDeg`**:
  - Gets or sets the position in degrees.
  - **Type**: `float`
- **`jogStepDeg`**:
  - Gets or sets the jog step size in degrees.
  - **Type**: `float`

---

#### 5. `PolController` Class

##### Constructor
###### `__init__(port="/dev/ttyUSB0", rot1callback=None, rot2callback=None, flt1callback=None)`
Initializes the polarization controller, combining rotary stages and filter wheels.

###### Parameters:
- `port` (str): Serial port for the device (default: `/dev/ttyUSB0`).
- `rot1callback` (function): Optional callback for `rot1` updates.
- `rot2callback` (function): Optional callback for `rot2` updates.
- `flt1callback` (function): Optional callback for `flt1` updates.

##### Methods
- **`stop()`**:
  - Stops and disconnects the device.

## Adressing the hardware
The ports can be assigned dynamically, so unexpected behaviour can occur (e.g. the software might attempt to communicate with Thorlabs Elliptec protocol to a Kurious controller due to different assignment of serial ports). This problem can be solved easily under Linux OS by setting the port to a static value using rules in /etc/udev/rules.d as (adjust serial numbers as needed!). The hardware in this specific configuration is adjusted using the following rules
```
SUBSYSTEM=="tty", ATTRS{manufacturer}=="Thorlabs", ATTRS{serial}=="1234", SYMLINK+="kdc1001"
SUBSYSTEM=="tty", ATTRS{manufacturer}=="FTDI", ATTRS{serial}=="1234", SYMLINK+="ellb"
SUBSYSTEM=="tty", ATTRS{manufacturer}=="THORLABS", ATTRS{serial}=="1234", SYMLINK+="kurios"
```

## Acknowledgements
This work was done as part of the project "Order models for optical microscopy of biological tissues" (Z1-4384) financially supported by the SLovenian Research Agency. Project homepage: [here](https://www.ijs.si/ijsw/ARRSProjekti/2022/Modeli%20urejenosti%20za%20optično%20mikroskopijo%20bioloških%20tkiv)

## Disclaimer
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.