from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)
    # Tự động tạo bảng nếu chưa có
    with app.app_context():
        import database.models.vehicle
        import database.models.user
        db.create_all()
        
        # Khởi tạo dữ liệu tài khoản mặc định (Seeding)
        from database.models.user import User
        if User.query.first() is None:
            # Nếu chưa có user nào, tạo luôn admin và bảo vệ
            admin_user = User(username='admin', role='admin', password_hash=generate_password_hash('123456'))
            guard_user = User(username='guard', role='guard', password_hash=generate_password_hash('123456'))
            db.session.add(admin_user)
            db.session.add(guard_user)
            db.session.commit()
            print("[AUTH] Đã tạo 2 tài khoản mặc định: admin/123456 (Quản lý) và guard/123456 (Bảo vệ)")
