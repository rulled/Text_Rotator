import time
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QApplication, QListWidgetItem
from PyQt5.QtCore import Qt, QPoint, QEvent
from PyQt5.QtGui import QCursor
from functools import partial

import sys
import os

class TextSelectionPopup(QWidget):
    def __init__(self, data, callback, parent=None):
        super(TextSelectionPopup, self).__init__(parent, 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.Popup)
        self.data = data
        self.callback = callback
        self.is_dark_theme = self.detect_dark_theme()
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
        self._add_items_to_list(self.data)
        # Adjust size whenever the list content changes
        self.adjust_popup_size()
        
    def adjust_popup_size(self):
        """Adjusts the popup height based on the number of items in the list."""
        MAX_VISIBLE_ITEMS = 15 # Max items before scrollbar appears
        MIN_VISIBLE_ITEMS = 1 # Minimum items to show
        # Estimate item height (adjust if needed based on font/padding)
        # Use sizeHintForRow(0) if items are uniform, otherwise estimate
        item_height = 35 # Approximate height including padding/border
        try:
            if self.text_list.count() > 0:
                 # Try to get a more accurate height from the first item
                 hint = self.text_list.sizeHintForRow(0)
                 if hint > 5: # Basic sanity check
                     item_height = hint
        except Exception: 
             pass # Stick with the default estimate
        
        # Calculate margins and borders (approximate)
        # Consider layout margins, widget border, list padding
        layout_margins = self.layout().contentsMargins()
        widget_border = 2 * 2 # From QWidget border: 2px * 2 sides
        list_padding = 5 * 2 # From QListWidget padding: 5px * 2 (top/bottom)
        vertical_margins = layout_margins.top() + layout_margins.bottom() + widget_border + list_padding
        
        num_items = self.text_list.count()
        if num_items == 0:
             ideal_list_height = item_height * MIN_VISIBLE_ITEMS
        else:
            ideal_list_height = item_height * num_items
            
        max_list_height = item_height * MAX_VISIBLE_ITEMS
        
        target_list_height = max(item_height * MIN_VISIBLE_ITEMS, 
                                 min(ideal_list_height, max_list_height))
        
        # Set the list widget's height bounds
        self.text_list.setMinimumHeight(item_height * MIN_VISIBLE_ITEMS)
        self.text_list.setMaximumHeight(target_list_height)
        self.text_list.setFixedHeight(target_list_height) # Force the height
        
        # Adjust the overall popup window height
        # Use sizeHint which should now be constrained by list widget's height
        # Add a little extra padding just in case
        extra_padding = 5 
        total_height = self.text_list.height() + vertical_margins + extra_padding
        # Keep width reasonable, maybe fixed or based on content width?
        # Let's keep width fixed for now
        current_width = self.width() if self.width() > 100 else 400 # Use current or default
        self.setFixedSize(current_width, total_height)
        print(f"Adjusted popup size: {num_items} items, List H={target_list_height}, Total H={total_height}")

    def _add_items_to_list(self, items, level=0):
        for item in items:
            if isinstance(item, str):
                # Текст
                preview = item.replace('\n', ' ')
                preview = preview[:50] + '...' if len(preview) > 50 else preview
                list_item = QListWidgetItem('  ' * level + preview)
                list_item.setData(Qt.UserRole, item)
                self.text_list.addItem(list_item)
            elif isinstance(item, dict) and item.get('type') == 'folder':
                # Папка
                folder_name = item.get('name', 'Безымянная папка')
                list_item = QListWidgetItem('  ' * level + f"📁 {folder_name}")
                list_item.setData(Qt.UserRole, None)  # Папки не имеют текста для вставки
                list_item.setData(Qt.UserRole + 1, 'folder')  # Помечаем как папку
                self.text_list.addItem(list_item)
                # Рекурсивно добавляем содержимое папки
                self._add_items_to_list(item.get('items', []), level + 1)
    
    def on_text_selected(self, item):
        text = item.data(Qt.UserRole)
        if text is not None:  # Если это не папка
            self.hide()  # Используем hide вместо close
            time.sleep(0.3)
            self.callback(text)
        
    def show_at_cursor(self):
        print("TextSelectionPopup.show_at_cursor() called")
        cursor_pos = QCursor.pos()
        print(f"Cursor position: {cursor_pos}")
        
        # Получаем размеры экрана
        screen = QApplication.primaryScreen().geometry()
        
        # Вычисляем позицию так, чтобы окно не выходило за пределы экрана
        x = min(cursor_pos.x() + 10, screen.width() - self.width() - 10)
        y = min(cursor_pos.y() + 10, screen.height() - self.height() - 10)
        
        self.move(x, y)
        print("Window moved to position")
        self.show()
        print("Window shown")
        self.activateWindow()
        print("Window activated")
        self.raise_()
        print("Window raised")
        time.sleep(0.1)
        QApplication.processEvents()
        print("Events processed")
        
        # Устанавливаем фокус на список
        self.text_list.setFocus()
        
    def show(self):
        print("TextSelectionPopup.show() called")
        super(TextSelectionPopup, self).show()
        print("TextSelectionPopup.show() completed")
        
    def hide(self):
        print("TextSelectionPopup.hide() called")
        super(TextSelectionPopup, self).hide()
        print("TextSelectionPopup.hide() completed")
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()  # Используем hide вместо close
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            current_item = self.text_list.currentItem()
            if current_item:
                item_type = current_item.data(Qt.UserRole + 1)
                if item_type == 'folder':
                    # TODO: Implement folder expansion/collapse on Enter?
                    pass # Do nothing for now
                elif current_item.data(Qt.UserRole) is not None:
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
        # Скрываем окно при потере фокуса
        self.hide()  # Используем hide вместо close
        # Вызываем родительский метод
        super(TextSelectionPopup, self).focusOutEvent(event)
        
    def changeEvent(self, event):
        # Обрабатываем изменение активации окна
        if event.type() == QEvent.ActivationChange:
            if not self.isActiveWindow():
                self.hide()  # Скрываем окно при потере активации
        super(TextSelectionPopup, self).changeEvent(event)

    def event(self, event):
        # Скрываем окно при потере активного состояния (деактивации)
        if event.type() == QEvent.WindowDeactivate:
            self.hide()
            return True
        return super(TextSelectionPopup, self).event(event) 