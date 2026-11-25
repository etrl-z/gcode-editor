import re

class GcodeParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.layers = [] # List of (layer_index, line_number, z_height)

    def parse(self):
        with open(self.file_path, 'r') as f:
            lines = f.readlines()
            last_z = "0.0"
            for i, line in enumerate(lines):
                # Aggiorna l'ultima Z nota
                z_match = re.search(r'G1\s+.*Z([\d\.]+)', line)
                if z_match:
                    last_z = z_match.group(1)

                if line.startswith(';LAYER:'):
                    layer_index = int(line.split(':')[1].strip())
                    # i è 0-indexed, quindi la linea 1 corrisponde a i=0.
                    # Se dici che il layer 0 è a riga 40, significa i=39.
                    # Il codice attuale usa i direttamente.
                    # Se vuoi che l'interfaccia mostri numeri di riga 1-based, aggiungiamo 1.
                    self.layers.append((layer_index, i + 1, last_z))
        return self.layers
