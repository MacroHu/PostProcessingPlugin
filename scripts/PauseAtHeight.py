from ..Script import Script


class PauseAtHeight(Script):
    def __init__(self):
        super().__init__()

    def getSettingDataString(self):
        return """{
            "name":"Pause at height",
            "key": "PauseAtHeight",
            "metadata": {},
            "version": 2,
            "settings":
            {
                "pause_height":
                {
                    "label": "Pause height",
                    "description": "At what height should the pause occur",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 5.0
                },
                "head_park_x":
                {
                    "label": "Head park X",
                    "description": "What x location does the head move to when pausing.",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 190
                },
                "head_park_y":
                {
                    "label": "Head park Y",
                    "description": "What y location does the head move to when pausing.",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 190
                },
                "retraction_ammount":
                {
                    "label": "Retraction",
                    "description": "How much fillament must be retracted at pause.",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 0
                },
                "extrude_amount":
                {
                    "label": "Extrude amount",
                    "description": "How much filament should be extruded after pause. This is needed when doing a material change on Ultimaker2's to compensate for the retraction after the change. In that case 128+ is recommended.",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 0
                },
                "redo_layers":
                {
                    "label": "Redo layers",
                    "description": "Redo a number of previous layers after a pause to increases adhesion.",
                    "unit": "layers",
                    "type": "int",
                    "default_value": 0
                }
            }
        }"""

    def execute(self, data):
        x = 0.
        y = 0.
        current_z = 0.
        pause_z = self.getSettingValueByKey("pause_height")
        retraction_amount = self.getSettingValueByKey("retraction_amount")
        extrude_amount = self.getSettingValueByKey("extrude_amount")
        park_x = self.getSettingValueByKey("head_park_x")
        park_y = self.getSettingValueByKey("head_park_y")
        layers_started = False
        redo_layers = self.getSettingValueByKey("redo_layers")
        for layer in data:
            lines = layer.split("\n")
            for line in lines:
                if ";LAYER:0" in line:
                    layers_started = True
                    continue

                if not layers_started:
                    continue

                if self.getValue(line, 'G') == 1 or self.getValue(line, 'G') == 0:
                    current_z = self.getValue(line, 'Z')
                    x = self.getValue(line, 'X', x)
                    y = self.getValue(line, 'Y', y)
                    if current_z is not None:
                        if current_z >= pause_z:
                            index = data.index(layer)
                            previous_layer = data[index - 1]
                            previous_lines = previous_layer.split("\n")
                            current_e = 0.
                            for prevLine in reversed(previous_lines):
                                current_e = self.getValue(prevLine, 'E', -1)
                                if current_e >= 0:
                                    break

                            prepend_gcode = ";TYPE:CUSTOM\n"
                            prepend_gcode += ";added code by post processing\n"
                            prepend_gcode += ";script: PauseAtHeight.py\n"
                            prepend_gcode += ";current z: %f \n" % (current_z)

                            # Retraction
                            prepend_gcode += "M83\n"
                            if retraction_amount != 0:
                                prepend_gcode += "G1 E-%f F6000\n" % retraction_amount

                            # Move the head away
                            prepend_gcode += "G1 Z%f F300\n" % (current_z + 1)
                            prepend_gcode += "G1 X%f Y%f F9000\n" % (park_x, park_y)
                            if current_z < 15:
                                prepend_gcode += "G1 Z15 F300\n"

                            # Disable the E steppers
                            prepend_gcode += "M84 E0\n"
                            # Wait till the user continues printing
                            prepend_gcode += "M0 ;Do the actual pause\n"

                            # Push the filament back
                            if retraction_amount != 0:
                                prepend_gcode += "G1 E%f F6000\n" % retraction_amount

                            # Optionally extrude material
                            if extrude_amount != 0:
                                prepend_gcode += "G1 E%f F200\n" % extrude_amount

                            # Retract again, the properly primes the nozzle when changing filament.
                            if retraction_amount != 0:
                                prepend_gcode += "G1 E-%f F6000\n" % retraction_amount

                            # Move the head back
                            prepend_gcode += "G1 Z%f F300\n" % (current_z + 1)
                            prepend_gcode += "G1 X%f Y%f F9000\n" % (x, y)
                            if retraction_amount != 0:
                                prepend_gcode += "G1 E%f F6000\n" % retraction_amount
                            prepend_gcode += "G1 F9000\n"
                            prepend_gcode += "M82\n"

                            # Reset extrude value to pre pause value
                            prepend_gcode += "G92 E%f\n" % current_e

                            layer = prepend_gcode + layer

                            # Include a number of previous layers
                            for i in range(1, redo_layers + 1):
                                previous_layer = data[index - i]
                                layer = previous_layer + layer

                            data[index] = layer  # Override the data of this layer with the modified data
                            return data
                        break
        return data
