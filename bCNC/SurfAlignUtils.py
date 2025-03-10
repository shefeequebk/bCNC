import bpy
import os
import sys
import warnings

def setup_blender_scene(engrave_text, text_width_mm, text_height_mm, text_position_mm, layer_height_mm, safe_height_mm, save_dir):
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
        

        bpy.ops.scene.cam_operation_add()
        

        bpy.ops.wm.save_as_mainfile(filepath=blend_file_path)

        # print(f"✅ COMPLETED! Text is properly sized to {text_width_mm}mm x {text_height_mm}mm")

        bpy.context.scene.cam_operations[0].cut_type = 'ONLINE'
        bpy.context.scene.cam_operations[0].stepdown = layer_height_mm / 1000  # layer height
        bpy.context.scene.cam_operations[0].movement.free_height = safe_height_mm / 1000  # Safe height
        bpy.context.scene.cam_operations[0].outlines_count = 2

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

