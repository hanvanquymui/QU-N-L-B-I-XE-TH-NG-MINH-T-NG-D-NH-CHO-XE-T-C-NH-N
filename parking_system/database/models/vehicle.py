from datetime import datetime
from database.db_manager import db

class VehicleLog(db.Model):
    __tablename__ = 'vehicle_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    license_plate = db.Column(db.String(20), nullable=True) # Nhận diện từ Cam 1 (có thể null nếu không thấy)
    action = db.Column(db.String(10), nullable=False)       # Trạng thái: 'IN' hoặc 'OUT'
    timestamp = db.Column(db.DateTime, default=datetime.now)
    image_path = db.Column(db.String(255), nullable=True)   # Nơi lưu ảnh biển số crop ra (hoặc tĩnh)

    def __repr__(self):
        return f"<VehicleLog {self.license_plate} - {self.action}>"

class ParkingSession(db.Model):
    __tablename__ = 'parking_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    license_plate = db.Column(db.String(20), nullable=False)
    time_in = db.Column(db.DateTime, default=datetime.now)
    time_out = db.Column(db.DateTime, nullable=True)
    slot_id = db.Column(db.String(20), nullable=True) # Ví dụ: "O_1", "O_2"
    fee = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(15), default="PARKING") # BOOKED, PARKING, COMPLETED, CANCELLED
    is_monthly = db.Column(db.Boolean, default=False) # Gói Tháng/Cư dân
    customer_name = db.Column(db.String(100), nullable=True) # Họ và tên khách đặt chỗ
    customer_phone = db.Column(db.String(20), nullable=True) # SĐT liên hệ
    customer_cccd = db.Column(db.String(20), nullable=True) # Nhập CCCD không bắt buộc
    reserved_until = db.Column(db.DateTime, nullable=True) # Hạn huỷ đặt chỗ
    card_id = db.Column(db.String(10), nullable=True) # Thẻ nhựa (1-20)
    image_in = db.Column(db.String(255), nullable=True)
    image_out = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<ParkingSession {self.license_plate} - {self.status}>"
