import sys
from PyQt6.QtWidgets import QApplication
from app.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Load stylesheet
    try:
        with open("app/ui/styles/neutral.qss", "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
