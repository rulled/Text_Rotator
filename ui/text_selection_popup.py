import time
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QListWidget, QApplication, 
                             QListWidgetItem, QGraphicsDropShadowEffect) # Removed QPushButton, QInputDialog
from PyQt5.QtCore import Qt, QPoint, QEvent, QPropertyAnimation, QEasingCurve, QRect # Добавили для анимации
from PyQt5.QtGui import QCursor, QColor # Добавили QColor для тени

import sys
import os

# Импортируем Windows API для размещения окна на переднем плане на уровне системы
if sys.platform == "win32":
    try:
        import ctypes
        # from ctypes import wintypes # wintypes не используется напрямую здесь
    except ImportError:
        ctypes = None
else:
    ctypes = None

class TextSelectionPopup(QDialog):
    def __init__(self, data, callback, parent=None):
        super(TextSelectionPopup, self).__init__(parent, 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint)
        
        self.setAttribute(Qt.WA_TranslucentBackground) # Важно для тени и анимации прозрачности
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self.data = data
        self.callback = callback
        self.is_dark_theme = self.detect_dark_theme()
        self.folder_stack = []
        
        self.init_ui()
        self.init_animations() # Инициализируем анимации
        self.apply_shadow()    # Применяем тень

    def detect_dark_theme(self):
        if hasattr(self.parent(), "is_dark_theme"):
            return self.parent().is_dark_theme
        else:
            try:
                if sys.platform == "win32":
                    import winreg
                    registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                    reg_key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                    is_light_theme = int(winreg.QueryValueEx(reg_key, "AppsUseLightTheme")[0])
                    return is_light_theme == 0
                return False
            except Exception as e:
                print(f"Ошибка определения темы для popup: {e}")
                return False
        
    def init_ui(self):
        self.setWindowTitle('Select Text')
        
        # Основной виджет-контейнер, к которому будут применяться стили (фон, граница)
        # Это позволит тени быть за пределами видимой части окна.
        self.container_widget = QListWidget() # Используем QListWidget как контейнер
        self.container_widget.setObjectName("popupContainer") # Для стилизации
        
        # Применяем стили в зависимости от темы
        border_radius_val = "8px" # Немного увеличим радиус
        border_color_light = "rgba(0, 0, 0, 0.1)" # Очень светлая граница для светлой темы
        border_color_dark = "rgba(255, 255, 255, 0.1)" # Очень светлая граница для темной темы

        # Общие стили для QListWidget (он же контейнер)
        container_style_sheet = f"""
            QListWidget#popupContainer {{
                border: 1px solid {border_color_dark if self.is_dark_theme else border_color_light};
                border-radius: {border_radius_val};
                font-family: 'Inter', 'San Francisco', sans-serif; /* Добавим San Francisco как fallback */
                font-size: 14px;
                font-weight: 400;
                padding: 5px; /* Внутренний отступ для элементов списка */
                background-color: {"#2C2C2E" if self.is_dark_theme else "#F2F2F7"}; /* Типичные цвета фона Apple */
                color: {"#FFFFFF" if self.is_dark_theme else "#000000"};
            }}
            QListWidget#popupContainer::item {{
                padding: 10px 8px; /* Увеличим вертикальный padding */
                border-bottom: 1px solid {"#3A3A3C" if self.is_dark_theme else "#E5E5EA"}; /* Более мягкие разделители */
            }}
            QListWidget#popupContainer::item:last-child {{
                border-bottom: none; /* Убираем разделитель у последнего элемента */
            }}
            QListWidget#popupContainer::item:selected {{
                background-color: {"#3A3A3C" if self.is_dark_theme else "#E5E5EA"}; /* Более мягкий цвет выделения */
                color: {"#FFFFFF" if self.is_dark_theme else "#000000"};
                border-radius: 4px; /* Небольшое скругление для выделенного элемента */
            }}
            QListWidget#popupContainer::item:hover {{
                background-color: {"#48484A" if self.is_dark_theme else "#DADADE"};
                border-radius: 4px;
            }}
            QListWidget#popupContainer::item[type="folder"] {{ /* Этот селектор может не работать напрямую, лучше через setData */
                font-weight: 500;
                color: {"#0A84FF" if not self.is_dark_theme else "#0A84FF"}; /* Apple Blue */
            }}
             QScrollBar:vertical {{
                 border: none;
                 background: transparent; 
                 width: 8px;
                 margin: 0px 0px 0px 0px;
             }}
             QScrollBar::handle:vertical {{
                 background: {"#555555" if self.is_dark_theme else "#CCCCCC"};
                 min-height: 25px;
                 border-radius: 4px;
             }}
             QScrollBar::handle:vertical:hover {{
                 background: {"#666666" if self.is_dark_theme else "#BBBBBB"};
             }}
             QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
             QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical,
             QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                 border: none; background: none; height: 0px; width: 0px;
             }}
        """
        self.container_widget.setStyleSheet(container_style_sheet)
        
        layout = QVBoxLayout(self) # Главный layout самого QDialog
        layout.setContentsMargins(10, 10, 10, 10) # Отступы для тени!
        layout.addWidget(self.container_widget)
        
        self.text_list = self.container_widget # Теперь self.text_list это наш контейнер
        self.update_text_list() # Это вызовет self.text_list.clear() и т.д.
        self.text_list.itemClicked.connect(self.on_text_selected)
        
        self.text_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.text_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.adjust_popup_size()

    def init_animations(self):
        # Анимация прозрачности
        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(150) # Быстрая анимация
        self.opacity_anim.setEasingCurve(QEasingCurve.OutCubic)

        # Анимация геометрии для эффекта "pop"
        self.geometry_anim = QPropertyAnimation(self, b"geometry")
        self.geometry_anim.setDuration(180) # Чуть дольше для более плавного "pop"
        self.geometry_anim.setEasingCurve(QEasingCurve.OutCubic)

    def apply_shadow(self):
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15) # Радиус размытия
        self.shadow.setXOffset(0)     # Смещение по X
        self.shadow.setYOffset(2)     # Небольшое смещение по Y для ощущения "приподнятости"
        shadow_color_alpha = 70 if self.is_dark_theme else 50 # Прозрачность тени
        self.shadow.setColor(QColor(0, 0, 0, shadow_color_alpha)) 
        self.setGraphicsEffect(self.shadow)
        
    def update_text_list(self):
        self.text_list.clear()
        # current_items_data = [] # Not strictly needed here anymore

        if not self.folder_stack: # Мы в корневом уровне
            # В корне отображаем только папки
            for item_data_obj in self.data: # self.data это данные из TextRotator (data_popup)
                if isinstance(item_data_obj, dict) and item_data_obj.get('type') == 'folder':
                    folder_name = item_data_obj.get('name', 'Безымянная папка')
                    list_item = QListWidgetItem(f"📁 {folder_name}")
                    list_item.setData(Qt.UserRole, None) # Для папок сам текст не нужен
                    list_item.setData(Qt.UserRole + 1, 'folder') # Тип
                    list_item.setData(Qt.UserRole + 2, item_data_obj) # Сам объект папки
                    self.text_list.addItem(list_item)
        else: # Мы внутри папки
            back_item = QListWidgetItem("← Назад к списку папок")
            back_item.setData(Qt.UserRole, None)
            back_item.setData(Qt.UserRole + 1, 'back')
            self.text_list.addItem(back_item)
            
            current_folder_obj = self.folder_stack[-1]
            current_items_data = current_folder_obj.get('items', [])
            # Внутри папки отображаем только текстовые элементы
            for item_data_obj in current_items_data:
                if isinstance(item_data_obj, str): # Это текстовый элемент
                    preview = item_data_obj.replace('\n', ' ')
                    preview = preview[:50] + '...' if len(preview) > 50 else preview
                    list_item = QListWidgetItem(preview)
                    list_item.setData(Qt.UserRole, item_data_obj) # Оригинальный текст
                    list_item.setData(Qt.UserRole + 1, 'text') # Тип
                    self.text_list.addItem(list_item)
        
        self.adjust_popup_size()

    def adjust_popup_size(self):
        screen = QApplication.primaryScreen()
        screen_height = screen.availableGeometry().height() # Используем availableGeometry
        
        min_items_visible = 3
        max_items_visible = 10 # Максимум элементов без прокрутки (примерно)

        # Оценка высоты одного элемента (включая padding)
        # Если список пуст, берем дефолтное значение
        item_height_estimate = 40 # (10px padding-top + 10px padding-bottom + ~20px text)
        if self.text_list.count() > 0:
            try:
                # Пытаемся получить реальную высоту первого элемента
                # sizeHintForRow может быть неточной без делегата, но для оценки сойдет
                hint = self.text_list.sizeHintForRow(0) 
                if hint > 0 : item_height_estimate = hint + 2 # +2 для border
            except Exception:
                pass # Используем estimate

        num_items = self.text_list.count()
        
        # Высота содержимого списка
        content_height = item_height_estimate * num_items
        
        # Внутренние отступы самого QListWidget (из CSS padding: 5px)
        list_widget_vertical_padding = 5 * 2 
        
        # Идеальная высота для QListWidget
        ideal_list_height = content_height + list_widget_vertical_padding
        
        # Ограничиваем высоту списка
        min_h = item_height_estimate * min_items_visible + list_widget_vertical_padding
        max_h = min(screen_height * 0.6, item_height_estimate * max_items_visible + list_widget_vertical_padding) # Не более 60% экрана
        
        target_list_height = max(min_h, min(ideal_list_height, max_h))
        
        self.text_list.setMinimumHeight(int(target_list_height))
        self.text_list.setMaximumHeight(int(target_list_height))
        # self.text_list.setFixedHeight(int(target_list_height)) # Можно и так

        # Отступы самого QDialog (где лежит тень)
        dialog_margins = self.layout().contentsMargins()
        dialog_vertical_margins = dialog_margins.top() + dialog_margins.bottom()
        
        total_height = int(target_list_height + dialog_vertical_margins)
        current_width = self.width() if self.width() > 100 else 400 # Оставляем ширину или дефолт
        
        # Устанавливаем размер всего QDialog
        self.setFixedSize(current_width, total_height)
        print(f"Adjusted popup size: {num_items} items. ItemH_est: {item_height_estimate}. ListH: {target_list_height}. TotalH: {total_height}")

    def on_text_selected(self, item):
        item_type = item.data(Qt.UserRole + 1)
        if item_type == 'folder':
            folder_obj = item.data(Qt.UserRole + 2)
            self.folder_stack.append(folder_obj)
            self.update_text_list()
        elif item_type == 'back':
            if self.folder_stack:
                self.folder_stack.pop()
                self.update_text_list()
        elif item_type == 'text' and item.data(Qt.UserRole) is not None:
            selected_text = item.data(Qt.UserRole)
            self.close_with_animation(selected_text) # Закрываем с анимацией
        
    def show_at_cursor(self):
        print("TextSelectionPopup.show_at_cursor() called")
        cursor_pos = QCursor.pos()
        
        screens = QApplication.screens()
        target_screen = QApplication.screenAt(cursor_pos) if QApplication.screenAt(cursor_pos) else QApplication.primaryScreen()
        screen_geometry = target_screen.availableGeometry() # Используем availableGeometry
        
        # self.adjust_popup_size() # Убедимся, что размер актуален перед расчетом позиции

        # Начальная позиция для анимации (чуть ниже и меньше)
        # Важно: self.width() и self.height() тут уже должны быть финальными (после adjust_popup_size)
        final_width = self.width()
        final_height = self.height()

        offset_x, offset_y = 10, 10
        
        x = cursor_pos.x() + offset_x
        y = cursor_pos.y() + offset_y
        
        if x + final_width > screen_geometry.right():
            x = screen_geometry.right() - final_width
        if y + final_height > screen_geometry.bottom():
            y = screen_geometry.bottom() - final_height
        if x < screen_geometry.left():
            x = screen_geometry.left()
        if y < screen_geometry.top():
            y = screen_geometry.top()

        final_rect = QRect(x, y, final_width, final_height)

        # Начальная геометрия для "pop" анимации
        # Появится немного ниже и "вырастет" вверх
        pop_offset_y = 15 
        start_rect = QRect(x, y + pop_offset_y, final_width, final_height - pop_offset_y)
        
        # Устанавливаем начальное состояние для анимации
        self.setGeometry(start_rect)
        self.setWindowOpacity(0.0)

        super(TextSelectionPopup, self).show() # Показываем окно (оно будет невидимым и в start_rect)
        
        # Запускаем анимации
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.start()

        self.geometry_anim.setStartValue(start_rect)
        self.geometry_anim.setEndValue(final_rect)
        self.geometry_anim.start()
        
        self.activateWindow()
        self.raise_()
        
        if ctypes and sys.platform == "win32":
            try:
                HWND_TOPMOST = -1
                SWP_NOSIZE = 0x0001
                SWP_NOMOVE = 0x0002
                SWP_SHOWWINDOW = 0x0040
                hwnd = self.winId().__int__()
                ctypes.windll.user32.SetWindowPos(
                    hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
                )
            except Exception as e:
                print(f"Windows API call failed: {e}")
        
        QApplication.processEvents() # Обработать события, чтобы анимация началась плавно
        self.text_list.setFocus()

    def close_with_animation(self, selected_value=None):
        # Можно добавить анимацию исчезновения, если очень хочется,
        # но обычно для таких pop-up окон это излишне.
        # Простое закрытие:
        if self.opacity_anim.state() == QPropertyAnimation.Running:
            self.opacity_anim.stop()
        if self.geometry_anim.state() == QPropertyAnimation.Running:
            self.geometry_anim.stop()
        
        self.close() # Это вызовет deleteLater из-за WA_DeleteOnClose
        if selected_value is not None:
            # Небольшая задержка перед callback, чтобы окно успело исчезнуть
            # QTimer.singleShot(50, lambda: self.callback(selected_value))
            # Однако, если окно удаляется, callback должен быть вызван до его полного удаления
            # или родительский объект должен быть устойчив к этому.
            # WA_DeleteOnClose может вызвать проблемы, если callback обращается к popup.
            # Лучше вызвать callback немедленно, а закрытие произойдет.
            self.callback(selected_value)


    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.folder_stack:
                self.folder_stack.pop()
                self.update_text_list()
            else:
                self.close_with_animation() # Закрываем с анимацией (или без, если не реализована на закрытие)
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            current_item = self.text_list.currentItem()
            if current_item:
                self.on_text_selected(current_item) # on_text_selected вызовет close_with_animation
        elif event.key() == Qt.Key_Up:
            current_row = self.text_list.currentRow()
            if current_row > 0:
                self.text_list.setCurrentRow(current_row - 1)
        elif event.key() == Qt.Key_Down:
            current_row = self.text_list.currentRow()
            if current_row < self.text_list.count() - 1:
                self.text_list.setCurrentRow(current_row + 1)
        else:
            super(TextSelectionPopup, self).keyPressEvent(event)
            
    def focusOutEvent(self, event):
        # Закрываем окно при потере фокуса, если это не связано с дочерними элементами
        if not self.isActiveWindow() and event.reason() != Qt.FocusReason.PopupFocusReason:
             print(f"FocusOutEvent, reason: {event.reason()}. Closing popup.")
             self.close_with_animation()
        super(TextSelectionPopup, self).focusOutEvent(event)
        
    def event(self, event):
        if event.type() == QEvent.WindowDeactivate:
            # Этот обработчик более надежен для закрытия при потере фокуса
            print("WindowDeactivate event. Closing popup.")
            self.close_with_animation()
            return True # Событие обработано
        return super(TextSelectionPopup, self).event(event)

    # show() не нужен, так как мы используем show_at_cursor()
    # def show(self):
    #     super(TextSelectionPopup, self).show()