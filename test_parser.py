from parser import GcodeParser

parser = GcodeParser('test.gcode')
layers = parser.parse()
print(layers)
