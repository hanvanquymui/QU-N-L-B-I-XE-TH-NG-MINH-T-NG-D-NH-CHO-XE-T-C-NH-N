import cv2
import time
from core.camera import VideoCamera
from core.parking import process_occupancy
from config import Config
from database.db_manager import db
from database.models.vehicle import ParkingSession

# Biến global lưu camera thứ 2 (dùng cho bãi đỗ)
camera_occupancy = None
previous_status = {}

# [NÂNG CẤP] Biến global chia sẻ trạng thái slot real-time cho API /api/live_status
live_slot_status = {
    "slots": {},        # {"O_1": "OCCUPIED", "O_2": "EMPTY", ...}
    "available": 0,
    "occupied": 0,
    "total": 20
}

def get_occupancy_camera():
    global camera_occupancy
    if camera_occupancy is None:
        camera_occupancy = VideoCamera(Config.VIDEO_CAM2)
    return camera_occupancy

def generate_occupancy_stream(app):
    """
    Worker này nối kết với Camera 2, gửi frame sang hàm tìm chỗ trống.
    Và liên kết dữ liệu với Database để theo dõi vé xe.
    """
    global previous_status
    cam = get_occupancy_camera()
    
    while True:
        frame = cam.get_frame()
        if frame is None:
            continue
            
        # 1. Pipeline AI: Tìm ô còn trống
        annotated_frame, status_dict = process_occupancy(frame)
        
        # 2. Xử lý logic như báo đèn, gán slot cho xe
        if status_dict:
            # [NÂNG CẤP] Cập nhật biến global cho API real-time
            available_count = sum(1 for v in status_dict.values() if v == "EMPTY")
            occupied_count = len(status_dict) - available_count
            live_slot_status["slots"] = status_dict.copy()
            live_slot_status["available"] = available_count
            live_slot_status["occupied"] = occupied_count
            live_slot_status["total"] = len(status_dict)
            
            if not previous_status:
                previous_status = status_dict.copy()
            else:
                for slot_id, status in status_dict.items():
                    # Nếu ô chuyển từ EMPTY sang OCCUPIED -> Có xe mới đỗ vào ô
                    if previous_status.get(slot_id) == "EMPTY" and status == "OCCUPIED":
                        # Kết nối CSDL để tìm xe vừa vãng lai vào cổng mà chưa có chỗ
                        with app.app_context():
                            unassigned_session = ParkingSession.query.filter_by(
                                status="PARKING", 
                                slot_id=None
                            ).order_by(ParkingSession.time_in.desc()).first()
                            
                            if unassigned_session:
                                unassigned_session.slot_id = slot_id
                                db.session.commit()
                                print(f"[MỚI_GÁN_CHỖ] Biển {unassigned_session.license_plate} đã đỗ an vị ở lô {slot_id}")
                    
                    previous_status[slot_id] = status
        
        # 3. Chuyển đổi để frontend Flask hiện lên
        ret, jpeg = cv2.imencode('.jpg', annotated_frame)
        if not ret:
            continue
            
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
