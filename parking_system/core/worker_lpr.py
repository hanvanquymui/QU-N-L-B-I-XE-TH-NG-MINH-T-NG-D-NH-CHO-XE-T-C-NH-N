import cv2
import time
import os
from collections import deque
from core.camera import VideoCamera
from core.ocr import process_lpr
from config import Config
from database.db_manager import db
from database.models.vehicle import VehicleLog, ParkingSession
from datetime import datetime

# Biến global lưu camera_lpr để không khởi tạo lại khi tải lại trang web
camera_lpr = None

# Bộ lọc thông minh (Debouncing): Lưu trữ thời gian xe vừa đọc biển.
# Do Camera 1 giây chụp tới 30 ảnh, ta phải chặn không cho AI ghi liên tục 30 dòng dữ liệu / giây vào Database!
plate_cache = {}

# [NÂNG CẤP] Hàng đợi thông báo xe RA - Frontend sẽ poll để hiện popup
# Mỗi item: {"plate": "92C-88888", "fee": "30,000 đ", "time": "11:20", "duration": "2h 15m"}
exit_alert_queue = deque(maxlen=10)

def handle_plate_db(app, plate_text, snapshot_img):
    now = time.time()
    
    # Lọc rác AI EasyOCR (các chữ lang băm bị nhận diện nhầm, biển thật phải >= 4 ký tự)
    if len(plate_text) < 4:
        return
        
    # Check Spam 60 giây: Nếu biển số này mới được ghi hình chưa quá 1 phút, thì bỏ qua không lưu DB nữa
    if plate_text in plate_cache:
        last_seen = plate_cache[plate_text]
        if now - last_seen < 60:
            plate_cache[plate_text] = now # Gia hạn thời gian
            return
        else:
            # 1 Phút rồi mới xuất hiện lại -> Coi như Xe ĐI RA (OUT)
            action = "OUT"
    else:
        # Lần đầu chạm mặt -> Xe ĐI VÀO (IN)
        action = "IN"
        
    plate_cache[plate_text] = now
    
    # Nâng cấp Lớp Hình Ảnh Mới: Setup lưu file cứng lên ổ đĩa
    image_rel_path = None
    if snapshot_img is not None:
        upload_dir = os.path.join(app.root_path, 'static', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        filename = f"{plate_text}_{int(now)}.jpg"
        filepath = os.path.join(upload_dir, filename)
        cv2.imwrite(filepath, snapshot_img)
        image_rel_path = f"uploads/{filename}" # Đường link truy xuất trên web
    
    # Gọi application context để DB ghi nhận
    with app.app_context():
        new_log = VehicleLog(license_plate=plate_text, action=action, image_path=image_rel_path)
        db.session.add(new_log)
        
        # [Nâng cấp Doanh nghiệp]: Quản lý theo Phiên (Ticket) để tính cước
        if action == "IN":
            # Kiểm tra xem có đơn Đặt Chỗ (BOOKED) nào của xe này không
            booked_session = ParkingSession.query.filter_by(license_plate=plate_text, status="BOOKED").first()
            if booked_session:
                booked_session.status = "PARKING"
                booked_session.time_in = datetime.now()
                booked_session.image_in = image_rel_path
                print(f"[BOOKING_CLAIMED] Khách hàng {plate_text} đã đến nhận chỗ đúng hạn.")
            else:
                new_session = ParkingSession(
                    license_plate=plate_text,
                    status="PARKING",
                    image_in=image_rel_path
                )
                db.session.add(new_session)
                print(f"[SESSION_CREATED] Xe {plate_text} bấm vé VÀO bãi.")
            
        elif action == "OUT":
            session = ParkingSession.query.filter_by(license_plate=plate_text, status="PARKING").first()
            if session:
                session.status = "COMPLETED"
                session.time_out = datetime.now()
                session.image_out = image_rel_path
                
                # Logic Thu Phí
                if session.is_monthly:
                    session.fee = 0.0
                    print(f"[SESSION_VIP] Xe Tháng {plate_text} RA khỏi bãi. Miễn phí cước.")
                elif session.reserved_until:
                    # Vé Trả Trước theo Gói Giờ
                    if session.time_out > session.reserved_until:
                        overstay_delta = session.time_out - session.reserved_until
                        overstay_hours = overstay_delta.total_seconds() / 3600.0
                        extra_fee = round(overstay_hours * 10000.0)
                        session.fee = (session.fee or 0) + extra_fee
                        print(f"[SESSION_OVERSTAY] Xe Mua Gói {plate_text} lố hạn! Phạt +{extra_fee:,.0f} VND. Tổng thu: {session.fee:,.0f} VND")
                    else:
                        print(f"[SESSION_PREPAID_OUT] Xe Mua Gói {plate_text} RA ĐÚNG HẠN. Doanh thu: {session.fee:,.0f}đ. Mở Barrier.")
                else:
                    # Vé Lượt Vãng Lai
                    delta = session.time_out - session.time_in
                    hours = delta.total_seconds() / 3600.0
                    if hours < 1.0: 
                        hours = 1.0
                    session.fee = round(hours * 10000.0)
                    print(f"[SESSION_CLOSED] Xe {plate_text} thanh toán {session.fee:,.0f} VND. Mở Barrier.")
                
                # [NÂNG CẤP] Đẩy thông báo xe RA vào hàng đợi cho Dashboard
                delta_park = session.time_out - session.time_in if session.time_in else None
                if delta_park:
                    total_min = int(delta_park.total_seconds() / 60)
                    h, m = divmod(total_min, 60)
                    dur_str = f"{h}h {m}m" if h > 0 else f"{m} phút"
                else:
                    dur_str = "--"
                
                exit_alert_queue.append({
                    "plate": plate_text,
                    "fee": f"{int(session.fee):,} đ",
                    "time": session.time_out.strftime('%H:%M'),
                    "duration": dur_str,
                    "type": "VIP" if session.is_monthly else "Vé lượt",
                    "timestamp": now
                })
                print(f"[EXIT_ALERT] Đã thêm thông báo xe RA: {plate_text}")

        db.session.commit()
        print(f"[SQL_SAVED] Lịch sử LOG: BIỂN {plate_text} -> {action}")

def get_lpr_camera():
    global camera_lpr
    if camera_lpr is None:
        camera_lpr = VideoCamera(Config.VIDEO_CAM1)
    return camera_lpr

def generate_lpr_stream(app):
    """
    (GIẢI PHÁP THÔNG MINH)
    Worker này chỉ lấy frame mới nhất từ Camera luồng riêng,
    Xử lý nhận diện biển số, và yield thẳng dạng JPEG lên FrontEnd qua Flask.
    """
    cam = get_lpr_camera()
    
    while True:
        frame = cam.get_frame()
        if frame is None:
            continue
            
        # 1. Pipeline AI: Event-driven OCR state machine
        annotated_frame, plate_text, snapshot = process_lpr(frame)
        
        # 2. Xử lý ghi danh Database (chỉ gửi thư đi NẾU CÓ tín hiệu kích hoạt chụp)
        if plate_text is not None and snapshot is not None:
            handle_plate_db(app, plate_text, snapshot)
        
        # 3. Chuyển ảnh đã vẽ sang JPEG stream
        ret, jpeg = cv2.imencode('.jpg', annotated_frame)
        if not ret:
            continue
            
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
