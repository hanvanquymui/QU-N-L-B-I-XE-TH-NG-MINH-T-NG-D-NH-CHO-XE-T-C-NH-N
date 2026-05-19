from flask import Flask, render_template, Response, current_app, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from database.db_manager import init_db, db
from database.models.vehicle import VehicleLog
from core.worker_lpr import generate_lpr_stream, plate_cache, exit_alert_queue
from core.worker_occupancy import generate_occupancy_stream, live_slot_status

app = Flask(__name__)
app.config.from_object(Config)

# Cấu hình LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    from database.models.user import User
    return User.query.get(int(user_id))

# Khởi tạo Database nếu chưa có
init_db(app)

@app.route('/login', methods=['GET', 'POST'])
def login():
    from database.models.user import User
    from werkzeug.security import check_password_hash
    
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            # flash error cho frontend
            pass
            
    # Bổ sung flash variable passing nếu không dùng Flask message flash default HTML (hoặc dùng JS alert)
    return render_template('login.html', error=request.method == 'POST')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    # Khi thêm giao diện Tailwind, ta sẽ trả về index.html
    return render_template('index.html')

@app.route('/analytics')
@login_required
def analytics():
    # RBAC: Chỉ admin mới được vào trang này
    if current_user.role != 'admin':
        return "Lỗi 403 Forbidden! Giao diện Báo Cáo Doanh Thu chỉ dành riêng cho cấp bậc Quản Trị Viên (Admin). Bảo vệ không có quyền xem thông tin này.", 403
    return render_template('analytics.html')

@app.route('/api/analytics/dashboard_data')
@login_required
def analytics_dashboard_data():
    if current_user.role != 'admin':
        from flask import jsonify
        return jsonify({"error": "Unauthorized"}), 403
        
    from database.models.vehicle import ParkingSession
    from sqlalchemy import func
    from datetime import datetime, timedelta
    from flask import jsonify
    
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Default: 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    if start_date_str:
        try: start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except: pass
    if end_date_str:
        try: end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        except: pass
        
    # Build Query Base
    base_query = ParkingSession.query.filter(
        ParkingSession.time_in >= start_date,
        ParkingSession.time_in <= end_date
    )
    
    # KPIs
    total_visits = base_query.count()
    parking_now_query = base_query.filter(ParkingSession.status == "PARKING")
    total_parking = parking_now_query.count()
    vip_parking = parking_now_query.filter(ParkingSession.is_monthly == True).count()
    
    total_revenue_val = db.session.query(func.sum(ParkingSession.fee)).filter(
        ParkingSession.time_in >= start_date,
        ParkingSession.time_in <= end_date,
        ParkingSession.status.in_(["COMPLETED", "BOOKED", "PARKING"])
    ).scalar() or 0.0
    
    completed_sessions = base_query.filter(ParkingSession.status == "COMPLETED").all()
    avg_minutes = 0
    if len(completed_sessions) > 0:
        total_seconds = sum(min(max((s.time_out - s.time_in).total_seconds(), 0), 86400*30) for s in completed_sessions if s.time_out)
        avg_minutes = int(total_seconds / len(completed_sessions) / 60)
        
    avg_str = f"{avg_minutes // 60}h {avg_minutes % 60}m" if avg_minutes > 60 else f"{avg_minutes} phút"
    
    paid_count = base_query.filter(ParkingSession.fee > 0).count()
    
    # Charts Data
    # 1. Hourly Chart (Lưu lượng 24h)
    hourly_counts = {f"{i:02d}:00": 0 for i in range(24)}
    sessions_in_range = base_query.all()
    for s in sessions_in_range:
        if s.time_in:
            hr = s.time_in.strftime('%H:00')
            if hr in hourly_counts:
                hourly_counts[hr] += 1
            
    # 2. Ticket Type (Vé Tháng vs Vé Lượt)
    is_monthly_count = sum(1 for s in sessions_in_range if s.is_monthly)
    normal_count = total_visits - is_monthly_count
    
    # 3. 7 Day Trends
    trend_labels = []
    trend_data = []
    for i in range(6, -1, -1):
        d = end_date - timedelta(days=i)
        trend_labels.append(d.strftime('%d/%m'))
        d_start = d.replace(hour=0, minute=0, second=0)
        d_end = d.replace(hour=23, minute=59, second=59)
        cnt = ParkingSession.query.filter(
            ParkingSession.time_in >= d_start,
            ParkingSession.time_in <= d_end
        ).count()
        trend_data.append(cnt)
        
    # Tables - Recent
    recent = []
    for s in base_query.order_by(ParkingSession.time_in.desc()).limit(15).all():
        recent.append({
            "license_plate": s.license_plate,
            "owner": s.customer_name or "Khách vãng lai",
            "type": "Vé Tháng (VIP)" if s.is_monthly else "Vé Lượt",
            "time_in": s.time_in.strftime('%H:%M %d/%m') if s.time_in else "",
            "time_out": s.time_out.strftime('%H:%M %d/%m') if s.time_out else "--",
            "status": s.status
        })
        
    # Tables - Top duration 
    top_sessions = sorted([s for s in completed_sessions if s.time_out], 
                          key=lambda x: (x.time_out - x.time_in).total_seconds(), reverse=True)[:10]
    top_longest = []
    for i, s in enumerate(top_sessions):
        delta = s.time_out - s.time_in
        days, remainder = divmod(delta.total_seconds(), 86400)
        hours, remainder = divmod(remainder, 3600)
        dur_str = f"{int(days)}d {int(hours)}h" if days > 0 else f"{int(hours)}h {int(remainder//60)}m"
        top_longest.append({
            "rank": i+1,
            "license_plate": s.license_plate,
            "owner": s.customer_name or "Khách",
            "duration": dur_str,
            "fee": f"{int(s.fee):,} đ"
        })
        
    return jsonify({
        "kpi": {
            "total_visits": f"{total_visits:,}",
            "total_parking": f"{total_parking:,}",
            "vip_parking": f"{vip_parking:,}",
            "total_revenue": f"{int(total_revenue_val):,} đ",
            "paid_count": f"{paid_count:,}",
            "avg_time": avg_str
        },
        "charts": {
            "hourly": {
                "labels": list(hourly_counts.keys()),
                "data": list(hourly_counts.values())
            },
            "ticket_type": {
                "labels": ["Vé Tháng (VIP)", "Vé Lượt"],
                "data": [is_monthly_count, normal_count]
            },
            "trend": {
                "labels": trend_labels,
                "data": trend_data
            }
        },
        "tables": {
            "recent": recent,
            "longest": top_longest
        }
    })

@app.route('/api/analytics/export')
@login_required
def analytics_export():
    if current_user.role != 'admin':
        return "Unauthorized", 403
        
    from database.models.vehicle import ParkingSession
    from datetime import datetime, timedelta
    import csv
    from io import StringIO
    from flask import Response
    
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    if start_date_str:
        try: start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except: pass
    if end_date_str:
        try: end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        except: pass
        
    query = ParkingSession.query.filter(
        ParkingSession.time_in >= start_date,
        ParkingSession.time_in <= end_date
    ).order_by(ParkingSession.time_in.asc()).all()
    
    def generate():
        si = StringIO()
        # Excel needs UTF-8 BOM to recognize utf-8 csv
        si.write('\ufeff')
        cw = csv.writer(si)
        cw.writerow(['ID_He_Thong', 'Bien_So_Xe', 'Thoi_Gian_Vao', 'Thoi_Gian_Ra', 'Loai_Ve', 'Chu_Xe', 'SDT_Lien_He', 'So_CCCD', 'Trang_Thai', 'Doanh_Thu_VND'])
        
        for s in query:
            cw.writerow([
                s.id,
                s.license_plate,
                s.time_in.strftime('%H:%M:%S %d/%m/%Y') if s.time_in else '',
                s.time_out.strftime('%H:%M:%S %d/%m/%Y') if s.time_out else '',
                "Ve Thang (VIP)" if s.is_monthly else "Ve Luot",
                s.customer_name or "",
                s.customer_phone or "",
                s.customer_cccd or "",
                s.status,
                int(s.fee)
            ])
            yield si.getvalue()
            si.seek(0)
            si.truncate(0)
            
    header = {
        'Content-Disposition': f'attachment; filename=bao_cao_do_xe_{start_date.strftime("%Y%m%d")}_to_{end_date.strftime("%Y%m%d")}.csv',
        'Content-Type': 'text/csv; charset=utf-8'
    }
    return Response(generate(), headers=header)

@app.route('/history')
@login_required
def history():
    from database.models.vehicle import ParkingSession
    # Truy xuất Quản Lý Phiếu Đỗ Xe (Thay vì log thô)
    sessions = ParkingSession.query.order_by(ParkingSession.time_in.desc()).all()
    return render_template('history.html', sessions=sessions)

# (LỚP NÂNG CẤP) Dummy routes để chuẩn bị cho Stream Camera
@app.route('/video_feed/cam1')
def video_feed_cam1():
    # Khéo léo truyền App Context vào luồng ngầm (Background Generator Thread)
    # nhờ vậy AI mới có "Quyền truy cập" Database
    app_instance = current_app._get_current_object()
    
    # Stream Cam 1 hiển thị phân tích biển số
    return Response(generate_lpr_stream(app_instance),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed/cam2')
def video_feed_cam2():
    app_instance = current_app._get_current_object()
    # Stream Cam 2 hiển thị phân tích chỗ trống đỗ xe
    return Response(generate_occupancy_stream(app_instance),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/manual')
@login_required
def manual_entry():
    return render_template('manual_entry.html')

@app.route('/api/manual_in_out', methods=['POST'])
@login_required
def manual_in_out():
    from database.models.vehicle import ParkingSession
    from datetime import datetime
    
    plate_text = request.form.get('license_plate', '').strip()
    is_monthly = request.form.get('is_monthly') == 'on'
    
    if not plate_text:
        return redirect(url_for('manual_entry'))
        
    session = ParkingSession.query.filter_by(license_plate=plate_text, status="PARKING").first()
    if session:
        # Kịch bản RA
        session.status = "COMPLETED"
        session.time_out = datetime.now()
        
        if session.is_monthly:
            session.fee = 0.0
        elif session.reserved_until:
            # Vé đặt trước / trả trước theo gói
            if session.time_out > session.reserved_until:
                overstay_delta = session.time_out - session.reserved_until
                overstay_hours = overstay_delta.total_seconds() / 3600.0
                extra_fee = round(overstay_hours * 10000.0)
                session.fee = (session.fee or 0) + extra_fee
                flash(f"Phụ thu lố hạn giờ quy định: +{extra_fee:,.0f}đ", "warning")
        else:
            # Vé lượt đi vào ngẫu nhiên
            delta = session.time_out - session.time_in
            hours = delta.total_seconds() / 3600.0
            if hours < 1.0: hours = 1.0
            session.fee = round(hours * 10000.0)
            
        flash(f"Thanh toán hoàn tất xe {plate_text}. Đang xuất vé...", "success")
    else:
        # Kịch bản VÀO
        new_session = ParkingSession(
            license_plate=plate_text,
            status="PARKING",
            is_monthly=is_monthly,
            image_in="uploads/manual.jpg"
        )
        db.session.add(new_session)
        flash(f"Đã mở barrier cho xe {plate_text} VÀO bãi.", "success")
    
    db.session.commit()
    return redirect(url_for('manual_entry'))

@app.route('/api/analyze_image', methods=['POST'])
@login_required
def analyze_image():
    from flask import jsonify
    import cv2
    import numpy as np
    import base64
    from core.ocr import process_lpr
    
    if 'image' not in request.files:
        return jsonify({'error': 'Không tìm thấy ảnh'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Chưa chọn file'}), 400
        
    try:
        in_memory_file = file.read()
        nparr = np.frombuffer(in_memory_file, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({'error': 'File ảnh không hợp lệ'}), 400
            
        annotated_frame, plate_text, _ = process_lpr(img)
        
        if not plate_text:
            return jsonify({'error': 'AI không tìm thấy biển số nào hợp lệ trong ảnh'}), 404
            
        _, buffer = cv2.imencode('.jpg', annotated_frame)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'success': True,
            'plate_text': plate_text,
            'image_base64': f"data:image/jpeg;base64,{img_base64}"
        })
    except Exception as e:
        return jsonify({'error': f'Lỗi phân tích: {str(e)}'}), 500


@app.route('/api/book_slot', methods=['POST'])
def book_slot():
    from database.models.vehicle import ParkingSession
    from datetime import datetime, timedelta
    
    plate_text = request.form.get('license_plate', '').strip()
    customer_name = request.form.get('customer_name', '').strip()
    customer_phone = request.form.get('customer_phone', '').strip()
    customer_cccd = request.form.get('customer_cccd', '').strip()
    
    try:
        duration_hours = int(request.form.get('duration_hours', 2))
        pre_fee = float(request.form.get('pre_fee', 20000))
    except ValueError:
        duration_hours = 2
        pre_fee = 20000.0

    if not plate_text: return redirect(url_for('manual_entry'))
    
    if ParkingSession.query.filter_by(license_plate=plate_text, status="PARKING").first():
        flash("Xe này đang đỗ trong bãi, không thể mua vé đặt trước!", "error")
        return redirect(url_for('manual_entry'))
        
    reserved_time = datetime.now() + timedelta(hours=duration_hours)
    new_session = ParkingSession(
        license_plate=plate_text,
        status="BOOKED",
        reserved_until=reserved_time,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_cccd=customer_cccd,
        fee=pre_fee
    )
    db.session.add(new_session)
    db.session.commit()
    
    flash(f"Đã xuất hóa đơn đỗ xe {pre_fee:,.0f}đ (Gói {duration_hours} giờ) cho hạng xe {plate_text}. Hạn chót lấy xe: {reserved_time.strftime('%H:%M %d/%m/%Y')}.", "success")
    return redirect(url_for('manual_entry'))

@app.route('/api/edit_plate', methods=['POST'])
@login_required
def edit_plate():
    from database.models.vehicle import ParkingSession
    session_id = request.form.get('session_id')
    new_plate = request.form.get('new_plate', '').strip()
    
    session = ParkingSession.query.get(session_id)
    if session and new_plate:
        old_plate = session.license_plate
        session.license_plate = new_plate
        db.session.commit()
        flash(f"Đã cập nhật lỗi BIỂN do AI: Giác quan AI ({old_plate}) -> Nhân sự chỉnh sửa ({new_plate})", "success")
    return redirect(url_for('history'))

@app.route('/vehicles')
@login_required
def vehicles_page():
    return render_template('vehicles.html')

@app.route('/api/search_vehicles')
@login_required
def search_vehicles():
    from flask import jsonify
    from database.models.vehicle import ParkingSession
    from datetime import datetime
    
    plate_query = request.args.get('q', '').strip()
    parking_only = request.args.get('parking_only') == 'true'
    today_only = request.args.get('today_only') == 'true'
    vip_only = request.args.get('vip_only') == 'true'
    
    if not plate_query:
        return jsonify([])
        
    query = ParkingSession.query.filter(
        ParkingSession.license_plate.ilike(f"%{plate_query}%")
    )
    
    if parking_only:
        query = query.filter(ParkingSession.status == "PARKING")
        
    if today_only:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(ParkingSession.time_in >= today_start)
        
    if vip_only:
        query = query.filter(ParkingSession.is_monthly == True)
        
    results = query.order_by(ParkingSession.time_in.desc()).limit(20).all()
    
    data = []
    from flask import url_for
    for s in results:
        data.append({
            'license_plate': s.license_plate,
            'image_in': url_for('static', filename=s.image_in) if s.image_in else None,
            'card_id': s.card_id or 'Chưa cấp thẻ',
            'time_in': s.time_in.strftime('%H:%M %d/%m/%Y') if s.time_in else '',
            'status': s.status,
            'is_monthly': s.is_monthly
        })
    return jsonify(data)

@app.route('/api/assign_card', methods=['POST'])
@login_required
def assign_card():
    from flask import jsonify
    from database.models.vehicle import ParkingSession
    session_id = request.form.get('session_id')
    card_id = request.form.get('card_id')
    
    session = ParkingSession.query.get(session_id)
    if session:
        session.card_id = card_id if card_id and card_id != "" else None
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False}), 404

@app.route('/api/live_status')
@login_required
def live_status():
    """[NÂNG CẤP] API real-time cho Live Map Dashboard - Frontend poll mỗi 3 giây"""
    from flask import jsonify
    from database.models.vehicle import ParkingSession, VehicleLog
    from datetime import datetime
    import time as _time
    
    # 1. Slot status từ worker_occupancy (biến global)
    slots_data = live_slot_status.copy()
    
    # 2. Biển số mới nhất từ plate_cache
    latest_plate = "--"
    latest_plate_time = ""
    if plate_cache:
        latest_entry = max(plate_cache.items(), key=lambda x: x[1])
        latest_plate = latest_entry[0]
        from datetime import datetime as dt
        latest_plate_time = dt.fromtimestamp(latest_entry[1]).strftime('%H:%M')
    
    # 3. Thống kê hôm nay từ Database
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    today_sessions = ParkingSession.query.filter(
        ParkingSession.time_in >= today_start
    ).all()
    
    today_in = len(today_sessions)
    today_out = sum(1 for s in today_sessions if s.status == "COMPLETED")
    today_revenue = sum(s.fee for s in today_sessions if s.fee and s.status in ["COMPLETED", "PARKING", "BOOKED"])
    
    # 4. Xe đang trong bãi (Active Sessions)
    active_sessions_raw = ParkingSession.query.filter_by(status="PARKING").order_by(ParkingSession.time_in.desc()).limit(10).all()
    
    active_sessions = []
    now = datetime.now()
    for s in active_sessions_raw:
        if s.time_in:
            delta = now - s.time_in
            total_min = int(delta.total_seconds() / 60)
            hours, mins = divmod(total_min, 60)
            duration_str = f"{hours}h {mins}m" if hours > 0 else f"{mins} phút"
        else:
            duration_str = "--"
        
        active_sessions.append({
            "id": s.id,
            "plate": s.license_plate,
            "slot": s.slot_id or "--",
            "time_in": s.time_in.strftime('%H:%M') if s.time_in else "--",
            "type": "VIP" if s.is_monthly else ("Đặt trước" if s.reserved_until else "Vé lượt"),
            "duration": duration_str,
            "customer": s.customer_name or "Khách vãng lai"
        })
    
    # 5. Tổng xe đang trong bãi
    total_parking = ParkingSession.query.filter_by(status="PARKING").count()
    
    # 6. [NÂNG CẤP] Lịch sử VÀO/RA gần nhất từ VehicleLog (real event log)
    recent_logs = VehicleLog.query.filter(
        VehicleLog.timestamp >= today_start
    ).order_by(VehicleLog.timestamp.desc()).limit(12).all()
    
    recent_events = []
    for log in recent_logs:
        recent_events.append({
            "plate": log.license_plate,
            "action": log.action,  # "IN" hoặc "OUT"
            "time": log.timestamp.strftime('%H:%M') if log.timestamp else "--",
            "image": log.image_path
        })
    
    # 7. [NÂNG CẤP] Thông báo xe RA (exit alerts) - chỉ lấy alerts trong 30 giây gần nhất
    current_time = _time.time()
    exit_alerts = []
    for alert in list(exit_alert_queue):
        if current_time - alert["timestamp"] < 30:  # Chỉ hiện trong 30 giây
            exit_alerts.append({
                "plate": alert["plate"],
                "fee": alert["fee"],
                "time": alert["time"],
                "duration": alert["duration"],
                "type": alert["type"]
            })
    
    return jsonify({
        "slots": slots_data["slots"],
        "total_slots": slots_data["total"],
        "available": slots_data["available"],
        "occupied": slots_data["occupied"],
        "occupancy_percent": round(slots_data["occupied"] / max(slots_data["total"], 1) * 100),
        "latest_plate": latest_plate,
        "latest_plate_time": latest_plate_time,
        "today_in": today_in,
        "today_out": today_out,
        "today_revenue": int(today_revenue),
        "total_parking": total_parking,
        "active_sessions": active_sessions,
        "recent_events": recent_events,
        "exit_alerts": exit_alerts
    })

@app.before_request
def auto_cancel_bookings():
    from database.models.vehicle import ParkingSession
    from datetime import datetime
    
    expired_bookings = ParkingSession.query.filter(
        ParkingSession.status == "BOOKED",
        ParkingSession.reserved_until < datetime.now()
    ).all()
    
    for b in expired_bookings:
        b.status = "CANCELLED"
    if expired_bookings:
        db.session.commit()

if __name__ == '__main__':
    # Hướng dẫn thông minh: Bật threaded=True giúp Flask không bị đứng 
    # khi có cả hai video stream cùng chạy
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
