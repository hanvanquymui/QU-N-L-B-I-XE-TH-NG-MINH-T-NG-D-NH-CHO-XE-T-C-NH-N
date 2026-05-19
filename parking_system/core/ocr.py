import cv2
import easyocr
import time
import numpy as np

print("[INFO] Khởi tạo AI Phân tích Biển Số (Cơ chế Virtual Tripwire)...")
reader = easyocr.Reader(['en'], gpu=False)

lpr_state = "WAITING"
detect_start_time = 0
last_best_text = None
last_bboxes = []
last_snapshot = None

def get_tripwire_box(w, h):
    # Khung ranh giới vô hình đã được điều chỉnh xuống thấp hơn (y=70% -> 90%) 
    # để nằm dưới vạch kẻ thẳng và bắt trúng khu vực biển số.
    return [int(w * 0.25), int(h * 0.50), int(w * 0.80), int(h * 0.80)]

def run_easyocr(frame):
    # Không dùng resize (fx=0.5) nữa vì ảnh camera cho xe mô hình khá nhỏ, 
    # nén lại sẽ làm mất nét của các chữ số nhỏ xíu trên biển.
    results = reader.readtext(frame)
    detected_parts = []
    
    for (bbox, text, prob) in results:
        # Hạ độ chính xác tối thiểu một chút vì ảnh dễ bị lóa
        if prob < 0.15 or len(text) < 2: continue
        (tl, tr, br, bl) = bbox
        tl = (int(tl[0]), int(tl[1]))
        br = (int(br[0]), int(br[1]))
        center_y = (tl[1] + br[1]) / 2
        
        # Chỉ giữ lại chữ cái và số
        cleaned_text = "".join(e for e in text if e.isalnum())
        if len(cleaned_text) < 2: continue
        
        detected_parts.append({
            "text": cleaned_text.upper(),
            "y": center_y,
            "tl": tl,
            "br": br
        })
        
    if detected_parts:
        detected_parts.sort(key=lambda item: item["y"])
        
        # BỘ LỌC THÔNG MINH: Chỉ lấy những kết quả CÓ CHỨA CHỮ SỐ
        # Giúp loại trừ nhầm lẫn với các tem nhãn chữ dán trên xe (ví dụ chữ "RACING", "SPEED")
        plate_parts = [item for item in detected_parts if any(char.isdigit() for char in item["text"])]
        
        if len(plate_parts) > 0:
            best_text = "-".join([item["text"] for item in plate_parts])
            current_bboxes = [(item["tl"], item["br"], item["text"]) for item in plate_parts]
        else:
            best_text = "-".join([item["text"] for item in detected_parts])
            current_bboxes = [(item["tl"], item["br"], item["text"]) for item in detected_parts]
            
        return best_text, current_bboxes
        
    return None, []

def process_lpr(frame):
    global lpr_state, detect_start_time, last_best_text, last_bboxes, last_snapshot
    
    if frame is None:
        return None, None, None
        
    h, w = frame.shape[:2]
    annotated_frame = frame.copy()
    box = get_tripwire_box(w, h)
    
    # 1. Thuật toán giám sát lấn vạch 0% CPU (Tương tự Camera 2)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    roi = gray[box[1]:box[3], box[0]:box[2]]
    
    # Đo độ phức tạp pixel
    complexity = np.std(roi)
    car_present = complexity > 20.0 
    
    is_trigger_event = False
    
    # 2. CỖ MÁY TRẠNG THÁI (STATE MACHINE)
    if lpr_state == "WAITING":
        if car_present:
            lpr_state = "STABILIZING"
            detect_start_time = time.time()
            
    elif lpr_state == "STABILIZING":
        elapsed = time.time() - detect_start_time
        
        # XE ĐỘNG: Không bắt xe ở lại vạch.
        # Chụp siêu tốc sau 0.1 giây vì shutter speed đã nhanh
        if elapsed > 0.10 or not car_present:
            last_snapshot = frame.copy()
            
            # [TỐI ƯU SIÊU TỐC] Cắt (Crop) chính xác vùng chứa biển số trước khi chạy AI
            roi_x1, roi_y1, roi_x2, roi_y2 = box
            
            # Mở rộng vùng crop thêm 20px mỗi bên cho an toàn
            roi_x1 = max(0, roi_x1 - 20)
            roi_y1 = max(0, roi_y1 - 20)
            roi_x2 = min(w, roi_x2 + 20)
            roi_y2 = min(h, roi_y2 + 20)
            
            plate_crop = last_snapshot[roi_y1:roi_y2, roi_x1:roi_x2]
            
            # [LÀM RÕ SỐ] Sử dụng Kernel Sharpening để chống nhòe
            kernel = np.array([[0, -1, 0],
                               [-1, 5,-1],
                               [0, -1, 0]])
            sharpened_crop = cv2.filter2D(plate_crop, -1, kernel)
            
            # Nhận diện trên ảnh đã cắt, tốc độ tăng gấp 10 lần
            best_text, local_bboxes = run_easyocr(sharpened_crop)
            
            # Dịch chuyển tọa độ bounding boxes về lại khung hình lớn
            current_bboxes = []
            for (tl, br, txt) in local_bboxes:
                global_tl = (tl[0] + roi_x1, tl[1] + roi_y1)
                global_br = (br[0] + roi_x1, br[1] + roi_y1)
                current_bboxes.append((global_tl, global_br, txt))
            
            last_best_text = best_text
            last_bboxes = current_bboxes
            lpr_state = "COOLDOWN"
            is_trigger_event = True  # Phát tín hiệu báo Worker lưu DB
                
    elif lpr_state == "COOLDOWN":
        # Giảm thời gian Reset (Timeout) xuống 1.5 giây để sẵn sàng cho xe tiếp theo liên tục
        elapsed = time.time() - detect_start_time
        if not car_present or elapsed > 1.5:
            lpr_state = "WAITING"
            last_best_text = None
            last_bboxes = []
    
    # 3. GIAO DIỆN (UI VẼ TRỰC TIẾP TRÊN CAM Y CHANG ROBOT COP)
    if lpr_state == "WAITING":
        color = (0, 255, 0)
        cv2.putText(annotated_frame, "READY: WAITING FOR VEHICLE", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    elif lpr_state == "STABILIZING":
        color = (0, 255, 255)
        cv2.putText(annotated_frame, "CAR DETECTED: CAPTURING...", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    else:
        color = (0, 0, 255)
        # Hệ thống đang khóa cứng đóng băng màn hình hiển thị kết quả
        text_display = last_best_text if last_best_text else "NO PLATE FOUND"
        cv2.putText(annotated_frame, f"DB SAVED: {text_display}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        cv2.putText(annotated_frame, "ZONE BLOCKED: PLEASE MOVE CAR", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Vẽ Lại bounding box của quá khứ đè lên khung hình hiện tại đang đông đá
        for (tl, br, text) in last_bboxes:
            cv2.rectangle(annotated_frame, tl, br, (0, 255, 0), 2)
            cv2.putText(annotated_frame, text, (tl[0], max(0, tl[1] - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Vẽ Khung Tripwire Laser ngắm sẵn ở giữa màn
    cv2.rectangle(annotated_frame, (box[0], box[1]), (box[2], box[3]), color, 2)
    cv2.putText(annotated_frame, f"TRIPWIRE (STD: {int(complexity)})", (box[0], box[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    # Nếu Trigger = True, Worker sẽ biết và ném hình ảnh vào CSDL Database
    if is_trigger_event:
        return annotated_frame, last_best_text, last_snapshot
    else:
        return annotated_frame, None, None
