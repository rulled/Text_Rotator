import time
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QApplication, QListWidgetItem
from PyQt5.QtCore import Qt, QPoint, QEvent
from PyQt5.QtGui import QCursor
from functools import partial

import sys
import os

# Импортируем Windows API для размещения окна на переднем плане на уровне системы
if sys.platform == "win32":
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        ctypes = None
else:
    ctypes = None

class TextSelectionPopup(QDialog):
    def __init__(self, data, callback, parent=None):
        super(TextSelectionPopup, self).__init__(parent, 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint)  # Добавляем флаг "всегда поверх"
        self.setWindowModality(Qt.WindowModal)  # Делаем модальным относительно окна
        self.setModal(True)  # Гарантируем модальность
        self.setAttribute(Qt.WA_DeleteOnClose)  # Автоматически удалять при закрытии
        
        self.data = data
        self.callback = callback
        self.is_dark_theme = self.detect_dark_theme()
        self.folder_stack = []  # Для навигации по папкам
        self.init_ui()
        
    def detect_dark_theme(self):
        """Определяет, активна ли темная тема в системе или у родительского окна."""
        if hasattr(self.parent(), "is_dark_theme"):
            return self.parent().is_dark_theme
        else:
            # Определяем по системе, если родитель не предоставляет информацию
            try:
                # Проверка для Windows
                if sys.platform == "win32":
                    import winreg
                    registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                    reg_key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                    # AppsUseLightTheme = 0 означает тёмный режим
                    is_light_theme = int(winreg.QueryValueEx(reg_key, "AppsUseLightTheme")[0])
                    return is_light_theme == 0
                return False
            except Exception as e:
                print(f"Ошибка определения темы для popup: {e}")
                return False
        
    def init_ui(self):
        self.setWindowTitle('Select Text')
        
        # Применяем стили в зависимости от темы
        if self.is_dark_theme:
            # Темная тема
            self.setStyleSheet("""
                QWidget {
                    background-color: #1E1E1E;
                    border: 2px solid #3C3C3C;
                    border-radius: 5px;
                }
                QListWidget {
                    border: none;
                    font-family: 'Inter';
                    font-size: 14px;
                    font-weight: 400;
                    padding: 5px;
                    background-color: #2D2D2D;
                    color: #FFFFFF;
                }
                QListWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #3C3C3C;
                }
                QListWidget::item:selected {
                    background-color: #3C3C3C;
                    color: #FFFFFF;
                }
                QListWidget::item:hover {
                    background-color: #3C3C3C;
                }
                QListWidget::item[type="folder"] {
                    font-weight: 500;
                    color: #FFFFFF;
                    background-color: #2D2D2D;
                    border-bottom: 1px solid #3C3C3C;
                }
                QListWidget::item[type="folder"]:hover {
                    background-color: #3C3C3C;
                }
                QListWidget::item[type="folder"]:selected {
                    background-color: #3C3C3C;
                    color: #FFFFFF;
                }
                /* ScrollBar Styles - Dark */
                QScrollBar:vertical {
                    border: none;
                    background: #2D2D2D; /* Match ListWidget background */
                    width: 8px; /* Thinner scrollbar */
                    margin: 0px 0px 0px 0px;
                }
                QScrollBar::handle:vertical {
                    background: #555555; /* Dark gray handle */
                    min-height: 25px;
                    border-radius: 4px; /* Rounded handle */
                }
                QScrollBar::handle:vertical:hover {
                    background: #666666; /* Slightly lighter on hover */
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    border: none;
                    background: none;
                    height: 0px;
                    width: 0px;
                }
                QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                    background: none;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
            """)
        else:
            # Светлая тема
            self.setStyleSheet("""
                QWidget {
                    background-color: white;
                    border: 2px solid #2196F3;
                    border-radius: 5px;
                }
                QListWidget {
                    border: none;
                    font-family: 'Inter';
                    font-size: 14px;
                    font-weight: 400;
                    padding: 5px;
                    background-color: white; /* Match scrollbar track */
                }
                QListWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #F0F0F0;
                }
                QListWidget::item:selected {
                    background-color: #E3F2FD;
                    color: #1976D2;
                }
                QListWidget::item:hover {
                    background-color: #F5F5F5;
                }
                QListWidget::item[type="folder"] {
                    font-weight: 500;
                    color: #1976D2;
                    background-color: #F8F9FA;
                    border-bottom: 1px solid #E9ECEF;
                }
                QListWidget::item[type="folder"]:hover {
                    background-color: #E9ECEF;
                }
                QListWidget::item[type="folder"]:selected {
                    background-color: #E3F2FD;
                    color: #1976D2;
                }
                 /* ScrollBar Styles - Light */
                 QScrollBar:vertical {
                     border: none;
                     background: white; /* Match ListWidget background */
                     width: 8px; /* Thinner scrollbar */
                     margin: 0px 0px 0px 0px;
                 }
                 QScrollBar::handle:vertical {
                     background: #CCCCCC; /* Light gray handle */
                     min-height: 25px;
                     border-radius: 4px; /* Rounded handle */
                 }
                 QScrollBar::handle:vertical:hover {
                     background: #BBBBBB; /* Slightly darker on hover */
                 }
                 QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                     border: none;
                     background: none;
                     height: 0px;
                     width: 0px;
                 }
                 QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                     background: none;
                 }
                 QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                     background: none;
                 }
            """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        
        self.text_list = QListWidget()
        self.update_text_list()
        self.text_list.itemClicked.connect(self.on_text_selected)
        # Ensure scrollbar appears when needed
        self.text_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.text_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.text_list)
        
        # Adjust size after items are added
        self.adjust_popup_size()
        
    def update_text_list(self):
        self.text_list.clear()
        # Если мы в корне — показываем только папки
        if not self.folder_stack:
            for item in self.data:
                if isinstance(item, dict) and item.get('type') == 'folder':
                    folder_name = item.get('name', 'Безымянная папка')
                    list_item = QListWidgetItem(f"📁 {folder_name}")
                    list_item.setData(Qt.UserRole, None)
                    list_item.setData(Qt.UserRole + 1, 'folder')
                    # Для перехода — сохраняем индекс
                    list_item.setData(Qt.UserRole + 2, item)
                    self.text_list.addItem(list_item)
        else:
            # Показываем кнопку "Назад"
            back_item = QListWidgetItem("← Назад к списку папок")
            back_item.setData(Qt.UserRole, None)
            back_item.setData(Qt.UserRole + 1, 'back')
            self.text_list.addItem(back_item)
            # Показываем тексты выбранной папки
            current_folder = self.folder_stack[-1]
            for item in current_folder.get('items', []):
                if isinstance(item, str):
                    preview = item.replace('\n', ' ')
                    preview = preview[:50] + '...' if len(preview) > 50 else preview
                    list_item = QListWidgetItem(preview)
                    list_item.setData(Qt.UserRole, item)
                    self.text_list.addItem(list_item)
        # Adjust size whenever the list content changes
        self.adjust_popup_size()
        
    def adjust_popup_size(self):
        """Dynamically adjusts popup height based on screen size and item count."""
        screen = QApplication.primaryScreen()
        screen_height = screen.size().height() if screen else 800
        min_percent = 0.15
        max_percent = 0.5
        min_height = int(screen_height * min_percent)
        max_height = int(screen_height * max_percent)

        # Estimate item height
        item_height = 35
        try:
            if self.text_list.count() > 0:
                hint = self.text_list.sizeHintForRow(0)
                if hint > 5:
                    item_height = hint
        except Exception:
            pass

        layout_margins = self.layout().contentsMargins()
        widget_border = 2 * 2
        list_padding = 5 * 2
        vertical_margins = layout_margins.top() + layout_margins.bottom() + widget_border + list_padding

        num_items = self.text_list.count()
        ideal_list_height = item_height * max(1, num_items)

        # Ограничения по высоте: минимум 15% экрана, максимум 50% экрана
        target_list_height = max(min_height, min(ideal_list_height, max_height))
        
        # Если элементов больше чем помещается — появляется скроллбар
        self.text_list.setMinimumHeight(min_height)
        self.text_list.setMaximumHeight(max_height)
        self.text_list.setFixedHeight(target_list_height)

        extra_padding = 5
        total_height = self.text_list.height() + vertical_margins + extra_padding
        current_width = self.width() if self.width() > 100 else 400
        self.setFixedSize(current_width, total_height)
        print(f"Adjusted popup size: {num_items} items, List H={target_list_height}, Total H={total_height}, Screen H={screen_height}")


    def on_text_selected(self, item):
        item_type = item.data(Qt.UserRole + 1)
        if item_type == 'folder':
            # Переход внутрь папки
            folder_obj = item.data(Qt.UserRole + 2)
            self.folder_stack.append(folder_obj)
            self.update_text_list()
        elif item_type == 'back':
            # Возврат к списку папок
            if self.folder_stack:
                self.folder_stack.pop()
                self.update_text_list()
        elif item.data(Qt.UserRole) is not None:
            # Выбран текст
            self.close()
            time.sleep(0.3)
            self.callback(item.data(Qt.UserRole))
        
    def show_at_cursor(self):
        print("TextSelectionPopup.show_at_cursor() called")
        cursor_pos = QCursor.pos()
        print(f"Cursor position: {cursor_pos}")
        
        # Получаем все экраны в системе
        screens = QApplication.screens()
        target_screen = None
        
        # Находим экран, на котором находится курсор
        for screen in screens:
            geometry = screen.geometry()
            if geometry.contains(cursor_pos):
                target_screen = screen
                print(f"Found cursor on screen: {screen.name()} with geometry: {geometry}")
                break
                
        # Если не нашли экран (что маловероятно), используем основной
        if not target_screen:
            target_screen = QApplication.primaryScreen()
            print(f"Cursor not found on any screen, using primary: {target_screen.name()}")
        
        # Получаем геометрию целевого экрана
        screen_geometry = target_screen.geometry()
        
        # Вычисляем позицию так, чтобы окно не выходило за пределы экрана
        # Добавляем небольшое смещение, чтобы окно не появлялось прямо под курсором
        offset_x, offset_y = 10, 10
        
        # Вычисляем начальную позицию
        x = cursor_pos.x() + offset_x
        y = cursor_pos.y() + offset_y
        
        # Проверяем, чтобы окно не выходило за правую или нижнюю границу экрана
        if x + self.width() > screen_geometry.right():
            x = screen_geometry.right() - self.width() - offset_x
        
        if y + self.height() > screen_geometry.bottom():
            y = screen_geometry.bottom() - self.height() - offset_y
        
        # Проверяем, чтобы окно не выходило за левую или верхнюю границу экрана
        if x < screen_geometry.left():
            x = screen_geometry.left() + offset_x
        
        if y < screen_geometry.top():
            y = screen_geometry.top() + offset_y
        
        print(f"Placing popup at: x={x}, y={y} on screen {target_screen.name()}")
        
        self.move(x, y)
        print("Window moved to position")
        self.show()
        print("Window shown")
        self.activateWindow()
        print("Window activated")
        self.raise_()
        print("Window raised")
        
        # Дополнительно используем Windows API для принудительного размещения окна поверх всех
        if ctypes and sys.platform == "win32":
            try:
                # Константы для SetWindowPos
                HWND_TOPMOST = -1
                SWP_NOSIZE = 0x0001
                SWP_NOMOVE = 0x0002
                SWP_SHOWWINDOW = 0x0040
                
                # Получаем хэндл окна
                hwnd = self.winId().__int__()
                
                # Принудительно устанавливаем окно поверх всех остальных
                ctypes.windll.user32.SetWindowPos(
                    hwnd, HWND_TOPMOST,
                    0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
                )
                print("Windows API: SetWindowPos succeeded")
            except Exception as e:
                print(f"Windows API call failed: {e}")
        
        time.sleep(0.1)
        QApplication.processEvents()
        print("Events processed")
        
        # Устанавливаем фокус на список
        self.text_list.setFocus()
        
    def show(self):
        print("TextSelectionPopup.show() called")
        super(TextSelectionPopup, self).show()
        print("TextSelectionPopup.show() completed")
        

        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.folder_stack:
                self.folder_stack.pop()
                self.update_text_list()
            else:
                self.close()
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            current_item = self.text_list.currentItem()
            if current_item:
                self.on_text_selected(current_item)
        elif event.key() == Qt.Key.Key_Up:
            current_row = self.text_list.currentRow()
            if current_row > 0:
                self.text_list.setCurrentRow(current_row - 1)
        elif event.key() == Qt.Key.Key_Down:
            current_row = self.text_list.currentRow()
            if current_row < self.text_list.count() - 1:
                self.text_list.setCurrentRow(current_row + 1)
        else:
            super(TextSelectionPopup, self).keyPressEvent(event)
            
    def focusOutEvent(self, event):
        # Закрываем окно при потере фокуса
        self.close()
        super(TextSelectionPopup, self).focusOutEvent(event)
        
    def changeEvent(self, event):
        # Обрабатываем изменение активации окна
        if event.type() == QEvent.ActivationChange:
            if not self.isActiveWindow():
                self.hide()  # Скрываем окно при потере активации
        super(TextSelectionPopup, self).changeEvent(event)

    def event(self, event):
        # Закрываем окно при потере активного состояния (деактивации)
        if event.type() == QEvent.WindowDeactivate:
            self.close()
            return True
        return super(TextSelectionPopup, self).event(event) 