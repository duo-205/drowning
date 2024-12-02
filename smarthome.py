import cv2
import serial
import numpy as np
from PIL import Image, ImageOps
from keras.models import load_model

# Load model và labels
class_names = open("labels.txt", "r").readlines()
model = load_model("keras_Model.h5", compile=False)

# Kết nối với ESP32 qua Serial
esp32 = serial.Serial(port="COM3", baudrate=115200, timeout=1)

# Open camera
camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

while True:
    ret, frame = camera.read()
    if not ret:
        break
    else:
        # Chuẩn bị dữ liệu đầu vào
        data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)

        # Đọc ảnh và xử lý
        image = frame.convert("RGB")
        image = ImageOps.fit(image, (224, 224), Image.Resampling.LANCZOS)
        image_array = np.asarray(image)
        normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1
        data[0] = normalized_image_array

        # Dự đoán
        prediction = model.predict(data)
        index = np.argmax(prediction)
        class_name = class_names[index]
        confidence_score = prediction[0][index]

        # Nếu kết quả đủ chính xác, gửi tín hiệu mở cửa
        if confidence_score > 0.8:  # Ngưỡng tự tin, điều chỉnh nếu cần
            print("Mở cửa!")
            esp32.write(b"o\n")  # Gửi tín hiệu mở cửa qua Serial
        else:
            print("Không nhận diện được khuôn mặt đủ chính xác.")

        cv2.imshow("Diem danh", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cv2.destroyAllWindows()
camera.release()
