import os
import sys
from PyQt6.QtWidgets import QApplication

# Set offscreen platform plugin to run PyQt tests headlessly in all environments
if "QT_QPA_PLATFORM" not in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Initialize a global QApplication instance before any test modules are imported
if QApplication.instance() is None:
    _global_test_app = QApplication(sys.argv)

if QApplication.instance() is not None:
    QApplication.instance().setProperty("is_test", True)
