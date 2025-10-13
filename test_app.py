"""Test script to debug application startup."""
import sys
import traceback

try:
    print("Starting application...")
    from cgns_gui.app import main
    print("Main imported successfully")
    sys.exit(main())
except Exception as e:
    print(f"Error occurred: {e}")
    traceback.print_exc()
    sys.exit(1)
