import cv2
import numpy as np

# Bứt phá khỏi giới hạn của YOLO vì YOLO gốc ở ngoài đời được "nhồi sọ" hình dạng đường phố và xe thật. 
# Nó hiểu nhầm tờ giấy trắng khổng lồ của bạn là 1 chiếc xe (Bạn có thấy khung xanh lớn không?)
# (GIẢI PHÁP SIÊU THÔNG MINH): Phân tích Độ Lệch Chuẩn Chi Tiết (Standard Deviation Vision).

SLOTS = {}
slots_initialized = False

def init_slots(frame_width, frame_height):
    global SLOTS, slots_initialized
    SLOTS.clear()
    
    # Ở ĐÂY TÔI CHỈNH SỬA TỌA ĐỘ THEO YÊU CẦU CỦA BẠN NHÉ!
    # Chỉnh nhẹ lề (Nới đỉnh lên 1 tí, đẩy lề trong ra 1 tí cho chuẩn xác và đều nhau 100%)
    col1_x1, col1_x2 = int(frame_width * 0.03), int(frame_width * 0.23)
    col2_x1, col2_x2 = int(frame_width * 0.25), int(frame_width * 0.45) # Đẩy sang phải
    
    col3_x1, col3_x2 = int(frame_width * 0.56), int(frame_width * 0.76) # Đẩy sang trái
    col4_x1, col4_x2 = int(frame_width * 0.78), int(frame_width * 0.98)
    
    # (GIẢI PHÁP THÔNG MINH) Do tờ giấy đặt hơi nghiêng (phối cảnh), 
    # cột bên TRÁI bị ngắn lại so với cột bên PHẢI trên màn hình camera.
    # Ta sẽ định nghĩa chiều cao Y riêng cho Trái và Phải!
    
    # 1. NHÓM 2 CỘT BÊN TRÁI (Bị nén lại)
    left_start_y = int(frame_height * 0.12)
    left_end_y = int(frame_height * 0.63) # Đẩy toàn bộ O_17, O_13, O_9, O_5 dồn lên trên O_1!
    left_row_h = (left_end_y - left_start_y) / 5
    
    # 2. NHÓM 2 CỘT BÊN PHẢI (Dồn lên như bên trái theo yêu cầu của bạn)
    right_start_y = int(frame_height * 0.12)
    right_end_y = int(frame_height * 0.63) # Đã kéo rụt lại giống bên trái (0.65)
    right_row_h = (right_end_y - right_start_y) / 5
    
    slot_id = 1
    for row in range(5):
        # Tọa độ Y riêng cho cột TRÁI
        l_y1 = int(left_start_y + row * left_row_h)
        l_y2 = int(l_y1 + left_row_h * 0.95)
        
        # Tọa độ Y riêng cho cột PHẢI
        r_y1 = int(right_start_y + row * right_row_h)
        r_y2 = int(r_y1 + right_row_h * 0.95)
        
        # Ghép 4 ô lại (ĐỔI MÀU: color_empty = Đỏ (0,0,255), color_occ = Xanh (0,255,0))
        SLOTS[f"O_{slot_id}"]   = {"box": [col1_x1, l_y1, col1_x2, l_y2], "color_empty": (0, 0, 255), "color_occ": (0, 255, 0)}
        SLOTS[f"O_{slot_id+1}"] = {"box": [col2_x1, l_y1, col2_x2, l_y2], "color_empty": (0, 0, 255), "color_occ": (0, 255, 0)}
        SLOTS[f"O_{slot_id+2}"] = {"box": [col3_x1, r_y1, col3_x2, r_y2], "color_empty": (0, 0, 255), "color_occ": (0, 255, 0)}
        SLOTS[f"O_{slot_id+3}"] = {"box": [col4_x1, r_y1, col4_x2, r_y2], "color_empty": (0, 0, 255), "color_occ": (0, 255, 0)}
        slot_id += 4
        
    slots_initialized = True

def process_occupancy(frame):
    global SLOTS, slots_initialized
    if frame is None:
        return None, {}
        
    annotated_frame = frame.copy()
    
    if not slots_initialized:
        h, w = frame.shape[:2]
        init_slots(w, h)
            
    status = {}
    # Chuyển đổi khung hình sang dạng ảnh Xám (Trắng Đen) để phân tích chi tiết độ phức tạp
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    for slot_name, slot_info in SLOTS.items():
        box = slot_info["box"]
        # Cắt đúng mảnh nhỏ hình chữ nhật chứa ô đỗ xe đó (Region of Interest)
        roi = gray_frame[box[1]:box[3], box[0]:box[2]]
        
        # Công nghệ Thị Giác Máy Tính Tốc độ ánh sáng thay YOLO (StdDev Analysis).
        # Tờ giấy trắng bóc: < 10. Chữ bút bi viết tay to (như số 12): ~ 21. 
        # Xe ô tô đồ chơi: > 33. -> Đặt mốc 25 là hoàn hảo nhất!
        complexity = np.std(roi)
        
        is_occupied = complexity > 25.0
            
        color = slot_info["color_occ"] if is_occupied else slot_info["color_empty"]
        status[slot_name] = "OCCUPIED" if is_occupied else "EMPTY"
        
        cv2.rectangle(annotated_frame, (box[0], box[1]), (box[2], box[3]), color, 2)
        cv2.putText(annotated_frame, f"{slot_name}", (box[0] + 5, box[1] + 15), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Vẽ thêm điểm Chi Tiết ở góc lồng kính để bạn theo dõi AI cảm nhận chiếc xe
        cv2.putText(annotated_frame, f"{int(complexity)}", (box[2] - 25, box[1] + 15), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)
                    
    # Hiển thị bộ đếm chỗ trống lên góc phải trên cùng
    empty_slots = sum(1 for v in status.values() if v == "EMPTY")
    occ_slots = len(SLOTS) - empty_slots
    cv2.putText(annotated_frame, f"TRONG: {empty_slots}/20", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.putText(annotated_frame, f"DAY: {occ_slots}/20", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
    return annotated_frame, status
