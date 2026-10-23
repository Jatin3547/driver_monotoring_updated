"""Quick utility to detect available cameras and identify your phone/webcam index."""

import sys

try:
    import cv2
except ImportError:
    print("Error: OpenCV is not installed. Run: pip install opencv-python")
    sys.exit(1)


def check_cameras(max_to_check: int = 5):
    print("========================================")
    print(" FLEETGUARD — CAMERA DETECTOR")
    print("========================================")
    found_any = False

    for idx in range(max_to_check):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(idx)

        if cap.isOpened():
            ok, frame = cap.read()
            if ok and frame is not None:
                h, w = frame.shape[:2]
                print(f"[+] Camera Index {idx}: AVAILABLE (Resolution: {w}x{h})")
                found_any = True
            cap.release()

    if not found_any:
        print("[-] No active camera detected. Ensure DroidCam is connected and started.")
    else:
        print("========================================")
        print("Set AI_CAMERA_INDEX in backend/.env to the index corresponding to your phone.")


if __name__ == "__main__":
    check_cameras()
