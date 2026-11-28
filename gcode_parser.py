import re


class GcodeParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.layers = []  # List of (layer_index, line_number, z_height)

    def parse(self):
        with open(self.file_path, 'r') as f:
            return self.parse_lines(f)

    def parse_lines(self, lines):
        self.layers = []
        last_z = "0.0"
        for line_number, line in enumerate(lines, start=1):
            # Z can change on any movement command, including G0 and G1.
            # Ignore semicolon comments so their text cannot look like a move.
            command = line.split(';', 1)[0]
            z_match = re.search(
                r'(?<![A-Za-z])Z\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))',
                command,
                re.IGNORECASE,
            )
            if z_match:
                last_z = z_match.group(1)

            layer_marker = re.match(r'\s*;\s*LAYER\s*:\s*(-?\d+)', line, re.IGNORECASE)
            if layer_marker:
                layer_index = int(layer_marker.group(1))
                self.layers.append((layer_index, line_number, last_z))

        return self.layers
