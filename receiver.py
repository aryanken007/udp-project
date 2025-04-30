import time
from pathlib import Path 
import cv2, socket, struct, numpy as np

UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT))
print(f"Listening on UDP/*:{UDP_PORT}")

IMG_DIR = Path(__file__).resolve().parent / "image_review" / "images"
IMG_DIR.mkdir(parents=True, exist_ok=True)

while True:
    # ── read the 4-byte size header ──
    header, _ = sock.recvfrom(65536)
    if len(header) < 4:
        continue
    frame_size = struct.unpack('>I', header[:4])[0]

    # ── grab the JPEG payload (may arrive split across datagrams) ──
    data = header[4:]
    while len(data) < frame_size:
        packet, _ = sock.recvfrom(65536)
        data += packet

    # ── decode & show ──
    img = cv2.imdecode(np.frombuffer(data[:frame_size], dtype=np.uint8),
                       cv2.IMREAD_COLOR)

    if img is None:
        continue
    
    ts = int(time.time() * 1000)
    cv2.imwrite(str(IMG_DIR / f"{ts}.jpg"), img)

    cv2.imshow('UDP Stream', img)
    if cv2.waitKey(1) & 0xFF == 27:   # ESC to quit
        break

cv2.destroyAllWindows()
