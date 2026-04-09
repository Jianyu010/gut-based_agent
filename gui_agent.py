import threading
import queue
time
import pyautogui
import logging
from PyQt5.QtCore import QTimer, QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget, QPushButton
from permissions_check import PermissionsChecker, PermissionError

logging.basicConfig(level=logging.DEBUG)

# Initialize the PermissionsChecker
permissions_checker = PermissionsChecker()
permissions_checker.grant_permission('write_file')


class MarkerDetector(QObject):
    signal = pyqtSignal()

    def __init__(self, queue, *args, **kwargs):
        super(MarkerDetector, self).__init__(*args, **kwargs)
        self.queue = queue
        self.stop_event = threading.Event()

    def run(self):
        while not self.stop_event.is_set():
            if pyautogui.pixelMatchesColor(100, 200, (255, 0, 0)):
                self.signal.emit()
                self.queue.put('Marker Detected')
                break
            time.sleep(0.1)
        logging.debug('Marker detection thread stopped.')

    def stop(self):
        self.stop_event.set()


class GUIAgent(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(GUIAgent, self).__init__(*args, **kwargs)
        self.setWindowTitle('GUI Agent')
        self.setGeometry(100, 100, 800, 600)

        self.text_edit = QTextEdit(self)
        self.button_open_textedit = QPushButton('Open TextEdit and Type', self)
        self.button_open_textedit.clicked.connect(self.open_textedit_and_type)

        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        layout.addWidget(self.button_open_textedit)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.queue = queue.Queue()
        self.marker_detector_thread = None
        self.project_directory = '/Users/jianyulong/Desktop/gui-based_agent'  # Set the project directory here

    def open_textedit_and_type(self):
        pyautogui.hotkey('command', 'space')
        time.sleep(1)
        pyautogui.typewrite('TextEdit\n', interval=0.25)
        time.sleep(3)
        pyautogui.typewrite('hello world\n', interval=0.25)

        self.marker_detector_thread = MarkerDetector(self.queue)
        self.marker_detector_thread.signal.connect(self.on_marker_detected)
        thread = threading.Thread(target=self.marker_detector_thread.run)
        thread.start()

    def on_marker_detected(self):
        logging.debug('Marker detected signal received.')
        pyautogui.hotkey('command', 's')
        time.sleep(1)
        file_path = f'{self.project_directory}/output.txt'
        try:
            if permissions_checker.check_permission('write_file'):
                pyautogui.typewrite(file_path + '\n', interval=0.25)
                pyautogui.press('enter')
            else:
                logging.error('Permission denied for writing to the file.')
        except PermissionError as e:
            logging.error(f'Permission error: {e}')

    def wait_for_marker(self):
        timer = QTimer()
        timer.timeout.connect(lambda: self.check_queue(timer))
        timer.start(100)  # Check every 100ms (10Hz)

    def check_queue(self, timer):
        try:
            msg = self.queue.get_nowait()
            logging.debug(f'Queue message received: {msg}')
            if msg == 'Marker Detected':
                timer.stop()
                self.on_marker_detected()
        except queue.Empty:
            pass

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    agent = GUIAgent()
    agent.show()
    sys.exit(app.exec_())
