from enum import Enum


# Enum for filter validation
class FilterEnum(Enum):
    FILTER_1 = "1"
    FILTER_2 = "2"
    FILTER_3 = "3"
    FILTER_4 = "4"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


class AcquisitionFileParser:
    def __init__(self, file_content):
        self.file_content = file_content
        self.version = None
        self.acquisition = None
        self.steps = []

    def parse(self):
        is_steps_section = False

        # Split the string into lines
        lines = self.file_content.splitlines()

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):  # Skip comments and empty lines
                continue
            
            if line.startswith("VERSION"):
                self.version = line.split(" ")[1]  # Extract version number
                continue
            
            if line == "ACQUISITION":
                is_steps_section = False
                self.acquisition = Acquisition()
                continue
            elif line == "STEPS":
                is_steps_section = True
                continue
            
            if not is_steps_section:
                self.acquisition.parse_line(line)
            else:
                self.steps.append(Step.parse_line(line))

        self._validate()

    def _validate(self):
        if not self.acquisition.is_complete():
            raise ValueError("ACQUISITION section is missing required fields!")
        if len(self.steps) != self.acquisition.num_steps:
            raise ValueError(
                f"Number of steps read ({len(self.steps)}) does not match declared num_steps ({self.acquisition.num_steps})!"
            )


class Acquisition:
    def __init__(self):
        self.project = None
        self.experiment = None
        self.path = None
        self.date = None
        self.operator = None
        self.metadata = {}
        self.num_steps = 0

    def parse_line(self, line):
        if ":" in line:
            key, value = map(str.strip, line.split(":", 1))
            if key == "metadata":
                pass  # Metadata will be parsed from subsequent lines
            elif key.startswith("custom_") or key in {"description"}:
                self.metadata[key] = value
            elif key == "num_steps":
                self.num_steps = int(value)
            else:
                setattr(self, key, value)

    def is_complete(self):
        required_fields = {"project", "experiment", "path", "date", "operator", "num_steps"}
        return all(getattr(self, field) is not None for field in required_fields)


class Step:
    def __init__(self, step, t_int, gain, z_pos, lam, phi_g, phi_a, flt_a):
        self.step = int(step)
        self.t_int = float(t_int)
        self.gain = float(gain)
        self.z_pos = float(z_pos)
        self.lam = float(lam)
        self.phi_g = float(phi_g)
        self.phi_a = float(phi_a)
        self.flt_a = flt_a

        # Validate filter using Enum
        if not FilterEnum.has_value(self.flt_a):
            raise ValueError(f"Invalid filter value '{self.flt_a}'. Allowed values are 1, 2, 3, or 4.")

    @classmethod
    def parse_line(cls, line):
        """Parse a line from the STEPS section into a Step object."""
        values = line.split("\t")
        return cls(*values)

    def __repr__(self):
        return (
            f"Step(step={self.step}, t_int={self.t_int}, gain={self.gain}, "
            f"z_pos={self.z_pos}, lam={self.lam}, phi_g={self.phi_g}, "
            f"phi_a={self.phi_a}, flt_a='{self.flt_a}')"
        )