import cv2
import threading
import time

class VideoCamera:
    """
    (GIẢI PHÁP THÔNG MINH)
    Đọc Camera trên luồng riêng biệt (Background Thread).
    Cách này giúp Flask server luôn nhận được frame MỚI NHẤT,
    Không bị giật lag do hàng đợi frame OpenCV bị dồn ứ khi có 2 camera.
    """
    def __init__(self, src):
        self.stream = cv2.VideoCapture(src)
        
        # [CẤU HÌNH PHẦN CỨNG]: Ép độ phân giải Full HD (Nếu camera hỗ trợ)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.stream.set(cv2.CAP_PROP_FPS, 60)
        
        # [CẤU HÌNH MÀN TRẬP]: Ép phơi sáng thấp (Shutter Speed nhanh) để chống nhòe
        self.stream.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25) # Tắt Auto Exposure
        self.stream.set(cv2.CAP_PROP_EXPOSURE, -5) # Tốc độ chụp siêu nhanh
        
        self.grabbed, self.frame = self.stream.read()
        self.stopped = False
        
        # Bắt đầu luồng đọc video
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        while not self.stopped:
            # Liên tục đọc khung hình
            self.grabbed, self.frame = self.stream.read()
            if not self.grabbed:
                # Chạy lại video từ đầu khi hết (phục vụ video giả lập)
                self.stream.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            # Nghỉ nhip nhỏ để tránh ngốn CPU
            time.sleep(0.01)

    def get_frame(self):
        if self.frame is not None:
            return self.frame.copy()
        return None

    def stop(self):
        self.stopped = True
        self.thread.join()
        if self.stream.isOpened():
            self.stream.release()
