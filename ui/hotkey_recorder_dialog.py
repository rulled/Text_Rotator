from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeySequence

class HotkeyRecorderDialog(QDialog):
    def __init__(self, parent=None):
        super(HotkeyRecorderDialog, self).__init__(parent)
        self.setWindowTitle("Запись горячей клавиши")
        self.setGeometry(300, 300, 400, 150)
        self.setModal(True)
        
        self.layout = QVBoxLayout()
        
        self.info_label = QLabel("Нажмите комбинацию клавиш (не более двух)")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.info_label)
        
        self.current_keys_label = QLabel("Ожидание клавиш...")
        self.current_keys_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.current_keys_label)
        
        self.button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.cancel_button)
        
        self.layout.addLayout(self.button_layout)
        
        self.setLayout(self.layout)
        
        self.pressed_keys = set()
        self.result_hotkey = ""
        
        # Устанавливаем обработчики событий клавиатуры
        self.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            # Игнорируем повторные срабатывания для удерживаемых клавиш
            if not event.isAutoRepeat():
                key_name = self.get_key_name(event.key())
                
                if key_name:
                    self.pressed_keys.add(key_name)
                    self.update_display()
                    
                    # Если нажаты две клавиши, завершаем запись
                    if len(self.pressed_keys) >= 2:
                        self.finalize_hotkey()
                
                return True
                
        elif event.type() == QEvent.KeyRelease:
            # Если отпустили все клавиши и у нас есть хотя бы одна клавиша,
            # завершаем запись
            if not event.isAutoRepeat():
                key_name = self.get_key_name(event.key())
                
                if key_name in self.pressed_keys:
                    self.pressed_keys.remove(key_name)
                    
                if not self.pressed_keys and self.result_hotkey:
                    self.accept()
                    
                return True
                
        return super(HotkeyRecorderDialog, self).eventFilter(obj, event)
    
    def get_key_name(self, qt_key):
        # Преобразование кодов Qt в имена клавиш, распознаваемые библиотекой keyboard
        special_keys = {
            Qt.Key.Key_Control: "ctrl",
            Qt.Key.Key_Alt: "alt",
            Qt.Key.Key_Shift: "shift",
            Qt.Key.Key_Meta: "windows",  # или "cmd" на macOS
            Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_Escape: "esc",
            Qt.Key.Key_Space: "space",
            Qt.Key.Key_Return: "enter",
            Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Delete: "delete",
            Qt.Key.Key_Home: "home",
            Qt.Key.Key_End: "end",
            Qt.Key.Key_PageUp: "page up",
            Qt.Key.Key_PageDown: "page down",
            Qt.Key.Key_Insert: "insert",
            Qt.Key.Key_F1: "f1",
            Qt.Key.Key_F2: "f2",
            Qt.Key.Key_F3: "f3",
            Qt.Key.Key_F4: "f4",
            Qt.Key.Key_F5: "f5",
            Qt.Key.Key_F6: "f6",
            Qt.Key.Key_F7: "f7",
            Qt.Key.Key_F8: "f8",
            Qt.Key.Key_F9: "f9",
            Qt.Key.Key_F10: "f10",
            Qt.Key.Key_F11: "f11",
            Qt.Key.Key_F12: "f12",
            Qt.Key.Key_QuoteLeft: "`", # Добавляем обработку обратной кавычки
        }
        
        if qt_key in special_keys:
            return special_keys[qt_key]
        
        # Преобразование обычных клавиш (буквы, цифры)
        # Проверяем на печатные символы ASCII и некоторые другие общие
        key_text = QKeySequence(qt_key).toString()
        if len(key_text) == 1 and key_text.isprintable():
             return key_text.lower()

        # Возвращаем None, если не удалось определить
        return None
    
    def update_display(self):
        if self.pressed_keys:
            keys_text = " + ".join(sorted(self.pressed_keys))
            self.current_keys_label.setText(f"Текущая комбинация: {keys_text}")
        else:
            self.current_keys_label.setText("Ожидание клавиш...")
    
    def finalize_hotkey(self):
        # Формируем строку для библиотеки keyboard
        self.result_hotkey = "+".join(sorted(self.pressed_keys))
        self.current_keys_label.setText(f"Выбрано: {self.result_hotkey}") 