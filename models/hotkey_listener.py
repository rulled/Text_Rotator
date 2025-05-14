import time
import keyboard
from PyQt5.QtCore import QThread, pyqtSignal

class HotkeyListener(QThread):
    """Поток для прослушивания горячей клавиши с использованием библиотеки keyboard."""
    hotkey_pressed = pyqtSignal()

    def __init__(self, hotkey_str, parent=None):
        super(HotkeyListener, self).__init__(parent)
        self.hotkey_str = hotkey_str
        self.running = False

    def run(self):
        self.running = True
        
        # Функция-заглушка для add_hotkey
        def on_hotkey():
            # Используем небольшой sleep, чтобы избежать "дребезга"
            time.sleep(0.1) 
            if self.running:
                self.hotkey_pressed.emit()

        try:
            keyboard.add_hotkey(self.hotkey_str, on_hotkey, suppress=True)
            # Держим поток активным, ожидая события
            while self.running:
                time.sleep(0.1) # Пауза, чтобы не загружать процессор
        except Exception as e:
            print(f"Ошибка в потоке HotkeyListener: {e}") # Лучше логировать ошибки
        finally:
            # Убираем обработчик при завершении потока
            try:
                keyboard.remove_hotkey(self.hotkey_str)
            except KeyError:
                 # Горячая клавиша могла быть уже удалена
                 pass
            print("HotkeyListener остановлен")

    def stop(self):
        self.running = False
        print("Остановка HotkeyListener...")
        # Небольшая хитрость, чтобы прервать ожидание в keyboard, 
        # если он завис в ожидании системных сообщений
        # keyboard.press_and_release('esc') # Это может вызвать нежелательное поведение
        self.wait(1000) # Ждем завершения потока не более 1 секунды 