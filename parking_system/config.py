import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-parking'
    
    # Hướng dẫn thông minh: Dùng os.path.join thay vì chuỗi có dấu '\' 
    # để tránh lỗi \v bị hiểu nhầm là ký tự Vertical Tab (gây lỗi 404 bạn vừa gặp)
    VIDEO_CAM1 = os.path.join(BASE_DIR, 'data', 'videos', '1.mp4')
    VIDEO_CAM2 = os.path.join(BASE_DIR, 'data', 'videos', 'baixe.mp4')
    MODEL_PATH = os.path.join(BASE_DIR, 'data', 'models', 'yolov8n.pt')
    
    # Cấu hình MySQL để kết nối với MySQL Workbench
    # Cú pháp: mysql+pymysql://<username>:<password>@<host>/<database_name>
    # Thay 'root', '123456', 'localhost', và 'parking_db' bằng thông tin thực tế của bạn
    # Lưu ý: Mật khẩu có chứa ký tự đặc biệt '@' nên cần được mã hóa thành '%40'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:Admin%40123@localhost/parking_db'
    
    # Cấu hình SQLite cũ (đã được comment lại để vô hiệu hóa)
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'database', 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False