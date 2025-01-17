import os
import cv2
import shutil
import pickle
import concurrent.futures
import csv
import sys
import threading
import time
from PIL import Image, ImageTk
import face_recognition
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtGui import * 
from PyQt5.QtWidgets import * 
from threading import Thread, Timer


class FaceRecognitionApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Face Recognition App")
        self.setGeometry(100, 100, 1000, 800) 
        
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.root_folder = os.path.join(self.BASE_DIR, "ImagesAttendance")
        self.trespassers_folder = os.path.join(self.BASE_DIR, "trespassers")
        self.all_face_encodings = []
        self.all_face_names = []
        self.face_data_file = "face_data.pkl"
        self.light_mode = True
        self.load_face_data()

        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QtWidgets.QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.background_label = QtWidgets.QLabel(self.central_widget)
        self.background_label.setScaledContents(True)
        
        background_image = QtGui.QPixmap("background_image.jpg")
        self.background_label.setPixmap(background_image)
        self.background_label.setGeometry(0, 0, 1000, 800)
        
        self.button_layout = QtWidgets.QHBoxLayout()

        self.add_class_button = self.create_circular_button("Add or Update Users", "add.png", self.show_add_class_window)
        self.start_stream_button = self.create_circular_button("Start Live Stream", "live.png", self.start_live_stream_window)
        self.sort_images_button = self.create_circular_button("Sort Images", "sort.png", self.show_sort_images_window)
        self.mode_toggle_button = QtWidgets.QPushButton()
        self.mode_toggle_button.setIcon(QtGui.QIcon("moon.png" if self.light_mode else "sun.png"))
        self.mode_toggle_button.clicked.connect(self.toggle_mode)
        self.mode_toggle_button.setToolTip("Switch to Dark Mode" if self.light_mode else "Switch to Light Mode")

        self.button_layout.addWidget(self.add_class_button)
        self.button_layout.addWidget(self.start_stream_button)
        self.button_layout.addWidget(self.sort_images_button)

        self.layout.addStretch(1)
        self.layout.addLayout(self.button_layout)
        self.layout.addWidget(self.mode_toggle_button, alignment=QtCore.Qt.AlignRight) 

        self.scheduler_thread = Thread(target=self.run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()

        self.set_mode()
        self.light_mode_stylesheet = """
            QToolButton {
                background-color: #fff;
                color: #333;
            }
        """
        self.dark_mode_stylesheet = """
            QToolButton {
                background-color: #333;
                color: #fff;
            }
        """

        # Menu bar setup
        self.setup_menu_bar()

        # Initialize student dashboard widget
        self.student_dashboard = StudentDashboard()
        self.layout.addWidget(self.student_dashboard)
        self.student_dashboard.hide()  # Hide by default
        
    def resizeEvent(self, event):
        self.background_label.setGeometry(0, 0, self.width(), self.height())
        event.accept()

    def setup_menu_bar(self):
        menu_bar = self.menuBar()
        kebab_menu = QtWidgets.QMenu()
        kebab_menu.addAction(f"Student Dashboard", self.toggle_student_dashboard)
        kebab_button = QtWidgets.QToolButton()
        kebab_button.setMenu(kebab_menu)
        kebab_button.setIcon(QtGui.QIcon('kebab_menu.png'))
        kebab_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        # Set style sheet based on current mode
        kebab_button.setStyleSheet(self.light_mode_stylesheet if self.light_mode else self.dark_mode_stylesheet)
        menu_bar.setCornerWidget(kebab_button, QtCore.Qt.TopRightCorner)

    def toggle_student_dashboard(self):
        self.student_dashboard.setVisible(not self.student_dashboard.isVisible())

    def create_circular_button(self, name, icon_path, action):
        button = QtWidgets.QToolButton()
        button.setIcon(QtGui.QIcon(icon_path))
        button.setIconSize(QtCore.QSize(100, 100))
        button.setFixedSize(120, 120)  # Set fixed size for the buttons
        if self.light_mode:  # Change background color based on mode
            button.setStyleSheet("QToolButton { border-radius: 60px; background-color: #fff; }"
                                 "QToolButton:hover { background-color: #eee; }")
        else:
            button.setStyleSheet("QToolButton { border-radius: 60px; background-color: #555; }"
                                 "QToolButton:hover { background-color: #777; }")
        button.clicked.connect(action)
        button.setToolTip(name)
        button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)  # Allow buttons to grow
        return button

    def toggle_mode(self):
        self.light_mode = not self.light_mode
        self.set_mode()
        self.student_dashboard.set_table_color(self.light_mode)

    def set_mode(self):
        if self.light_mode:
            self.setStyleSheet("")
            self.mode_toggle_button.setIcon(QtGui.QIcon("moon.png"))
            self.mode_toggle_button.setToolTip("Switch to Dark Mode")
            # Change background color of circular buttons to white in light mode
            self.add_class_button.setStyleSheet("QToolButton { border-radius: 50px; background-color: #fff; }"
                                                "QToolButton:hover { background-color: #eee; }")
            self.start_stream_button.setStyleSheet("QToolButton { border-radius: 50px; background-color: #fff; }"
                                                   "QToolButton:hover { background-color: #eee; }")
            self.sort_images_button.setStyleSheet("QToolButton { border-radius: 50px; background-color: #fff; }"
                                                  "QToolButton:hover { background-color: #eee; }")
        else:
            dark_stylesheet = """
                QWidget{
                    background-color: #333;
                    color: #fff;
                }
                QPushButton{
                    background-color: #555;
                    color: #fff;
                    border: none;
                    padding: 10px 20px;
                    margin: 5px;
                }
                QPushButton:hover{
                    background-color: #777;
                }
            """
            self.setStyleSheet(dark_stylesheet)
            self.mode_toggle_button.setIcon(QtGui.QIcon("sun.png"))
            self.mode_toggle_button.setToolTip("Switch to Light Mode")
            # Change background color of circular buttons to default in dark mode
            self.add_class_button.setStyleSheet("QToolButton { border-radius: 50px; background-color: #555; }"
                                                "QToolButton:hover { background-color: #777; }")
            self.start_stream_button.setStyleSheet("QToolButton { border-radius: 50px; background-color: #555; }"
                                                   "QToolButton:hover { background-color: #777; }")
            self.sort_images_button.setStyleSheet("QToolButton { border-radius: 50px; background-color: #555; }"
                                                  "QToolButton:hover { background-color: #777; }")

    def update_face_data(self, class_name=None):
        existing_face_encodings, existing_face_names, flag = self.load_face_data()

        if flag == 0:
            # Encode faces from the updated dataset
            new_face_encodings = []
            new_face_names = []

            if class_name:
                # Use the encoding function for a specific class
                average_face_encoding, class_name = self.encode_faces_in_class(os.path.join(self.root_folder, class_name))
                if average_face_encoding is not None:
                    new_face_encodings.append(average_face_encoding)
                    new_face_names.append(class_name)
            else:
                # Iterate through each folder in the root folder
                for class_name in os.listdir(self.root_folder):
                    class_folder = os.path.join(self.root_folder, class_name)

                    if os.path.isdir(class_folder):
                        # Check if the class is already present in the existing data
                        if class_name not in existing_face_names:
                            # Use the encoding function for a specific class
                            average_face_encoding, class_name = self.encode_faces_in_class(class_folder)
                            if average_face_encoding is not None:
                                new_face_encodings.append(average_face_encoding)
                                new_face_names.append(class_name)

            # Combine existing and new face data
            existing_face_encodings = existing_face_encodings + new_face_encodings
            existing_face_names = existing_face_names + new_face_names

        # Save the combined face data to the file using the existing save_face_data() function
        self.save_face_data(existing_face_encodings, existing_face_names)

        # Update class variables
        self.all_face_encodings = existing_face_encodings
        self.all_face_names = existing_face_names

    def load_face_data(self):
        # Check if the face data file exists
        if os.path.exists(self.face_data_file):
            # Load existing face data
            with open(self.face_data_file, 'rb') as file:
                face_data = pickle.load(file)
                existing_face_encodings = face_data.get('encodings', [])
                existing_face_names = face_data.get('names', [])
                flag = 0
        else:
            # Encode faces from the entire dataset
            existing_face_encodings, existing_face_names = self.encode_faces_in_dataset(self.root_folder)
            # Save the encoded data to the file using the existing save_face_data() function
            self.save_face_data(existing_face_encodings, existing_face_names)
            flag = 1
        self.all_face_encodings = existing_face_encodings
        self.all_face_names = existing_face_names
        return existing_face_encodings, existing_face_names, flag
    
    def save_face_data(self, encodings, names):
        face_data = {'encodings': encodings, 'names': names}
        with open(self.face_data_file, 'wb') as file:
            pickle.dump(face_data, file)
        print("Encodings Saved.")

    def encode_faces_in_class(self, class_folder):
        # Initialize face encodings and face names for the current class
        class_face_encodings = []
        class_face_names = []

        # Iterate through each image in the class folder
        for filename in os.listdir(class_folder):
            image_path = os.path.join(class_folder, filename)

            # Load the image
            image = face_recognition.load_image_file(image_path)

            # Find face encodings
            face_encodings = face_recognition.face_encodings(image)

            for face_encoding in face_encodings:
                # Use all face encodings (not just the first one)
                class_face_encodings.append(face_encoding)
                class_face_names.append(os.path.basename(class_folder))

        # Calculate the average face encoding for the class
        if class_face_encodings:
            average_face_encoding = [
                sum(emb[i] for emb in class_face_encodings) / len(class_face_encodings)
                for i in range(len(class_face_encodings[0]))
            ]
            return average_face_encoding, os.path.basename(class_folder)
        else:
            print("Class encoding failed")
            return None, None

    def encode_faces_in_dataset(self, root_folder):
        all_face_encodings = []
        all_face_names = []

        # Iterate through each folder in the root folder
        for class_name in os.listdir(root_folder):
            class_folder = os.path.join(root_folder, class_name)

            if os.path.isdir(class_folder):
                # Initialize face encodings and face names for the current class
                class_face_encodings = []
                class_face_names = []

                # Iterate through each image in the class folder
                for filename in os.listdir(class_folder):
                    image_path = os.path.join(class_folder, filename)

                    # Load the image
                    image = face_recognition.load_image_file(image_path)

                    # Find face encodings
                    face_encodings = face_recognition.face_encodings(image)

                    for face_encoding in face_encodings:
                        # Use all face encodings (not just the first one)
                        class_face_encodings.append(face_encoding)
                        class_face_names.append(class_name)

                # Calculate the average face encoding for the class
                if class_face_encodings:
                    average_face_encoding = [
                        sum(emb[i] for emb in class_face_encodings) / len(class_face_encodings)
                        for i in range(len(class_face_encodings[0]))
                    ]

                    # Add the average face encoding and name for the current class to the overall list
                    all_face_encodings.append(average_face_encoding)
                    all_face_names.append(class_name)

        return all_face_encodings, all_face_names

    def show_sort_images_window(self):
        sort_images_window = QtWidgets.QDialog(self)
        sort_images_window.setWindowTitle("Sort Images")
        sort_images_window.setGeometry(self.x() + 300, self.y() + 275, 400, 250)
        sort_images_window.setWindowIcon(QtGui.QIcon("sort.png"))

        folder_label = QtWidgets.QLabel("Select Folder Path:")
        folder_button = QtWidgets.QPushButton("Browse")
        folder_button.clicked.connect(self.get_folder_path)
        self.folder_entry = QtWidgets.QLineEdit()

        class_label = QtWidgets.QLabel("Enter Class Name:")
        self.class_entry = QtWidgets.QLineEdit()

        submit_button = QtWidgets.QPushButton("Submit")
        submit_button.clicked.connect(lambda: self.sort_images(self.folder_entry.text(), self.class_entry.text(), sort_images_window))

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(folder_label)
        layout.addWidget(self.folder_entry)
        layout.addWidget(folder_button)
        layout.addWidget(class_label)
        layout.addWidget(self.class_entry)
        layout.addWidget(submit_button)
        sort_images_window.setLayout(layout)
        sort_images_window.exec_()

    def get_folder_path(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        self.folder_entry.setText(folder_path)

    def run_scheduler(self):
        self.delete_similar_faces_wrapper()
        timer = Timer(600, self.run_scheduler)
        timer.start()

    def delete_similar_faces_wrapper(self):
        self.delete_similar_faces(self.trespassers_folder)

    def delete_similar_faces(self, folder_path, tolerance=0.6):
        if not os.path.exists(folder_path):
            return
        face_encodings = []
        file_paths = []
        #print("Started")
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            image = face_recognition.load_image_file(file_path)
            face_encoding = face_recognition.face_encodings(image)
            if len(face_encoding) > 0:
                face_encodings.append(face_encoding[0])
                file_paths.append(file_path)
        #print("model work done")
        for i in range(len(face_encodings)):
            for j in range(i + 1, len(face_encodings)):
                if face_recognition.compare_faces([face_encodings[i]], face_encodings[j], tolerance=tolerance)[0]:
                    print(f"Deleting similar faces: {file_paths[i]} and {file_paths[j]}")
                    if os.path.exists(file_paths[j]):
                        os.remove(file_paths[j])
                    else:
                        print(f"File not found: {file_paths[j]}")
        #print("Deletion successful")

    def sort_images(self, folder_path, class_name, sort_images_window):
        class_index = self.all_face_names.index(class_name)
        class_face_encoding = self.all_face_encodings[class_index]
        output_folder_path = os.path.join(folder_path, f"Sorted_{class_name}_Images")
        os.makedirs(output_folder_path, exist_ok=True)
        for filename in os.listdir(folder_path):
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                image_path = os.path.join(folder_path, filename)
                image = face_recognition.load_image_file(image_path)
                face_locations = face_recognition.face_locations(image)
                face_encodings = face_recognition.face_encodings(image, face_locations)
                for face_encoding in face_encodings:
                    match = face_recognition.compare_faces([class_face_encoding], face_encoding, tolerance=0.5)
                    if match[0]:
                        shutil.copy(image_path, os.path.join(output_folder_path, filename))
        QtWidgets.QMessageBox.information(self, "Sorting Complete", f"Images for class {class_name} have been sorted.")
        sort_images_window.close()

    def show_add_class_window(self):
        add_class_window = QtWidgets.QDialog(self)
        add_class_window.setWindowTitle("Add or Update")
        add_class_window.setGeometry(self.x() + 300, self.y() + 325, 400, 100)
        add_class_window.setWindowIcon(QtGui.QIcon("add.png"))
        
        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel("Enter the User name:")
        entry = QtWidgets.QLineEdit()
        add_button = QtWidgets.QPushButton("Add Class")
        add_button.clicked.connect(lambda: self.add_new_class(entry.text(), add_class_window))
        layout.addWidget(label)
        layout.addWidget(entry)
        layout.addWidget(add_button)
        add_class_window.setLayout(layout)
        add_class_window.exec_()

    def add_new_class(self, class_name, add_class_window):
        folder_path = os.path.join(self.root_folder, class_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        video_capture = cv2.VideoCapture(0)
        count = 0
        while True:
            ret, frame = video_capture.read()
            cv2.imshow('Capture Frame', frame)
            key = cv2.waitKey(1)
            if key == ord('c'):
                image_path = os.path.join(folder_path, f"{class_name}_{count}.jpg")
                cv2.imwrite(image_path, frame)
                print(f"Image {count} captured for class {class_name}")
                count += 1
            elif key == ord('q'):
                break
        video_capture.release()
        cv2.destroyAllWindows()
        self.update_face_data(class_name)
        add_class_window.close()

    def start_live_stream_window(self):
        dialog = StartLiveStreamDialog()
        if dialog.exec_():
            input_type = dialog.get_input_type()
            if input_type == "RTSP":
                url = dialog.get_rtsp_url()
                self.start_live_stream_rtsp(url)
            elif input_type == "Webcam":
                port = dialog.get_webcam_port()
                self.start_live_stream_webcam(port)

    def start_live_stream_rtsp(self, url):
        live_stream_window = LiveStreamApp(self.all_face_encodings, self.all_face_names, rtsp_url=url)
        live_stream_window.start_live_stream_rtsp(url)

    def start_live_stream_webcam(self, port):
        live_stream_window = LiveStreamApp(self.all_face_encodings, self.all_face_names, webcam_port=port)
        live_stream_window.start_live_stream_webcam(port)


class StartLiveStreamDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Start Live Stream")
        self.setWindowIcon(QtGui.QIcon("live.png"))
        self.setGeometry(self.x() + 300, self.y() + 275, 400, 250)

        layout = QtWidgets.QVBoxLayout()

        self.input_type_label = QtWidgets.QLabel("Select Input Type:")
        self.input_type_combo = QtWidgets.QComboBox()
        self.input_type_combo.addItems(["RTSP", "Webcam"])

        self.rtsp_url_label = QtWidgets.QLabel("RTSP URL:")
        self.rtsp_url_entry = QtWidgets.QLineEdit()

        self.webcam_port_label = QtWidgets.QLabel("Webcam Port:")
        self.webcam_port_spinbox = QtWidgets.QSpinBox()
        self.webcam_port_spinbox.setMinimum(0)
        self.webcam_port_spinbox.setMaximum(1)

        self.start_button = QtWidgets.QPushButton("Start")
        self.start_button.clicked.connect(self.accept)

        layout.addWidget(self.input_type_label)
        layout.addWidget(self.input_type_combo)
        layout.addWidget(self.rtsp_url_label)
        layout.addWidget(self.rtsp_url_entry)
        layout.addWidget(self.webcam_port_label)
        layout.addWidget(self.webcam_port_spinbox)
        layout.addWidget(self.start_button)

        self.setLayout(layout)

    def get_input_type(self):
        return self.input_type_combo.currentText()

    def get_rtsp_url(self):
        return self.rtsp_url_entry.text()

    def get_webcam_port(self):
        return self.webcam_port_spinbox.value()


class StudentDashboard(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QtWidgets.QVBoxLayout(self)
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(3)
        self.set_table_color()
        self.table.setHorizontalHeaderLabels(["Student ID", "Student Name", "Accommodation"])
        h_header = self.table.horizontalHeader()
        h_header.setStyleSheet(f"color: {'#fff' if not self.light_mode else '#333'};")
        v_header = self.table.verticalHeader()
        v_header.setStyleSheet(f"color: {'#fff' if not self.light_mode else '#333'};")

        # Sample data for demonstration
        sample_data = [
            ["222AD118", "Athi", "Hosteller"],
            ["221CS280", "Ritthyk", "Hosteller"],
            ["221CS314", "SivaRam", "Hosteller"],
            ["222AD116", "Artha", "DayScholar"]
        ]

        self.set_table_data(sample_data)

        self.layout.addWidget(self.table)
        self.hide()  # Hide by default

    def set_table_color(self, light_mode=True):
        self.light_mode = light_mode
        # Use ternary if-else to set text color based on mode
        self.table.setStyleSheet(f"color: {'#333' if self.light_mode else '#fff'};")

    def set_table_data(self, data):
        self.table.setRowCount(len(data))
        for row, rowData in enumerate(data):
            for col, value in enumerate(rowData):
                item = QtWidgets.QTableWidgetItem(str(value))
                self.table.setItem(row, col, item)
                

class LiveStreamApp(QtWidgets.QWidget):
    def __init__(self, all_face_encodings, all_face_names, rtsp_url=None, webcam_port=None):
        super().__init__()
        self.all_face_encodings = all_face_encodings
        self.all_face_names = all_face_names
        self.streaming = False
        self.video_capture = None
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.trespassers_folder = os.path.join(self.BASE_DIR, "trespassers")
        self.window_width = 1920
        self.window_height = 1080
        self.live_stream_window = QtWidgets.QMainWindow()
        self.live_stream_window.setWindowTitle("Live Stream")
        self.live_stream_window.setWindowIcon(QtGui.QIcon("live.png"))
        self.live_stream_window.setGeometry(0, 0, self.window_width, self.window_height)
        self.live_stream_label = QtWidgets.QLabel()
        self.live_stream_label.setAlignment(QtCore.Qt.AlignCenter)
        self.live_stream_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.name_label = QtWidgets.QLabel("")
        self.name_label.setFont(QtGui.QFont("Helvetica", 14))
        self.name_label.setAlignment(QtCore.Qt.AlignRight)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.live_stream_label)
        layout.addWidget(self.name_label)
        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(layout)
        self.live_stream_window.setCentralWidget(central_widget)
        self.live_stream_window.show()

        # Connect destroyed signal to cleanup method
        self.live_stream_window.destroyed.connect(self.cleanup)

    def start_live_stream_rtsp(self, url):
        self.video_capture = cv2.VideoCapture(f"{url}")
        if url:
            rtsp_thread = threading.Thread(target=self.start_stream)
            rtsp_thread.daemon = True
            rtsp_thread.start()

    def start_live_stream_webcam(self, port):
        self.video_capture = cv2.VideoCapture(port)
        if port is not None:
            webcam_thread = threading.Thread(target=self.start_stream)
            webcam_thread.daemon = True
            webcam_thread.start()

    def start_stream(self):
        if self.video_capture is not None:
            self.streaming = True
            frame_rate = 2
            start_time = time.time()
            csv_file_path = "detections.csv"
            os.makedirs(self.trespassers_folder, exist_ok=True)
            with open(csv_file_path, mode='a', newline='') as csv_file:
                fieldnames = ['Class Name', 'Date', 'Time']
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                while self.streaming:
                    ret, frame = self.video_capture.read()
                    if ret:
                        elapsed_time = time.time() - start_time
                        if elapsed_time > 1 / frame_rate:
                            start_time = time.time()
                            frame = cv2.resize(frame, (int(self.window_width * 0.7), self.window_height))
                            face_locations = face_recognition.face_locations(frame, model="cnn")
                            face_encodings = face_recognition.face_encodings(frame, face_locations, model="cnn")
                            names = []
                            for face_encoding in face_encodings:
                                matches = face_recognition.compare_faces(self.all_face_encodings, face_encoding, tolerance=0.5)
                                name = "Unknown"
                                if True in matches:
                                    first_match_index = matches.index(True)
                                    name = self.all_face_names[first_match_index]
                                names.append(name)
                            current_time = time.strftime('%Y-%m-%d_%H_%M_%S')
                            for (top, right, bottom, left), name in zip(face_locations, names):
                                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                                font = cv2.FONT_HERSHEY_DUPLEX
                                cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.5, (255, 255, 255), 1)
                                if name == "Unknown":
                                    image_path = os.path.join(self.trespassers_folder, f"trespasser_{current_time}.png")
                                    temp = cv2.imwrite(image_path, frame)
                                else:
                                    writer.writerow({'Class Name': name, 'Date': current_time.split("_")[0], 'Time': current_time.split("_")[1]})
                            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            h, w, ch = frame.shape
                            bytes_per_line = ch * w
                            qt_image = QtGui.QImage(frame.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
                            qt_pixmap = QtGui.QPixmap.fromImage(qt_image)
                            self.live_stream_label.setPixmap(qt_pixmap)
                            self.live_stream_label.setScaledContents(True)
                            self.name_label.setText("\n".join(names))
                            key = cv2.waitKey(1)
                            if key == ord("q"):
                                self.stop_live_stream()
                    else:
                        print("Error reading frame from RTSP stream")
            self.video_capture.release()

    def stop_live_stream(self):
        self.streaming = False
        self.video_capture.release()
        cv2.destroyAllWindows()
        self.live_stream_window.close()

    def cleanup(self):
        self.streaming = False
        if self.video_capture is not None and self.video_capture.isOpened():
            self.video_capture.release()
        cv2.destroyAllWindows()
        
    def closeEvent(self, event):
        self.stop_live_stream()
        event.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = FaceRecognitionApp()
    window.show()
    app.exec_()
