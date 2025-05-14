import sys
from PyQt5 import QtWidgets
from PyQt5.QtGui import QIcon
from text_rotator import TextRotator
from utils.resource_path import resource_path
import os

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    # Устанавливаем иконку приложения
    app_icon_path = resource_path("assets/app.ico")
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))
    else:
        print(f"Warning: Application icon not found at {app_icon_path}")
        
    app.setQuitOnLastWindowClosed(False)
    window = TextRotator()
    sys.exit(app.exec_()) 