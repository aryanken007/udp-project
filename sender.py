#!/usr/bin/env python3
"""
sender.py  –  Press SPACE on the console to grab ONE frame from the Logitech
camera and blast it as a JPEG to the receiver.  ESC quits.

•   Waits until a camera is actually plugged in.
•   Tries /dev/video0 … /dev/video4 automatically.
•   Cross-platform terminal key capture (works over SSH).
"""

import cv2, socket, struct, sys, time, platform

# ─────────────────────────── Config ───────────────────────────────────────────
UDP_IP        = "172.20.10.11"      # ← laptop IP
UDP_PORT      = 5005
FRAME_W, FRAME_H = 320, 240
JPEG_QUALITY  = 80                 # 0-100

# ───────────────── Camera helper (borrowed from your first code) ──────────────
def find_camera(max_index: int = 5):
    """Return an opened cv2.VideoCapture or None if none found."""
    for idx in range(max_index):
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            print(f"[sender] Camera found at index {idx}")
            # set resolution once we know we have a camera
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
            return cap
        cap.release()
    return None

# ───────────────── Key-press helper (SPACE / ESC) ─────────────────────────────
def wait_for_space() -> bool:
    """Block until SPACE (return True) or ESC (return False) is pressed."""
    print("[sender] Press SPACE to capture, ESC to quit.")
    if platform.system() == "Windows":         # (the board runs Linux, but keep)
        import msvcrt
        while True:
            k = msvcrt.getch()
            if k == b' ':      return True
            if k == b'\x1b':   return False
    else:                                       # POSIX: Linux, macOS, Android
        import termios, tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch == ' ':   return True
                if ch == '\x1b':return False
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

# ─────────────────────────── Main program ─────────────────────────────────────
print("[sender] Waiting for camera to be connected …")
cap = None
while cap is None:
    cap = find_camera()
    if cap is None:
        print("[sender] No camera yet – retrying in 2 s.")
        time.sleep(2)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

try:
    while True:
        if not wait_for_space():          # User pressed ESC
            print("[sender] Exiting.")
            break

        ok, frame = cap.read()
        if not ok:
            print("[sender] ⚠️  Failed to grab frame – trying again.")
            continue

        ok, buf = cv2.imencode(
            '.jpg', frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
        )
        if not ok:
            print("[sender] ⚠️  JPEG encode failed.")
            continue

        data = buf.tobytes()
        header = struct.pack('>I', len(data))   # 4-byte big-endian length
        sock.sendto(header + data, (UDP_IP, UDP_PORT))
        print(f"[sender] ✅ Sent {len(data)}-byte JPEG to {UDP_IP}:{UDP_PORT}")

finally:
    if cap: cap.release()
    sock.close()
