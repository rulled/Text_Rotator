from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeySequence

class HotkeyRecorderDialog(QDialog):
    def __init__(self, parent=None):
        super(HotkeyRecorderDialog, self).__init__(parent)
        self.setWindowTitle("Запись горячей клавиши")
        self.setGeometry(300, 300, 400, 180) # Adjusted height for new label
        self.setModal(True)
        
        self.layout = QVBoxLayout()
        
        self.info_label = QLabel("Нажмите клавишу или комбинацию клавиш.\nОтпустите немодификаторную клавишу для выбора, или нажмите OK.")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.info_label)
        
        self.current_keys_label = QLabel("Ожидание клавиш...")
        self.current_keys_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.current_keys_label)
        
        self.button_layout = QHBoxLayout()

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept_hotkey)
        self.ok_button.setEnabled(False) # Initially disabled
        self.button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.cancel_button)
        
        self.layout.addLayout(self.button_layout)
        
        self.setLayout(self.layout)
        
        self.pressed_keys = set()
        self.result_hotkey = ""
        
        # Устанавливаем обработчики событий клавиатуры
        self.installEventFilter(self)
    
    def is_modifier_key(self, key_name):
        return key_name in ["ctrl", "alt", "shift", "windows", "cmd"]

    def update_current_hotkey_and_display(self):
        if not self.pressed_keys:
            self.current_keys_label.setText("Ожидание клавиш...")
            self.ok_button.setEnabled(False)
            return

        keys_list = sorted(list(self.pressed_keys))
        displayed_hotkey = " + ".join(keys_list)
        self.current_keys_label.setText(f"Текущая комбинация: {displayed_hotkey}")

        has_non_modifier = any(not self.is_modifier_key(k) for k in keys_list)
        self.ok_button.setEnabled(has_non_modifier and bool(keys_list))

    def accept_hotkey(self):
        keys_list = sorted(list(self.pressed_keys))
        if keys_list and any(not self.is_modifier_key(k) for k in keys_list):
            self.result_hotkey = " + ".join(keys_list)
            self.accept()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if not event.isAutoRepeat():
                key_name = self.get_key_name(event.key())
                if key_name:
                    # Limit the number of keys in a combination (e.g., max 4)
                    if len(self.pressed_keys) < 4:
                        self.pressed_keys.add(key_name)
                    self.update_current_hotkey_and_display()
                return True  # Consume the event
                
        elif event.type() == QEvent.KeyRelease:
            if not event.isAutoRepeat():
                released_key_name = self.get_key_name(event.key())
                if released_key_name: # Make sure it's a key we track
                    # This check is crucial: was the released key part of the *current* combo?
                    # It's possible to get a KeyRelease for a key not in self.pressed_keys
                    # if events are processed out of order or if focus changes quickly.
                    if released_key_name not in self.pressed_keys and not self.is_modifier_key(released_key_name):
                        # This situation can happen if a non-modifier key is quickly pressed and released
                        # before its KeyPress could be fully processed to add it to pressed_keys, 
                        # but its KeyRelease arrives. If it's a single action key, treat it as such.
                        # This is a heuristic to catch very fast single key presses.
                        if not self.pressed_keys: # No other keys are being held
                            self.result_hotkey = released_key_name
                            self.accept()
                            return True
                        # else, another key is held, so this quick release might not be the intended hotkey alone

                    is_released_key_action_key = not self.is_modifier_key(released_key_name)
                    
                    # Create a snapshot of what keys *were* pressed including the one being released
                    # if it was indeed in the set. This logic assumes eventFilter sees KeyPress before KeyRelease for a given key.
                    potential_hotkey_list = sorted(list(self.pressed_keys.union({released_key_name} if released_key_name else set())))
                    # Filter out released_key_name if it wasn't actually pressed (empty string or None from get_key_name)
                    potential_hotkey_list = [k for k in potential_hotkey_list if k] 

                    if released_key_name in self.pressed_keys:
                        if is_released_key_action_key:
                            # If an action key is released, consider the current combination (including it) for acceptance.
                            # self.pressed_keys at this point still includes released_key_name.
                            current_combo_for_release = sorted(list(self.pressed_keys))
                            if current_combo_for_release and any(not self.is_modifier_key(k) for k in current_combo_for_release):
                                self.result_hotkey = " + ".join(current_combo_for_release)
                                self.accept()
                                return True # Hotkey accepted

                        # If it's a modifier release, or an action key release that didn't lead to acceptance,
                        # remove it from the set and update display.
                        self.pressed_keys.remove(released_key_name)
                        self.update_current_hotkey_and_display()
                    elif is_released_key_action_key and not self.pressed_keys:
                        # Handle case: single action key pressed and released very fast,
                        # KeyPress might not have added to self.pressed_keys if another release was processed first.
                        # If no other keys are pressed, accept this single action key.
                        self.result_hotkey = released_key_name
                        self.current_keys_label.setText(f"Выбрано: {self.result_hotkey}") # Update display before accept
                        self.accept()
                        return True

                return True # Consume the event
                
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
            keys_text = " + ".join(sorted(list(self.pressed_keys)))
            self.current_keys_label.setText(f"Текущая комбинация: {keys_text}")
        else:
            self.current_keys_label.setText("Ожидание клавиш...")