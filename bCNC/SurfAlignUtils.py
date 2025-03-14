import bpy
import os
import sys
import warnings
from scipy.spatial import ConvexHull
import numpy as np
import matplotlib.pyplot as plt
import re
import math

def setup_blender_scene(engrave_text, text_width_mm, text_height_mm, text_position_mm, rotation_degrees, layer_height_mm, safe_height_mm, save_dir, feedrate_mm, spindle_rpm):
    blend_file_path = os.path.join(save_dir, "output.blend")
    addon_name = "bl_ext.user_default.fabex"
    
    # Suppress warnings
    warnings.filterwarnings("ignore")
    
    # Suppress print output
    original_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
    
    try:
        # Enable Addon
        if addon_name not in bpy.context.preferences.addons:
            bpy.ops.preferences.addon_enable(module=addon_name)
            print(f"Addon '{addon_name}' enabled successfully.")
        else:
            print(f"Addon '{addon_name}' is already enabled.")

        # Set Render Engine
        bpy.context.scene.render.engine = 'FABEX_RENDER'
        bpy.context.scene.interface.level = '2'
        bpy.context.scene.cam_machine.feedrate_default = 1.51

        # Set units to millimeters
        # bpy.context.scene.unit_settings.system = 'METRIC'
        # bpy.context.scene.unit_settings.scale_length = 0.001
        bpy.context.scene.unit_settings.length_unit = 'MILLIMETERS'  # Set units to millimeters

        # Remove all objects
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)

        # Add text object
        bpy.ops.object.text_add(location=(0, 0, 0))
        text_obj = bpy.context.object
        text_obj.data.body = engrave_text

        # Convert Text to Mesh to Get Accurate Dimensions
        bpy.ops.object.convert(target='MESH')
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

        # Get Actual Dimensions After Conversion
        dimensions = text_obj.dimensions
        print("Actual Dimensions After Conversion:", dimensions)

        # Scale text object to fit within 50mm x 100mm while keeping aspect ratio
        scale_factor = min(text_width_mm / (dimensions.x * 1000), text_height_mm / (dimensions.y * 1000))
        text_obj.scale = (scale_factor, scale_factor, scale_factor)
        text_pos_meters = (text_position_mm[0] / 1000, text_position_mm[1] / 1000, text_position_mm[2] / 1000)
        # Move text object to a new location (e.g., (0, 0, 1))
        text_obj.location = text_pos_meters
        text_obj.rotation_euler = (0, 0, math.radians(rotation_degrees))  # Convert to radians


        bpy.ops.scene.cam_operation_add()
        

        bpy.ops.wm.save_as_mainfile(filepath=blend_file_path)

        # print(f"✅ COMPLETED! Text is properly sized to {text_width_mm}mm x {text_height_mm}mm")

        bpy.context.scene.cam_operations[0].cut_type = 'ONLINE'
        bpy.context.scene.cam_operations[0].stepdown = layer_height_mm / 1000  # layer height
        bpy.context.scene.cam_operations[0].movement.free_height = safe_height_mm / 1000  # Safe height
        bpy.context.scene.cam_operations[0].outlines_count = 2
        bpy.context.scene.cam_operations[0].feedrate = feedrate_mm/1000
        bpy.context.scene.cam_operations[0].spindle_rpm = spindle_rpm

        bpy.ops.object.calculate_cam_path()

        bpy.ops.wm.save_as_mainfile(filepath=blend_file_path)
        
        gcode_file_path = os.path.join(save_dir, "Op_Text_1.tap")
        # Instead of closing, reset the scene
        bpy.ops.wm.read_factory_settings(use_empty=True)

        # print("✅ COMPLETED! GCODE is generated", blend_file_path)
        
    finally:
        sys.stdout.close()
        sys.stderr.close()
        # Restore original print output
        sys.stdout = original_stdout
        warnings.resetwarnings()
    

    return gcode_file_path




def parse_gcode(gcode_file_path):
    coordinates = []
    z_layers = {}
    current_position = {'X': 0, 'Y': 0, 'Z': 0}
    last_gcode = "G0"  # Default movement mode is G0

    with open(gcode_file_path, 'r') as file:
        for line in file:
            line = line.strip()

            # Detect and update last G-code command
            if line.startswith("G") :
                last_gcode = line[:2]  # Extract the command (G0/G1)

            if last_gcode == "G0" or last_gcode == "G1":

                # Extract X, Y, Z coordinates from the line
                match_x = re.search(r'X([-+]?[0-9]*\.?[0-9]+)', line)
                match_y = re.search(r'Y([-+]?[0-9]*\.?[0-9]+)', line)
                match_z = re.search(r'Z([-+]?[0-9]*\.?[0-9]+)', line)

                if match_x:
                    current_position['X'] = float(match_x.group(1))
                if match_y:
                    current_position['Y'] = float(match_y.group(1))
                if match_z:
                    current_position['Z'] = float(match_z.group(1))

                # Store the coordinate with the last valid G-code
                x, y, z = current_position['X'], current_position['Y'], current_position['Z']
                coordinates.append((x, y, z))

                if z not in z_layers:
                    z_layers[z] = []
                z_layers[z].append((x, y))
    
    return z_layers


def get_probe_points(z_layers, n_probe_points=3):
    # Find the lowest Z layer
    min_z = min(z_layers.keys())
    # print("BOTTOM LAYER", min_z, z_layers[min_z])
    bottom_layer_points = np.array(z_layers[min_z])

    # Remove duplicate points
    bottom_layer_points = np.unique(bottom_layer_points, axis=0)

    if len(bottom_layer_points) < 3:
        print("⚠️ Not enough unique points for Convex Hull! Returning available points.")
        return bottom_layer_points.tolist(), bottom_layer_points.tolist(), min_z, bottom_layer_points, None

    # Compute Convex Hull
    hull = ConvexHull(bottom_layer_points)

    # Select evenly spaced probe points from hull vertices
    hull_points = [tuple(bottom_layer_points[vertex]) for vertex in hull.vertices]

    if len(hull_points) <= n_probe_points:
        probe_points = hull_points
    else:
        step = len(hull_points) // n_probe_points
        probe_points = hull_points[::step][:n_probe_points]

    return probe_points, hull_points, min_z, bottom_layer_points, hull



def plot_probe_points(z_layers, probe_points, min_z, bottom_layer_points, hull):
    # 3D Plot including probe points
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Plot all G-code points (faded for context)
    for z, xy_list in z_layers.items():
        x, y = zip(*xy_list)
        z_list = [z] * len(x)
        ax.scatter(x, y, z_list, color='black', s=5, alpha=0.3)

    # Plot probe points on the bottom layer
    probe_x, probe_y = zip(*probe_points)
    probe_z = [min_z] * len(probe_x)
    ax.scatter(probe_x, probe_y, probe_z, color='red', s=50, label='Probe Points')

    # Draw convex hull edges for visualization
    for simplex in hull.simplices:
        x_hull = bottom_layer_points[simplex, 0]
        y_hull = bottom_layer_points[simplex, 1]
        z_hull = [min_z, min_z]
        ax.plot(x_hull, y_hull, z_hull, 'g-', linewidth=1)

    ax.set_xlabel('X Axis')
    ax.set_ylabel('Y Axis')
    ax.set_zlabel('Z Axis')
    ax.legend()
    plt.show()