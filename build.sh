#!/bin/bash

# Build Script for PLAXIS 3D Spudcan Automation Tool using PyInstaller

echo "Starting build process..."

# --- Configuration ---
APP_NAME="PlaxisSpudcanAutomator"
MAIN_SCRIPT="src/main.py"
OUTPUT_DIR_BASE="dist" # PyInstaller will create a subfolder named APP_NAME here
BUILD_TEMP_DIR="build_temp" # PyInstaller's working directory

# Icon - Optional: If you have an icon, place it in resources and uncomment.
# ICON_FILE="resources/app_icon.ico"
ICON_OPTION="" # Default to no icon if ICON_FILE is not set or not found

# Check if icon file exists and set option
# if [ -f "$ICON_FILE" ]; then
#    ICON_OPTION="--icon=$ICON_FILE"
#    echo "Using icon: $ICON_FILE"
# else
#    echo "Icon file not found at $ICON_FILE. Building without an icon."
# fi

# --- Clean Previous Builds ---
echo "Cleaning previous builds..."
rm -rf "./${OUTPUT_DIR_BASE}/${APP_NAME}" # Output directory for bundled app
rm -rf "./${BUILD_TEMP_DIR}"       # PyInstaller work directory
rm -f "./${APP_NAME}.spec"         # PyInstaller spec file (if generated outside OUTPUT_DIR_BASE)
rm -f "./${OUTPUT_DIR_BASE}/${APP_NAME}.spec"

# --- Create Output Directory (if it doesn't exist) ---
mkdir -p "./${OUTPUT_DIR_BASE}"

# --- Run PyInstaller ---
echo "Running PyInstaller..."

# Common PyInstaller options for a PySide6 GUI application:
# --name: Name of the executable and output folder.
# --onefile: Create a single executable file (can be slower to start).
#            Default is one-folder bundle (faster startup, more files). Let's use one-folder for now.
# --windowed: Prevents a console window from appearing (for GUI apps on Windows). Use --noconsole on macOS.
# --noconfirm: Replace output directory without asking.
# --paths: Add paths for PyInstaller to search for imports (similar to PYTHONPATH).
# --add-data: To include non-binary files (e.g., images, data). Syntax: <SRC_PATH_OS_SEP_DEST_PATH>
#             Example: --add-data "resources/image.png:resources"
# --hidden-import: To manually include modules PyInstaller might miss.
# --distpath: Where to put the final bundled app.
# --workpath: Where to put temporary PyInstaller working files.

# For a one-folder bundle:
pyinstaller \
    --name "$APP_NAME" \
    --windowed \
    --noconfirm \
    --paths "./src" \
    "$ICON_OPTION" \
    --distpath "./${OUTPUT_DIR_BASE}" \
    --workpath "./${BUILD_TEMP_DIR}" \
    "$MAIN_SCRIPT"

# Example for a one-file bundle (if preferred later):
# pyinstaller \
#     --name "$APP_NAME" \
#     --onefile \
#     --windowed \
#     --noconfirm \
#     --paths "./src" \
#     "$ICON_OPTION" \
#     --distpath "./${OUTPUT_DIR_BASE}" \
#     --workpath "./${BUILD_TEMP_DIR}" \
#     "$MAIN_SCRIPT"

# Check if PyInstaller was successful
if [ $? -eq 0 ]; then
    echo "PyInstaller completed successfully."
    echo "Executable and associated files are in ./${OUTPUT_DIR_BASE}/${APP_NAME}"
else
    echo "PyInstaller failed. Check the output above for errors."
    exit 1
fi

# --- Post-build steps (Optional) ---
# echo "Performing post-build steps (e.g., creating an archive)..."
# Example: Create a zip archive of the one-folder bundle
# if [ -d "./${OUTPUT_DIR_BASE}/${APP_NAME}" ]; then
#   echo "Creating zip archive..."
#   (cd "./${OUTPUT_DIR_BASE}" && zip -r "${APP_NAME}_bundle.zip" "$APP_NAME")
#   echo "Archive created: ./${OUTPUT_DIR_BASE}/${APP_NAME}_bundle.zip"
# fi

echo "Build process finished."
echo "To run the application, navigate to ./${OUTPUT_DIR_BASE}/${APP_NAME} and run $APP_NAME (or $APP_NAME.exe on Windows)."
echo "Ensure PyInstaller is installed (pip install pyinstaller) and this script is executable (chmod +x build.sh)."

exit 0
