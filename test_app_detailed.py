"""Detailed test script to debug application startup."""
import sys
import os

# Set environment to show more info
os.environ['QT_LOGGING_RULES'] = '*.debug=false;qt.qpa.*=true'

print("Step 1: Importing modules...")
try:
    from cgns_gui.app import main, _prepare_environment, MainWindow
    from PySide6.QtWidgets import QApplication
    print("✓ Modules imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 2: Preparing environment...")
try:
    _prepare_environment(False)
    print("✓ Environment prepared")
except Exception as e:
    print(f"✗ Environment preparation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 3: Creating QApplication...")
try:
    app = QApplication(sys.argv)
    app.setApplicationName("CGNS Viewer Test")
    print(f"✓ QApplication created, platform: {app.platformName()}")
except Exception as e:
    print(f"✗ QApplication creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 4: Creating MainWindow...")
try:
    window = MainWindow()
    print("✓ MainWindow created")
except Exception as e:
    print(f"✗ MainWindow creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 5: Showing window...")
try:
    window.show()
    print(f"✓ Window.show() called, visible: {window.isVisible()}")
except Exception as e:
    print(f"✗ Window.show() failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 6: Starting window...")
try:
    window.start()
    print("✓ Window.start() called")
except Exception as e:
    print(f"✗ Window.start() failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 7: Running event loop...")
print("If you see a window, the application is working!")
print("Press Ctrl+C to exit if the window is stuck...")
sys.exit(app.exec())
