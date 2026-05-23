import sys
import os
from PyQt6.QtWidgets import QApplication
from app.ui.main_window import MainWindow

def main():
    # Silence HuggingFace telemetry before any imports can trigger it
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    app = QApplication(sys.argv)
    app.setApplicationName("Karl")

    # Minimal base stylesheet (ASCII-only, safe on all Windows locales).
    # The full theme stylesheet is applied by MainWindow after init.
    app.setStyleSheet(
        "QMainWindow, QWidget { "
        "background-color: #0D0D0F; color: #DDDDE0; "
        "font-family: 'Segoe UI', Inter, Arial, sans-serif; font-size: 11pt; }"
    )

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
