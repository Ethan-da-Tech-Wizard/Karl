import os
import sys

# R07: Kill telemetry before ANY library imports phone home
os.environ["HF_HUB_OFFLINE"]            = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_DATASETS_OFFLINE"]       = "1"
os.environ["TOKENIZERS_PARALLELISM"]    = "false"

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
