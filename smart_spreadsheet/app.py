import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    # window.check_settings_and_prompt()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
