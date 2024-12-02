import sys
import serial
import time
import json
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal, Qt


class SerialReader(QThread):
    data_received = pyqtSignal(str)

    def __init__(self, port, baudrate=115200):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.running = True

    def run(self):
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Đã kết nối với {self.port} ở baudrate {self.baudrate}")
            while self.running:
                if self.serial_conn.in_waiting > 0:
                    data = self.serial_conn.readline()
                    data_str = self.process_data(data)
                    self.data_received.emit(data_str)
                time.sleep(0.1)
        except serial.SerialException as e:
            print(f"Không thể kết nối với cổng {self.port}: {e}")
            QMessageBox.critical(None, "Serial Error", f"Không thể kết nối với cổng {self.port}: {e}")
        except Exception as e:
            print(f"Lỗi khi đọc từ Serial: {e}")

    def process_data(self, data):
        try:
            decoded_data = data.decode('utf-8', errors='ignore').strip()
            return decoded_data
        except UnicodeDecodeError:
            print(f"Không thể giải mã dữ liệu: {data}")
            return str(data)

    def close(self):
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()


class PortInputWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chọn Cổng Serial")
        self.setGeometry(200, 200, 400, 120)
        self.setWindowIcon(QIcon("CanhBaoDuoiNuoc.png"))

        self.layout = QVBoxLayout()
        self.label = QLabel("Nhập cổng Serial (ví dụ: COM4):")
        self.label.setStyleSheet("font-size: 18px; color: #333;")
        self.layout.addWidget(self.label)

        self.port_input = QLineEdit()
        self.port_input.setStyleSheet("padding: 10px; font-size: 16px; border: 1px solid #aaa;")
        self.layout.addWidget(self.port_input)

        self.connect_button = QPushButton("Kết Nối")
        self.connect_button.setStyleSheet("background-color: #28a745; color: white; font-size: 18px; padding: 12px;")
        self.connect_button.clicked.connect(self.on_connect)
        self.layout.addWidget(self.connect_button)

        self.setLayout(self.layout)

    def on_connect(self):
        port = self.port_input.text().strip()
        if port:
            self.monitor = WristbandMonitor(port)
            self.monitor.show()
            self.close()
        else:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập một cổng Serial hợp lệ")


class WristbandMonitor(QWidget):
    def __init__(self, serial_port):
        super().__init__()

        self.setWindowTitle("Hệ Thống Cảnh Báo Đuối Nước")
        self.setGeometry(100, 100, 800, 500)
        self.setWindowIcon(QIcon("CanhBaoDuoiNuoc.png"))

        self.layout = QVBoxLayout()

        # Labels for data fields with blue background
        self.label = QLabel("Chưa có dữ liệu")
        self.label.setAlignment(Qt.AlignLeft)
        self.label.setStyleSheet("font-size: 26px; color: #333; padding: 20px; background-color: #ADD8E6; border-radius: 15px;")
        self.layout.addWidget(self.label)

        # Acceleration data with blue background
        self.accel_label = QLabel("Gia tốc:\nX: Không có dữ liệu\nY: Không có dữ liệu\nZ: Không có dữ liệu")
        self.accel_label.setAlignment(Qt.AlignLeft)
        self.accel_label.setStyleSheet("font-size: 24px; color: #555; padding: 20px; background-color: #ADD8E6; border-radius: 15px;")
        self.layout.addWidget(self.accel_label)

        # Alert label for warnings (red background for alerts)
        self.alert_label = QLabel("")
        self.alert_label.setStyleSheet("font-size: 24px; color: red; padding: 20px; background-color: #FFB6C1; border-radius: 15px;")
        self.alert_label.setAlignment(Qt.AlignLeft)
        self.layout.addWidget(self.alert_label)

        # Start SerialReader thread to read data
        self.serial_reader = SerialReader(serial_port)
        self.serial_reader.data_received.connect(self.on_data_received)
        self.serial_reader.start()

        # Buffers for recent heart rate and SpO2 values
        self.heart_rate_buffer = []
        self.spo2_buffer = []
        self.buffer_size = 5  # Number of values to consider for averaging

        self.setLayout(self.layout)

    def on_data_received(self, message):
        try:
            data_dict = json.loads(message)

            if all(key in data_dict for key in ["Pressure", "HeartRate", "Oxygen", "Acceleration X", "Acceleration Y", "Acceleration Z"]):
                pressure = data_dict["Pressure"]
                heartRate = data_dict["HeartRate"]
                oxyRate = data_dict["Oxygen"]
                x_scaled = data_dict["Acceleration X"]
                y_scaled = data_dict["Acceleration Y"]
                z_scaled = data_dict["Acceleration Z"]

                data_dict = {
                    "pressure": pressure,
                    "heartRate": heartRate,
                    "SpO2": oxyRate,
                    "accelX": x_scaled,
                    "accelY": y_scaled,
                    "accelZ": z_scaled
                }

                self.update_display(data_dict)
            else:
                print("Dữ liệu không đầy đủ!")
        except json.JSONDecodeError as e:
            print(f"Lỗi khi giải mã JSON: {e}")
        except Exception as e:
            print(f"Lỗi không xác định: {e}")

    def update_display(self, data):
        # Update displayed values with larger font size
        self.label.setText(
            f"Nhịp Tim: {data['heartRate']} bpm\n"
            f"SpO2: {data['SpO2']}%\n"
            f"Áp Suất: {data['pressure']} mmHg"
        )
        self.accel_label.setText(
            f"Gia tốc:\nX: {data['accelX']:.2f} g\nY: {data['accelY']:.2f} g\nZ: {data['accelZ']:.2f} g"
        )
        self.check_alerts(data)

    def check_alerts(self, data):
        # Store recent heart rate and SpO2 values for averaging
        self.heart_rate_buffer.append(data["heartRate"])
        self.spo2_buffer.append(data["SpO2"])

        # Remove the oldest value if the buffer size exceeds the limit
        if len(self.heart_rate_buffer) > self.buffer_size:
            self.heart_rate_buffer.pop(0)
        if len(self.spo2_buffer) > self.buffer_size:
            self.spo2_buffer.pop(0)

        # Calculate average heart rate and SpO2
        heart_rate_avg = sum(self.heart_rate_buffer) / len(self.heart_rate_buffer)
        spo2_avg = sum(self.spo2_buffer) / len(self.spo2_buffer)

        alerts = []
        # Check for warnings based on the averages
        if heart_rate_avg < 30:
            alerts.append(f"Nhịp Tim Thấp (Trung bình): {heart_rate_avg:.2f} bpm")
        if spo2_avg < 30:
            alerts.append(f"SpO2 Thấp (Trung bình): {spo2_avg:.2f}%")

        # Display alerts in red background if any
        self.alert_label.setText("Cảnh Báo:\n" + "\n".join(alerts) if alerts else "")

    def closeEvent(self, event):
        self.serial_reader.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    port_input_window = PortInputWindow()
    port_input_window.show()
    sys.exit(app.exec_())
