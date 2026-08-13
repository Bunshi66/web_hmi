import os
import sys

# Ensure backend path is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=== Standalone Hardware Diagnostics ===")
print("This script bypasses FastAPI and tests the camera connection directly.")

try:
    from app.services.camera_sdk import CameraSDK
except ImportError as e:
    print(f"[ERROR] Could not import CameraSDK: {e}")
    print("Make sure you are running this from the backend/ directory or have dependencies installed.")
    sys.exit(1)

def test_hardware():
    sdk = CameraSDK()
    
    print("\n--- Attempting to connect ---")
    connected = sdk.connect()
    
    if connected:
        print("[SUCCESS] Camera is connected!")
        
        print("\n--- Testing frame grab ---")
        try:
            frame = sdk.get_frame()
            if frame is not None:
                print(f"[SUCCESS] Grabbed frame of shape: {frame.shape}")
            else:
                print("[ERROR] get_frame() returned None")
        except Exception as e:
            print(f"[ERROR] Exception during get_frame: {e}")
            
        print("\n--- Disconnecting ---")
        sdk.disconnect()
        print("[SUCCESS] Disconnected cleanly.")
    else:
        print("[FAILURE] Could not connect to the camera.")
        print("Check if the network link is 1000Mbps and the camera is reachable.")

if __name__ == "__main__":
    test_hardware()
