import cv2
import os

# Tự động lấy đường dẫn tuyệt đối bất kể bạn chạy lệnh từ thư mục nào
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
video_path = os.path.join(BASE_DIR, 'data', 'videos', 'baixe.mp4')
cap = cv2.VideoCapture(video_path)
ret, frame = cap.read()
if not ret:
    print("Không thể đọc video!")
    exit()

# Thu nhỏ frame nếu quá to (tuỳ chọn)
frame = cv2.resize(frame, (1280, 720))

slots = {}
slot_count = 1

print("HƯỚNG DẪN:")
print("- Giữ chuột trái và kéo để vẽ Ô ĐỖ XE.")
print("- Nhấn phím SPACE hoặc ENTER để CHỐT ô vừa vẽ.")
print("- Nhấn phím C để HỦY vẽ ô hiện tại.")
print("- Nhấn phím ESC khi ĐÃ VẼ XONG TẤT CẢ 20 Ô.")

while True:
    clone = frame.copy()
    cv2.putText(clone, f"Hay ve Slot {slot_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.putText(clone, "Keo chuot de ve -> Nhan SPACE de luu -> Nhan ESC de ket thuc", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    
    r = cv2.selectROI("Ve Toa Do 20 O Do Xe", clone, fromCenter=False, showCrosshair=True)
    
    # Nếu bấm ESC không vẽ nữa thì (0,0,0,0) sẽ trả về
    if r == (0, 0, 0, 0):
        break
        
    x, y, w, h = int(r[0]), int(r[1]), int(r[2]), int(r[3])
    
    slots[f"Slot {slot_count}"] = {
        "box": [x, y, x+w, y+h],
        "color_empty": (0, 255, 0),
        "color_occ": (0, 0, 255)
    }
    
    # Vẽ ô in dính lên frame hiện tại để user thấy họ đã vẽ cái nào rồi
    cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
    cv2.putText(frame, str(slot_count), (x+5, y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
    
    print(f"[Đã lưu] Slot {slot_count}: Tọa độ {[x, y, x+w, y+h]}")
    slot_count += 1

cv2.destroyAllWindows()

print("\n" + "="*50)
print("BẠN HÃY COPY ĐOẠN CODE DƯỚI ĐÂY (TỪ CHỮ SLOTS = { ... })")
print("VÀ CHÉP ĐÈ VÀO BIẾN `SLOTS` TRONG FILE `core/parking.py` NHÉ:\n")

print("SLOTS = {")
for idx, (name, data) in enumerate(slots.items()):
    comma = "," if idx < len(slots)-1 else ""
    print(f'    "{name}": {{')
    print(f'        "box": {data["box"]},')
    print(f'        "color_empty": (0, 255, 0),')
    print(f'        "color_occ": (0, 0, 255)')
    print(f'    }}{comma}')
print("}")
print("="*50)
