import bpy
import os
import shutil


def install_addon(zip_path):
    """Installs a Blender addon from a given ZIP file path without UI."""
    addon_name = os.path.splitext(os.path.basename(zip_path))[0]  # Extract addon name

    # Ensure the ZIP file exists
    if not os.path.isfile(zip_path):
        print(f"❌ ERROR: ZIP file not found at {zip_path}")
        return False

    # Get Blender's addon directory
    addon_dir = os.path.join(bpy.utils.user_resource('SCRIPTS'), "addons")

    # Uninstall if already installed
    if addon_name in bpy.context.preferences.addons:
        print(f"🔄 Uninstalling existing addon: {addon_name}")
        bpy.ops.preferences.addon_disable(module=addon_name)
        bpy.ops.preferences.addon_remove(module=addon_name)

    # Install the addon
    print(f"📂 Installing addon from: {zip_path}")
    bpy.ops.wm.addon_install(filepath=zip_path)

    # Enable the addon
    try:
        bpy.ops.preferences.addon_enable(module=addon_name)
        print(f"✅ Addon '{addon_name}' installed and enabled!")
        return True
    except Exception as e:
        print(f"❌ ERROR: Failed to enable addon '{addon_name}' - {e}")
        return False


# Example Usage (Replace with your ZIP file path)
zip_file_path = "C:/path/to/your/addon.zip"  # Update with actual addon ZIP path
install_addon(zip_file_path)
