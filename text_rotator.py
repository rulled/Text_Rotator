import sys
import json
import os
import time
import copy

# --- Application Version ---
__version__ = "1.0.0" # Example version
# -------------------------

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import (QSystemTrayIcon, QMenu, QAction, QInputDialog, 
                             QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QListWidget, QPlainTextEdit, QLineEdit, QMessageBox,
                             QAbstractItemView, QWidget, QDialog, QCheckBox)
from PyQt5.QtCore import Qt, QPoint, QThread, pyqtSignal, QPropertyAnimation, QRect, QEasingCurve, QVariantAnimation, QAbstractAnimation, QEvent
from PyQt5.QtGui import QIcon, QFont, QPalette, QMouseEvent, QCursor, QColor, QPainter, QPen, QBrush
import keyboard
import pyperclip
from functools import partial

from models.hotkey_listener import HotkeyListener
from ui.text_selection_popup import TextSelectionPopup
from ui.folder_edit_dialog import FolderEditDialog
from ui.hotkey_recorder_dialog import HotkeyRecorderDialog
from ui.settings_dialog import SettingsDialog # Import the new dialog
from utils.resource_path import resource_path

def is_system_dark_theme():
    """Определяет, активна ли в системе темная тема."""
    try:
        # Проверка для Windows
        if sys.platform == "win32":
            import winreg
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            reg_key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            # AppsUseLightTheme = 0 означает тёмный режим
            is_light_theme = int(winreg.QueryValueEx(reg_key, "AppsUseLightTheme")[0])
            return is_light_theme == 0
        # Проверка для Linux
        elif sys.platform == "linux":
            # Здесь можно добавить логику для разных DE (GNOME, KDE и т.д.)
            return False
        # Проверка для macOS
        elif sys.platform == "darwin":
            # Требуется дополнительный модуль для macOS
            return False
        return False
    except Exception as e:
        print(f"Ошибка определения темы системы: {e}")
        return False

class MacOSButton(QPushButton):
    """Кнопка в стиле macOS с эффектом при наведении."""
    
    def __init__(self, color, hover_icon=None, parent=None):
        super(MacOSButton, self).__init__(parent)
        self.setFixedSize(14, 14)
        self.setFlat(True)
        self.base_color = color
        
        # Определяем цвет при наведении (немного темнее базового)
        self.hover_color = self._darken_color(color, 0.85)  # 15% темнее
        
        # Текущий цвет (для анимации)
        self.current_color = color
        
        # Иконка для состояния наведения - больше не используется
        self.hover_icon = None
        self.has_icon = False
        self.is_hovered = False
        
        # Для анимации прозрачности - больше не используется 
        self._opacity = 0.0
        
        # Создаем анимации для цвета
        self.color_in_animation = QVariantAnimation()
        self.color_in_animation.setDuration(180)
        self.color_in_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.color_in_animation.valueChanged.connect(self._update_color)
        
        self.color_out_animation = QVariantAnimation()
        self.color_out_animation.setDuration(180)
        self.color_out_animation.setEasingCurve(QEasingCurve.InCubic)
        self.color_out_animation.valueChanged.connect(self._update_color)
        
        # Устанавливаем стартовые и конечные значения для анимаций цвета
        self._setup_color_animations()
        
        # Стиль по умолчанию - убедимся, что кнопки всегда видны
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color}; 
                border-radius: 7px; 
                border: 1px solid rgba(0, 0, 0, 0.15);
            }}
        """)
    
    def _brighten_color(self, color_hex, factor):
        """Осветляет HEX-цвет на указанный коэффициент."""
        # Конвертируем HEX в RGB
        color = QColor(color_hex)
        h, s, v, a = color.getHsvF()
        
        # Увеличиваем яркость (не более 1.0)
        v = min(v * factor, 1.0)
        
        # Создаем новый цвет
        new_color = QColor.fromHsvF(h, s, v, a)
        return new_color.name()
    
    def _darken_color(self, color_hex, factor):
        """Затемняет HEX-цвет на указанный коэффициент."""
        # Конвертируем HEX в RGB
        color = QColor(color_hex)
        h, s, v, a = color.getHsvF()
        
        # Уменьшаем яркость (множитель меньше 1.0)
        v = max(v * factor, 0.0)
        
        # Создаем новый цвет
        new_color = QColor.fromHsvF(h, s, v, a)
        return new_color.name()
        
    def _setup_color_animations(self):
        """Настраивает анимации цвета."""
        # Используем QColor для анимации
        base_color = QColor(self.base_color)
        hover_color = QColor(self.hover_color)
        
        # Настраиваем анимацию появления (от базового к подсвеченному)
        self.color_in_animation.setStartValue(base_color)
        self.color_in_animation.setEndValue(hover_color)
        
        # Настраиваем анимацию исчезновения (от подсвеченного к базовому)
        self.color_out_animation.setStartValue(hover_color)
        self.color_out_animation.setEndValue(base_color)
    
    def _update_color(self, color_value):
        """Обновляет цвет кнопки во время анимации."""
        self.current_color = color_value.name()
        self._apply_styles()
    
    def _update_opacity(self, value):
        """Обновляет прозрачность иконки во время анимации."""
        self._opacity = value
        self.opacity_effect.setOpacity(value)
        
        # Обновляем иконку при необходимости
        if self.has_icon:
            if self._opacity > 0 and not self.icon():
                self.setIcon(self.hover_icon)
                self.setIconSize(QtCore.QSize(10, 10))
            elif self._opacity == 0 and self.icon():
                self.setIcon(QIcon())
        
        self.update()
    
    def _apply_styles(self):
        """Применяет текущие стили к кнопке."""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.current_color}; 
                border-radius: 7px; 
                border: none;
            }}
        """)
    
    def enterEvent(self, event):
        """Срабатывает при наведении курсора."""
        self.is_hovered = True
        
        # Останавливаем анимации выхода, если они запущены
        if self.color_out_animation.state() == QVariantAnimation.Running:
            self.color_out_animation.stop()
        
        # Запускаем анимации входа только для цвета
        self.color_in_animation.start()
        
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Срабатывает при уходе курсора."""
        self.is_hovered = False
        
        # Останавливаем анимации входа, если они запущены
        if self.color_in_animation.state() == QVariantAnimation.Running:
            self.color_in_animation.stop()
        
        # Запускаем анимации выхода только для цвета
        self.color_out_animation.start()
        
        super().leaveEvent(event)
    
    def paintEvent(self, event):
        """Переопределяем отрисовку, чтобы добавить эффекты."""
        super().paintEvent(event)
        # Дополнительная логика отрисовки при необходимости

class CustomTitleBar(QWidget):
    """Кастомный заголовок окна в стиле macOS."""
    
    def __init__(self, parent=None):
        super(CustomTitleBar, self).__init__(parent)
        self.parent = parent
        self.is_dark_theme = parent.is_dark_theme if hasattr(parent, 'is_dark_theme') else False
        self.setFixedHeight(32)
        self.moving = False
        self.start_point = None
        
        # Создаем кнопки
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, 0)
        self.layout.setSpacing(6)
        
        # Заголовок окна - теперь он слева
        self.title_label = QLabel(self.parent.windowTitle() if self.parent else "")
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.layout.addWidget(self.title_label, 1)  # 1 - stretch factor
        
        # Кнопки управления окном - теперь они справа (в стиле Windows)
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(8)
        
        # Создаем кнопки с базовым цветом без иконок
        # Порядок кнопок в стиле Windows: сворачивание, разворачивание, закрытие
        self.btn_minimize = MacOSButton("#FEBC2E")
        self.btn_maximize = MacOSButton("#28C840")
        self.btn_close = MacOSButton("#FF5F57")
        
        # Добавляем тонкую границу для лучшей видимости
        for btn in [self.btn_close, self.btn_minimize, self.btn_maximize]:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn.current_color};
                    border-radius: 7px;
                    border: 1px solid rgba(0, 0, 0, 0.15);
                }}
            """)
        
        # Добавляем кнопки в нужном порядке для Windows (слева направо)
        buttons_layout.addWidget(self.btn_minimize)
        buttons_layout.addWidget(self.btn_maximize)
        buttons_layout.addWidget(self.btn_close)
            
        self.btn_close.clicked.connect(self.close_window)
        self.btn_minimize.clicked.connect(self.minimize_window)
        self.btn_maximize.clicked.connect(self.maximize_window)
        
        # Добавляем контейнер с кнопками в основной макет (справа)
        self.layout.addWidget(buttons_container)
        
        self.apply_theme()
        
    def apply_theme(self):
        """Применяет стиль в зависимости от темы."""
        if self.is_dark_theme:
            # Темная тема
            self.setStyleSheet("""
                CustomTitleBar {
                    background-color: #1E1E1E;
                    color: #FFFFFF;
                }
                QLabel {
                    color: #FFFFFF;
                    font-family: 'Inter';
                    font-size: 14px;
                    font-weight: 500;
                }
            """)
            
            # Обновляем стили для кнопок с сохранением их базовых цветов и добавлением рамки
            for btn, color in [(self.btn_close, "#FF5F57"), 
                              (self.btn_minimize, "#FEBC2E"), 
                              (self.btn_maximize, "#28C840")]:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color};
                        border-radius: 7px;
                        border: 1px solid rgba(0, 0, 0, 0.15);
                    }}
                """)
        else:
            # Светлая тема
            self.setStyleSheet("""
                CustomTitleBar {
                    background-color: #F0F0F0;
                    color: #000000;
                }
                QLabel {
                    color: #000000;
                    font-family: 'Inter';
                    font-size: 14px;
                    font-weight: 500;
                }
            """)
            
            # Обновляем стили для кнопок с сохранением их базовых цветов и добавлением рамки
            for btn, color in [(self.btn_close, "#FF5F57"), 
                              (self.btn_minimize, "#FEBC2E"), 
                              (self.btn_maximize, "#28C840")]:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color};
                        border-radius: 7px;
                        border: 1px solid rgba(0, 0, 0, 0.15);
                    }}
                """)
    
    def update_theme(self, is_dark):
        """Обновляет тему заголовка."""
        self.is_dark_theme = is_dark
        self.apply_theme()
    
    def mousePressEvent(self, event):
        """Обработка нажатия мыши для начала перемещения окна."""
        if event.button() == Qt.LeftButton:
            self.moving = True
            self.start_point = event.globalPos()
    
    def mouseMoveEvent(self, event):
        """Обработка движения мыши для перемещения окна."""
        if self.moving and self.start_point:
            delta = QPoint(event.globalPos() - self.start_point)
            self.parent.move(self.parent.x() + delta.x(), self.parent.y() + delta.y())
            self.start_point = event.globalPos()
    
    def mouseReleaseEvent(self, event):
        """Обработка отпускания кнопки мыши."""
        self.moving = False
        self.start_point = None
    
    def mouseDoubleClickEvent(self, event):
        """Двойной клик по заголовку - разворачивает/сворачивает окно."""
        self.maximize_window()
    
    def close_window(self):
        """Закрывает окно."""
        self.parent.close()
    
    def minimize_window(self):
        """Сворачивает окно."""
        self.parent.showMinimized()
    
    def maximize_window(self):
        """Разворачивает/восстанавливает окно."""
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()

class ResizableFramelessWindow(QtWidgets.QMainWindow):
    """Окно без рамки с возможностью изменения размера."""
    
    def __init__(self):
        super(ResizableFramelessWindow, self).__init__()
        # Убираем стандартную рамку окна
        self.setWindowFlag(Qt.FramelessWindowHint)
        
        # Настройки отображения
        self.setMinimumSize(400, 300)
        self.draggable = True
        self.resizable = True
        self.border_width = 8  # Увеличиваем ширину границы для изменения размера
        
        # Флаги для определения области изменения размера
        self.left_resize = False
        self.right_resize = False
        self.top_resize = False
        self.bottom_resize = False
        
        # Для перемещения окна
        self.dragging = False
        self.drag_position = None
        
        # Установка атрибута для лучшей обработки мыши
        self.setAttribute(Qt.WA_Hover, True)
    
    def mousePressEvent(self, event):
        """Обработка нажатия кнопки мыши."""
        if event.button() == Qt.LeftButton:
            # Определяем, находится ли курсор в области изменения размера
            cursor_position = event.pos()
            self.update_cursor_shape(cursor_position)
            
            # Если курсор находится в области изменения размера
            if self.left_resize or self.right_resize or self.top_resize or self.bottom_resize:
                self.dragging = False
                self.draggable = False
            else:
                # Для перемещения окна
                self.dragging = True
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
        
        super(ResizableFramelessWindow, self).mousePressEvent(event)
    
    def update_cursor_shape(self, pos):
        """Обновляет флаги изменения размера и форму курсора."""
        rect = self.rect()
        
        # Сбрасываем флаги
        self.left_resize = self.right_resize = self.top_resize = self.bottom_resize = False
        
        # Левая граница
        if abs(pos.x()) <= self.border_width:
            self.left_resize = True
        
        # Правая граница
        if abs(rect.width() - pos.x()) <= self.border_width:
            self.right_resize = True
        
        # Верхняя граница
        if abs(pos.y()) <= self.border_width:
            self.top_resize = True
        
        # Нижняя граница
        if abs(rect.height() - pos.y()) <= self.border_width:
            self.bottom_resize = True
        
        # Устанавливаем соответствующую форму курсора
        if (self.top_resize and self.left_resize) or (self.bottom_resize and self.right_resize):
            self.setCursor(Qt.SizeFDiagCursor)
        elif (self.top_resize and self.right_resize) or (self.bottom_resize and self.left_resize):
            self.setCursor(Qt.SizeBDiagCursor)
        elif self.top_resize or self.bottom_resize:
            self.setCursor(Qt.SizeVerCursor)
        elif self.left_resize or self.right_resize:
            self.setCursor(Qt.SizeHorCursor)
        elif not self.dragging:
            self.setCursor(Qt.ArrowCursor)
    
    def mouseMoveEvent(self, event):
        """Обработка движения мыши."""
        cursor_position = event.pos()
        
        # Если изменяем размер
        if event.buttons() == Qt.LeftButton and (self.left_resize or self.right_resize or 
                                                self.top_resize or self.bottom_resize):
            # Текущая геометрия окна
            rect = self.geometry()
            
            # Новая геометрия в зависимости от направления изменения размера
            if self.left_resize:
                diff = event.globalPos().x() - rect.x()
                if rect.width() - diff >= self.minimumWidth():
                    rect.setX(event.globalPos().x())
                    rect.setWidth(rect.width() - diff)
            
            if self.right_resize:
                rect.setWidth(event.globalPos().x() - rect.x())
            
            if self.top_resize:
                diff = event.globalPos().y() - rect.y()
                if rect.height() - diff >= self.minimumHeight():
                    rect.setY(event.globalPos().y())
                    rect.setHeight(rect.height() - diff)
            
            if self.bottom_resize:
                rect.setHeight(event.globalPos().y() - rect.y())
            
            # Применяем новую геометрию
            if rect.width() >= self.minimumWidth() and rect.height() >= self.minimumHeight():
                self.setGeometry(rect)
        
        # Если перемещаем окно
        elif event.buttons() == Qt.LeftButton and self.dragging and self.draggable:
            self.move(event.globalPos() - self.drag_position)
        
        # Если просто двигаем мышью без нажатия кнопки
        elif not event.buttons() and self.resizable:
            self.update_cursor_shape(cursor_position)
        
        super(ResizableFramelessWindow, self).mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Обработка отпускания кнопки мыши."""
        self.dragging = False
        self.draggable = True
        
        # Обновляем курсор при отпускании кнопки
        if self.resizable:
            self.update_cursor_shape(event.pos())
        else:
            self.setCursor(Qt.ArrowCursor)
            
        super(ResizableFramelessWindow, self).mouseReleaseEvent(event)
        
    def event(self, event):
        """Перехватываем события для обработки HoverMove."""
        if event.type() == QtCore.QEvent.HoverMove and self.resizable:
            self.update_cursor_shape(event.pos())
        return super(ResizableFramelessWindow, self).event(event)

class MacOSToggleSwitch(QWidget):
    """Переключатель в стиле macOS."""
    
    # Сигнал, который будет отправлен при изменении состояния
    toggled = pyqtSignal(bool)
    
    def __init__(self, parent=None, is_on=False, 
                 track_color="#E4E4E4", thumb_color="#FFFFFF", 
                 track_active_color="#34C759"):
        super(MacOSToggleSwitch, self).__init__(parent)
        
        # Настройка размеров
        self.track_width = 50
        self.track_height = 27
        self.thumb_size = 23
        self.track_border = 2
        
        # Цвета
        self.track_color = track_color
        self.thumb_color = thumb_color  
        self.track_active_color = track_active_color
        
        # Позиция ползунка
        self.margin = (self.track_height - self.thumb_size) // 2
        self._thumb_position = self.margin
        
        # Текущее состояние
        self.is_on = is_on
        if self.is_on:
            self._thumb_position = self.track_width - self.margin - self.thumb_size
        
        # Для анимации
        self.animation = QPropertyAnimation(self, b"thumb_position")
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.setDuration(150)
        
        # Настройка виджета
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(self.track_width, self.track_height)
    
    # Свойство для анимации положения ползунка
    def get_thumb_position(self):
        return self._thumb_position
    
    def set_thumb_position(self, position):
        self._thumb_position = position
        self.update()
    
    thumb_position = QtCore.pyqtProperty(float, get_thumb_position, set_thumb_position)
    
    def paintEvent(self, event):
        """Отрисовка переключателя."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Рисуем фон (track)
        if self.is_on:
            track_color = self.track_active_color
        else:
            track_color = self.track_color
        
        # Рисуем трек с тенью
        track_rect = QtCore.QRectF(0, 0, self.track_width, self.track_height)
        
        # Отрисовка трека с закругленными краями
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(track_color)))
        painter.drawRoundedRect(track_rect, self.track_height / 2, self.track_height / 2)
        
        # Рисуем ползунок (thumb)
        thumb_rect = QtCore.QRectF(
            self._thumb_position, 
            self.margin, 
            self.thumb_size, 
            self.thumb_size
        )
        
        # Небольшая тень под ползунком
        shadow_rect = thumb_rect.adjusted(-1, -1, 1, 2)
        shadow_color = QColor(0, 0, 0, 30)
        painter.setBrush(QBrush(shadow_color))
        painter.drawEllipse(shadow_rect)
        
        # Отрисовка ползунка
        painter.setBrush(QBrush(QColor(self.thumb_color)))
        painter.drawEllipse(thumb_rect)
    
    def mousePressEvent(self, event):
        """Обработка нажатия на переключатель."""
        if event.button() == Qt.LeftButton:
            self.toggle()
    
    def toggle(self):
        """Переключение состояния."""
        self.is_on = not self.is_on
        
        # Анимация перемещения ползунка
        if self.is_on:
            end_pos = self.track_width - self.margin - self.thumb_size
        else:
            end_pos = self.margin
        
        self.animation.setStartValue(self._thumb_position)
        self.animation.setEndValue(end_pos)
        self.animation.start()
        
        # Отправляем сигнал о переключении
        self.toggled.emit(self.is_on)
    
    def set_state(self, is_on, emit_signal=False):
        """Установка состояния переключателя."""
        if self.is_on != is_on:
            self.is_on = is_on
            
            # Анимация перемещения ползунка
            if self.is_on:
                end_pos = self.track_width - self.margin - self.thumb_size
            else:
                end_pos = self.margin
            
            self.animation.setStartValue(self._thumb_position)
            self.animation.setEndValue(end_pos)
            self.animation.start()
            
            if emit_signal:
                self.toggled.emit(self.is_on)
        elif self.is_on == is_on:
            # Если состояние уже установлено, просто обновляем положение ползунка
            if self.is_on:
                self._thumb_position = self.track_width - self.margin - self.thumb_size
            else:
                self._thumb_position = self.margin
            self.update()

class ModeLabel(QLabel):
    """Метка с анимацией изменения прозрачности в стиле Apple."""
    
    def __init__(self, text, parent=None):
        super(ModeLabel, self).__init__(text, parent)
        
        # Устанавливаем меньший размер шрифта
        font = self.font()
        font.setPointSize(font.pointSize() - 2)
        self.setFont(font)
        
        # Создаем эффект прозрачности
        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.6)  # Начальное значение (неактивное)
        self.setGraphicsEffect(self.opacity_effect)
        
        # Создаем анимацию для прозрачности
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(200)  # Длительность анимации
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def set_active(self, active):
        """Устанавливает состояние метки (активно/неактивно) с анимацией."""
        if active:
            # Активация: увеличиваем непрозрачность и делаем текст зеленым
            self.animation.setStartValue(self.opacity_effect.opacity())
            self.animation.setEndValue(1.0)
            self.setStyleSheet("color: #34C759; font-weight: bold;")
        else:
            # Деактивация: уменьшаем непрозрачность и делаем текст серым
            self.animation.setStartValue(self.opacity_effect.opacity())
            self.animation.setEndValue(0.6)
            self.setStyleSheet("color: #808080; font-weight: normal;")
        
        self.animation.start()

class TextRotator(ResizableFramelessWindow):
    def __init__(self):
        super(TextRotator, self).__init__()
        
        self.data_rotation = [] # Data when checkbox is OFF
        self.data_popup = []    # Data when checkbox is ON
        self.flat_texts_for_rotation = [] # For rotation mode cache
        self.current_rotation_index = 0
        self.hotkey = "ctrl+2"
        self.config_file = os.path.join(os.path.expanduser("~"), "text_rotator_config.json")
        self.is_running = False
        self.hotkey_listener_thread = None
        self.use_popup = False # Will be determined by load_config
        self.popup = None
        self.add_folder_button = None # Placeholder for the button
        self.settings_dialog = None # Placeholder for the settings dialog instance
        self.is_dark_theme = False # Will be determined by apply_theme based on mode
        self.theme_mode = "auto" # New setting: "auto", "light", "dark"
        
        self.load_config() # Load config first (loads theme_mode)
        self.apply_theme() # Apply theme based on loaded mode
        self.init_ui()     # Then init UI
        
        # Создаем иконку в трее
        self.tray_icon = QSystemTrayIcon(self)
        # Устанавливаем иконку приложения для трея
        app_icon_path = resource_path("assets/app.ico")
        if os.path.exists(app_icon_path):
            self.tray_icon.setIcon(QIcon(app_icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon))
        
        # Создаем меню для иконки в трее
        tray_menu = QMenu()
        
        show_action = QAction("Показать окно", self)
        show_action.triggered.connect(self.show)
        
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close_app)
        
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # Соединяем двойной клик по иконке с показом окна
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # Применяем тему в зависимости от режима системы - Moved up before init_ui
        # self.apply_theme()

    def apply_theme(self, mode=None):
        """Применяет тему на основе указанного режима или сохраненного self.theme_mode."""
        # Determine the mode to use
        current_mode = mode if mode else self.theme_mode
        
        # Determine if dark theme should be active based on mode
        if current_mode == "dark":
            self.is_dark_theme = True
        elif current_mode == "light":
            self.is_dark_theme = False
        else: # Auto mode
            self.is_dark_theme = is_system_dark_theme()
            
        print(f"Applying theme. Mode: {current_mode}, is_dark_theme: {self.is_dark_theme}") # Debug log

        # Apply the stylesheet based on self.is_dark_theme
        if self.is_dark_theme:
            # Темная тема
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #1E1E1E;
                    color: #FFFFFF;
                    border-radius: 10px;
                    border: 1px solid #3C3C3C;
                }
                QDialog, QWidget {
                    background-color: #1E1E1E;
                    color: #FFFFFF;
                }
                QLabel {
                    color: #FFFFFF;
                    font-family: 'Inter';
                    font-size: 16px;
                    font-weight: 400;
                }
                QLineEdit, QPlainTextEdit {
                    border: 1px solid #3C3C3C;
                    border-radius: 5px;
                    padding: 5px;
                    font-family: 'Inter';
                    font-size: 16px;
                    font-weight: 400;
                    background-color: #2D2D2D;
                    color: #FFFFFF;
                }
                /* Hover effect for the specific hotkey QLineEdit */
                QLineEdit#hotkeyDisplayLineEdit:hover {
                    background-color: #3A3A3A; /* Slightly lighter dark */
                }
                QPushButton {
                    border: 1px solid #3C3C3C;
                    border-radius: 5px;
                    padding: 5px 10px;
                    font-family: 'Inter';
                    font-size: 16px;
                    font-weight: 400;
                    background-color: #2D2D2D;
                    color: #FFFFFF;
                }
                QPushButton:hover {
                    background-color: #3C3C3C;
                }
                QPushButton:disabled {
                    background-color: #1E1E1E;
                    color: #808080;
                    border-color: #2D2D2D;
                }
                QListWidget {
                    border: 1px solid #3C3C3C;
                    border-radius: 5px;
                    font-family: 'Inter';
                    font-size: 16px;
                    font-weight: 400;
                    background-color: #2D2D2D;
                    color: #FFFFFF;
                }
                QListWidget::item:selected {
                    background-color: #3C3C3C;
                }
                QCheckBox {
                    font-family: 'Inter';
                    font-size: 16px;
                    font-weight: 400;
                    color: #FFFFFF;
                }
                QMenu {
                    background-color: #2D2D2D;
                    color: #FFFFFF;
                    border: 1px solid #3C3C3C;
                }
                QMenu::item:selected {
                    background-color: #3C3C3C;
                }
            """)
        else:
            # Светлая тема
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #FFFFFF;
                }
                QDialog, QWidget {
                    background-color: #FFFFFF;
                }
                QLabel {
                    color: #000000;
                    font-family: 'Inter';
                    font-size: 16px;
                    font-weight: 400;
                }
                QLineEdit, QPlainTextEdit {
                    border: 1px solid #C9C9C9;
                    border-radius: 5px;
                    padding: 5px;
                    font-family: 'Inter';
                    font-size: 16px;
                    font-weight: 400;
                }
                /* Hover effect for the specific hotkey QLineEdit */
                 QLineEdit#hotkeyDisplayLineEdit:hover {
                    background-color: #F5F5F5; /* Slightly lighter gray */
                }
                QPushButton {
                    border: 1px solid #CCCCCD;
                    border-radius: 5px;
                    padding: 5px 10px;
                    font-family: 'Inter';
                    font-size: 16px;
                    font-weight: 400;
                    background-color: #FFFFFF;
                }
                QPushButton:hover {
                    background-color: #F9F9F9;
                }
                QPushButton:disabled {
                    background-color: #F0F0F0;
                    color: #A0A0A0;
                    border-color: #D0D0D0;
                }
                QListWidget {
                    border: 1px solid #C9C9C9;
                    border-radius: 5px;
                    font-family: 'Inter';
                    font-size: 16px;
                    font-weight: 400;
                }
                QListWidget::item:selected {
                    background-color: #AAD3FE;
                }
                QCheckBox {
                    font-family: 'Inter';
                    font-size: 16px;
                    font-weight: 400;
                }
                QMenu {
                    background-color: #FFFFFF;
                    color: #000000;
                    border: 1px solid #C9C9C9;
                }
                QMenu::item:selected {
                    background-color: #AAD3FE;
                }
            """)

        # Если есть кастомный заголовок, обновляем его тему
        if hasattr(self, 'title_bar'):
            self.title_bar.update_theme(self.is_dark_theme)
            
        # Update button icons after theme change
        self.update_button_icons()
        
        # If settings dialog exists, update its style too
        if self.settings_dialog:
             self.settings_dialog.apply_parent_style()

    def init_ui(self):
        self.setWindowTitle('Text Rotator')
        self.setGeometry(300, 300, 600, 500)
        
        # Основной макет
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Вертикальный макет для всего окна
        full_layout = QVBoxLayout(main_widget)
        full_layout.setContentsMargins(0, 0, 0, 0)
        full_layout.setSpacing(0)
        
        # Добавляем кастомный заголовок в верхнюю часть
        self.title_bar = CustomTitleBar(self)
        full_layout.addWidget(self.title_bar)
        
        # Содержимое окна
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(10)
        
        # Горячая клавиша
        hotkey_layout = QHBoxLayout()
        hotkey_label = QLabel("Горячая клавиша:")
        self.hotkey_display = QLineEdit(self.hotkey)
        self.hotkey_display.setReadOnly(True)
        self.hotkey_display.setToolTip("Нажмите для изменения горячей клавиши") # Add tooltip back
        self.hotkey_display.setObjectName("hotkeyDisplayLineEdit") # Add object name back
        # --- Устанавливаем event filter для отслеживания клика --- 
        self.hotkey_display.installEventFilter(self)
        
        # --- Создаем кнопку настроек ЗДЕСЬ (вместо "Изменить") --- 
        settings_button = QPushButton()
        settings_icon = self.get_themed_icon("setting.svg") # Use new themed icon
        settings_button.setIcon(settings_icon)
        settings_button.setToolTip("Настройки")
        settings_button.clicked.connect(self.open_settings)
        
        hotkey_layout.addWidget(hotkey_label)
        hotkey_layout.addWidget(self.hotkey_display, 1) # Give hotkey display stretch factor
        hotkey_layout.addWidget(settings_button) # Add settings button here
        
        content_layout.addLayout(hotkey_layout)
        
        # Добавляем переключатель режима работы (macOS тумблер)
        popup_layout = QHBoxLayout()
        
        # Создаем метки для режимов с анимацией
        self.rotation_label = ModeLabel("Rotation")
        self.popup_label = ModeLabel("Popup")
        
        # Светлый оттенок серого для неактивного и зелёный для активного режима
        track_color = "#E4E4E4" if not self.is_dark_theme else "#3C3C3C"
        active_color = "#34C759"  # Зелёный цвет в стиле macOS
        
        # Создаём переключатель и устанавливаем начальное состояние
        self.mode_toggle = MacOSToggleSwitch(
            is_on=self.use_popup,
            track_color=track_color,
            track_active_color=active_color
        )
        self.mode_toggle.toggled.connect(self.toggle_popup_mode)
        
        # Устанавливаем начальное состояние меток
        self.update_mode_labels()
        
        # Добавляем метки и переключатель в макет
        popup_layout.addWidget(self.rotation_label)
        popup_layout.addWidget(self.mode_toggle)
        popup_layout.addWidget(self.popup_label)
        popup_layout.addStretch()
        popup_layout.addWidget(QLabel("Отдельный профиль для каждого режима"))
        
        content_layout.addLayout(popup_layout)
        
        # Список текстов и папок
        list_label = QLabel("Список текстов и папок (активный профиль):")
        content_layout.addWidget(list_label)
        
        self.main_list_widget = QListWidget() # Переименовали
        self.main_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.main_list_widget.itemDoubleClicked.connect(self.edit_selected_item)
        self.update_main_list_widget()
        content_layout.addWidget(self.main_list_widget)
        
        # Кнопки управления списком
        list_buttons_layout = QHBoxLayout()
        
        # Загружаем иконки с использованием resource_path с учетом темы
        add_icon = self.get_themed_icon("add.svg")
        folder_icon = self.get_themed_icon("folder.svg")
        delete_icon = self.get_themed_icon("delete.svg")
        move_up_icon = self.get_themed_icon("move_up.svg")
        move_down_icon = self.get_themed_icon("move_down.svg")
        
        # Кнопки слева
        add_text_button = QPushButton()
        add_text_button.setIcon(add_icon)
        add_text_button.setToolTip("Добавить текст в активный профиль")
        add_text_button.clicked.connect(self.add_root_text)
        
        delete_button = QPushButton()
        delete_button.setIcon(delete_icon)
        delete_button.setToolTip("Удалить выбранное из активного профиля")
        delete_button.clicked.connect(self.delete_selected_item)
        
        # Create and store the "Add Folder" button
        self.add_folder_button = QPushButton() 
        self.add_folder_button.setIcon(folder_icon)
        self.add_folder_button.setToolTip("Добавить папку (только в режиме окна выбора)")
        self.add_folder_button.clicked.connect(self.add_root_folder)
        # --- Start disabled by default ---
        self.add_folder_button.setEnabled(False) 
        
        # Кнопки справа
        move_up_button = QPushButton()
        move_up_button.setIcon(move_up_icon)
        move_up_button.setToolTip("Вверх")
        move_up_button.clicked.connect(self.move_item_up)
        
        move_down_button = QPushButton()
        move_down_button.setIcon(move_down_icon)
        move_down_button.setToolTip("Вниз")
        move_down_button.clicked.connect(self.move_item_down)
        
        # Добавляем кнопки в макет
        # Слева: создать, удалить, папка
        list_buttons_layout.addWidget(add_text_button)
        list_buttons_layout.addWidget(delete_button)
        list_buttons_layout.addWidget(self.add_folder_button)
        list_buttons_layout.addStretch() # Растягивающийся промежуток между группами кнопок
        # Справа: вверх, вниз, настройки
        list_buttons_layout.addWidget(move_up_button)
        list_buttons_layout.addWidget(move_down_button)
        # list_buttons_layout.addWidget(settings_button) # Remove settings button from here
        
        content_layout.addLayout(list_buttons_layout)
        
        # --- Explicitly enable ONLY if use_popup is True after load_config ---
        if self.use_popup:
            self.add_folder_button.setEnabled(True)
            print("Init UI: Add Folder button enabled because use_popup is True.")
        else:
             print("Init UI: Add Folder button remains disabled because use_popup is False.")

        # Кнопка запуска/остановки
        self.start_stop_button = QPushButton("Запустить")
        self.start_stop_button.setStyleSheet("""
            QPushButton {
                background-color: #34C759; /* Apple Green */
                color: #FFFFFF;
                font-size: 16px; /* Consistent font size */
                font-weight: 600; /* Semi-bold for emphasis */
                border: 1px solid rgba(0, 0, 0, 0.1); /* Subtle border */
                border-radius: 8px; /* Rounded corners */
                padding: 8px 18px; /* Adjusted padding */
                min-height: 24px; /* Ensure minimum height */
            }
            QPushButton:hover {
                background-color: #30B853; /* Slightly darker green */
            }
            QPushButton:pressed {
                background-color: #2CA94D; /* Even darker green */
            }
            QPushButton:disabled {
                background-color: #E5E5E5; /* Standard disabled color */
                color: #A0A0A0;
                border: 1px solid #D0D0D0;
            }
        """)
        self.start_stop_button.clicked.connect(self.toggle_start_stop)
        content_layout.addWidget(self.start_stop_button)
        
        # Статус
        self.status_label = QLabel("Готово к запуску")
        self.status_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.status_label)
        
        # Добавляем содержимое в основной макет
        full_layout.addWidget(content_widget)

        self.show()
    
    def update_mode_labels(self):
        """Обновляет стиль меток режимов в зависимости от активного режима с анимацией."""
        if self.use_popup:
            self.rotation_label.set_active(False)
            self.popup_label.set_active(True)
        else:
            self.rotation_label.set_active(True)
            self.popup_label.set_active(False)
        
    def toggle_popup_mode(self, state):
        """Переключает режим работы (Rotation/Popup)."""
        if state == self.use_popup:
            return  # No change
              
        self.use_popup = state
        print(f"Переключение профиля. Активный профиль: {'popup' if self.use_popup else 'rotation'}")
        
        # Обновляем метки с анимацией
        self.update_mode_labels()
        
        # Enable/Disable the "Add Folder" button based on the mode
        self.add_folder_button.setEnabled(self.use_popup) 
        
        # Update the list widget to show the data for the new profile
        self.update_main_list_widget() 
        
        # Save the new state immediately
        self.save_config()
        
        # If the listener is running, restart it to use the correct data/mode
        if self.is_running:
            print("Перезапуск listener из-за смены режима...")
            was_running = self.is_running # Store state before stopping
            self.toggle_start_stop()      # Stop
            if was_running:               # Schedule start only if it was running
                # Small delay might help ensure the stop completes before starting again
                QtCore.QTimer.singleShot(100, self.toggle_start_stop) # Start again after 100ms

    def record_hotkey(self):
        # Если программа запущена, сначала остановим её
        was_running = False
        if self.is_running:
            was_running = True
            self.toggle_start_stop()
        
        dialog = HotkeyRecorderDialog(self)
        if dialog.exec_():
            if dialog.result_hotkey:
                try:
                    # Проверяем валидность комбинации с keyboard
                    keyboard.parse_hotkey(dialog.result_hotkey)
                    # Если валидно, сохраняем
                    self.hotkey = dialog.result_hotkey
                    self.hotkey_display.setText(self.hotkey)
                    self.save_config()
                    QMessageBox.information(self, "Успех", f"Горячая клавиша изменена на {self.hotkey}")
                except ValueError as e:
                    QMessageBox.warning(self, "Ошибка", f"Некорректная или неподдерживаемая комбинация клавиш: {dialog.result_hotkey}\n({str(e)})")
                except Exception as e: # Ловим другие возможные ошибки keyboard
                    QMessageBox.warning(self, "Ошибка", f"Не удалось обработать комбинацию: {dialog.result_hotkey}\n({str(e)})")
        
        # Если программа была запущена, запустим её снова
        if was_running:
            self.toggle_start_stop()
    
    def get_current_data(self):
        """Returns the data list for the currently active profile."""
        return self.data_popup if self.use_popup else self.data_rotation

    def _flatten_data(self, data_list):
        """Рекурсивно собирает все тексты из ЗАДАННОЙ структуры данных в плоский список."""
        flat_list = []
        for item in data_list:
            if isinstance(item, str):
                flat_list.append(item)
            elif isinstance(item, dict) and item.get('type') == 'folder':
                # Рекурсивно обходим папку
                flat_list.extend(self._flatten_data(item.get('items', [])))
        return flat_list

    def recreate_popup(self, data):
        """Пересоздает окно выбора текста для обеспечения корректной работы"""
        if self.popup:
            # Удаляем старый экземпляр
            try:
                self.popup.hide()  # Сначала скрываем
                self.popup.setParent(None)  # Отсоединяем от родительского окна
                self.popup.deleteLater()  # Планируем уничтожение
            except Exception as e:
                print(f"Ошибка при уничтожении popup: {e}")
            
        # Создаем новый экземпляр
        callback = partial(self.paste_selected_text_from_flat_list, data)
        self.popup = TextSelectionPopup(data, callback, parent=self)
        return self.popup

    def rotate_text(self):
        """Handles hotkey press: either rotates text or shows popup based on mode."""
        print(f"Hotkey pressed. Current mode: {'popup' if self.use_popup else 'rotation'}") # Добавим лог режима
        if self.use_popup:
            # --- Режим всплывающего окна ---
            print("Entering popup mode logic...") # Лог входа
            current_profile_data = self.data_popup # Get data for popup profile
            print(f"Popup profile data: {current_profile_data}") # Лог данных профиля
            if not current_profile_data:
                 print("Профиль окна выбора пуст, попап не показан.")
                 return

            print("Preparing to show popup...") # Лог перед показом
            
            # Всегда пересоздаем окно для надежности
            popup = self.recreate_popup(current_profile_data)
            
            print("Calling show_at_cursor()...") # Лог перед вызовом
            popup.show_at_cursor() # show_at_cursor now includes raise_() and activateWindow()
            print("Called show_at_cursor() on popup.") # Лог вызова показа
            
            # Добавляем дополнительную активацию окна
            popup.activateWindow()
            popup.raise_()
            QtWidgets.QApplication.processEvents()

        else:
            # --- Режим ротации ---
            if not self.flat_texts_for_rotation:
                print("Профиль ротации пуст, ротация невозможна.")
                return
                
            if not self.flat_texts_for_rotation: # Double check after potential flattening
                 print("Профиль ротации все еще пуст после проверки.")
                 return

            # Ensure index is valid
            if self.current_rotation_index >= len(self.flat_texts_for_rotation):
                 self.current_rotation_index = 0 # Reset if out of bounds
                 
            if not self.flat_texts_for_rotation: # Check again after potential reset
                 print("Профиль ротации пуст после сброса индекса.")
                 return

            text_to_insert = self.flat_texts_for_rotation[self.current_rotation_index]
            
            # Обновляем индекс для следующего вызова
            self.current_rotation_index = (self.current_rotation_index + 1) % len(self.flat_texts_for_rotation)
            
            # --- Use paste_text which handles clipboard AND paste simulation ---
            print(f"Rotation mode: pasting item {self.current_rotation_index}/{len(self.flat_texts_for_rotation)}")
            self.paste_text(text_to_insert) 

    def paste_selected_text_from_flat_list(self, data, text):
        """Callback for TextSelectionPopup. Gets text and pastes it."""
        if text:
            self.paste_text(text) # Use the common paste method
        else:
            print(f"Ошибка: Неверный текст получен из попапа.")
            
    def paste_text(self, text_to_insert):
        """Вставляет переданный текст (используется и попапом, и ротацией)."""
        if text_to_insert:
            try:
                # Копируем текст в буфер обмена через Qt
                clipboard = QtWidgets.QApplication.clipboard()
                clipboard.setText(text_to_insert)
                
                # Небольшая пауза перед манипуляциями с клавиатурой
                time.sleep(0.1) 
                
                # Вставляем новый текст
                keyboard.press_and_release('ctrl+v')
                
                # Если мы в режиме ротации, выделяем только что вставленный текст123123123
                # чтобы следующая вставка его заменила (как в oldversion.py)
                if not self.use_popup: 
                    time.sleep(0.05) # Короткая пауза после вставки перед выделением
                    keyboard.press('shift')
                    for _ in range(len(text_to_insert)):
                        keyboard.press_and_release('left') # Используем стрелку ВЛЕВО
                    keyboard.release('shift')

            except Exception as e:
                print(f"Ошибка вставки текста: {e}")
                QMessageBox.warning(self, "Ошибка вставки", f"Не удалось вставить текст: {e}")

    def load_config(self):
        """Loads configuration, including theme mode."""
        # Set defaults first
        self.data_rotation = []
        self.data_popup = []
        self.hotkey = "ctrl+2"
        self.use_popup = False # Default to rotation mode
        self.theme_mode = "auto" # Default theme mode
        needs_save_after_migration = False

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                self.hotkey = config.get('hotkey', "ctrl+2")
                self.theme_mode = config.get('theme_mode', "auto") # Load theme mode

                if 'data_rotation' in config or 'data_popup' in config:
                    self.data_rotation = config.get('data_rotation', [])
                    self.data_popup = config.get('data_popup', [])
                    self.use_popup = config.get('use_popup', False)
                    print(f"Load Config: Загружены профили rotation/popup. Режим use_popup: {self.use_popup}")
                elif 'data' in config:
                    print("Load Config: Обнаружен старый формат ('data'). Миграция...")
                    self.data_rotation = config.get('data', [])
                    self.data_popup = []
                    self.use_popup = False # Reset mode
                    needs_save_after_migration = True # Mark for saving
                    print("Load Config: Миграция завершена. Режим установлен на 'rotation'.")
                elif 'texts' in config:
                    print("Load Config: Обнаружен старый формат ('texts'). Миграция...")
                    self.data_rotation = config.get('texts', [])
                    self.data_popup = []
                    self.use_popup = False # Reset mode
                    needs_save_after_migration = True # Mark for saving
                    print("Load Config: Миграция завершена. Режим установлен на 'rotation'.")
                else:
                    print("Load Config: Конфигурационный файл не содержит данных. Режим: rotation.")
                    self.use_popup = False # Ensure default is set

                # Save immediately if migration occurred to persist the corrected state
                if needs_save_after_migration:
                    print("Load Config: Сохранение конфигурации после миграции...")
                    self.save_config() # Save the updated structure and use_popup=False

        except json.JSONDecodeError as e:
             QMessageBox.warning(self, "Ошибка конфигурации", f"Не удалось прочитать файл конфигурации: {e}\nБудут использованы настройки по умолчанию.")
             self.data_rotation, self.data_popup, self.hotkey, self.use_popup = [], [], "ctrl+2", False
        except Exception as e:
            QMessageBox.warning(self, "Ошибка загрузки", f"Не удалось загрузить конфигурацию: {e}\nБудут использованы настройки по умолчанию.")
            self.data_rotation, self.data_popup, self.hotkey, self.use_popup = [], [], "ctrl+2", False

        self.flat_texts_for_rotation = []
        self.current_rotation_index = 0

    def save_config(self):
        """Saves configuration including both profiles and theme mode."""
        # No need to update flat_texts_for_rotation here
        try:
            config = {
                'data_rotation': self.data_rotation,
                'data_popup': self.data_popup,
                'hotkey': self.hotkey,
                'use_popup': self.use_popup, # Save the current mode
                'theme_mode': self.theme_mode # Save the theme mode
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка сохранения", f"Не удалось сохранить конфигурацию: {str(e)}")

    def toggle_start_stop(self):
        if self.is_running:
            # Останавливаем
            try:
                if self.hotkey_listener_thread and self.hotkey_listener_thread.isRunning():
                    print("Остановка listener потока...")
                    self.hotkey_listener_thread.stop()
                    self.hotkey_listener_thread.wait() # wait() can block GUI, use event loop check later if needed
                self.hotkey_listener_thread = None # Allow garbage collection
                self.is_running = False
                self.start_stop_button.setText("Запустить")
                self.status_label.setText("Остановлено")
                self.tray_icon.showMessage("Text Rotator", "Программа остановлена", QSystemTrayIcon.Information, 2000)
                print("Listener остановлен.")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось корректно остановить программу: {str(e)}")
                print(f"Ошибка при остановке: {e}")
        else:
            # Запускаем
            can_start = False
            active_profile_data = self.get_current_data()
            mode_name = "окна выбора" if self.use_popup else "ротации"

            if not self.use_popup:
                # Rotation mode: flatten rotation data and check if not empty
                print("Подготовка к запуску в режиме ротации...")
                self.flat_texts_for_rotation = self._flatten_data(self.data_rotation) # Use rotation data
                if self.flat_texts_for_rotation:
                    can_start = True
                    self.current_rotation_index = 0 # Reset index on start
                    print(f"Режим ротации: Найдено {len(self.flat_texts_for_rotation)} текстов.")
                else:
                     QMessageBox.warning(self, "Предупреждение", f"Профиль '{mode_name}' пуст или не содержит текстов. Добавьте тексты перед запуском.")
            else:
                 # Popup mode: check if popup data structure itself is not empty
                 print("Подготовка к запуску в режиме окна выбора...")
                 if self.data_popup: # Check the main structure, flattening happens on hotkey press
                     # We also need at least one actual text string inside for it to work
                     if self._flatten_data(self.data_popup):
                         can_start = True
                         print("Режим окна выбора: Профиль не пуст и содержит тексты.")
                     else:
                          QMessageBox.warning(self, "Предупреждение", f"Профиль '{mode_name}' не содержит текстовых элементов. Добавьте тексты перед запуском.")
                 else:
                     QMessageBox.warning(self, "Предупреждение", f"Профиль '{mode_name}' пуст. Добавьте тексты или папки перед запуском.")

            if not can_start:
                print("Запуск отменен: нет данных для активного режима.")
                return # Don't start if checks fail

            try:
                print(f"Запуск listener для горячей клавиши: {self.hotkey}")
                self.hotkey_listener_thread = HotkeyListener(self.hotkey)
                # rotate_text now handles both modes internally
                self.hotkey_listener_thread.hotkey_pressed.connect(self.rotate_text) 
                self.hotkey_listener_thread.start()
                
                self.is_running = True
                self.start_stop_button.setText("Остановить")
                
                mode_text_display = "режим окна выбора" if self.use_popup else "режим ротации"
                self.status_label.setText(f"Запущено ({mode_text_display}). Нажмите {self.hotkey}")
                
                self.hide()
                self.tray_icon.showMessage(
                    "Text Rotator запущен",
                    f"Профиль '{mode_name}' активен. Используйте {self.hotkey}.",
                    QSystemTrayIcon.Information,
                    2000
                )
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось запустить listener: {str(e)}")
                print(f"Ошибка при запуске listener: {e}")
                self.is_running = False # Ensure state is correct on failure
                self.start_stop_button.setText("Запустить")
                self.status_label.setText("Ошибка запуска")

    def update_main_list_widget(self):
        """Обновляет QListWidget, отображая данные АКТИВНОГО профиля."""
        self.main_list_widget.clear()
        # Use the helper method to get the correct data list
        current_data = self.get_current_data() 
        for item in current_data:
            if isinstance(item, str):
                preview = item.replace('\n', ' ')[:80] + ('...' if len(item.replace('\n', ' ')) > 80 else '')
                if not self.use_popup:  # Если режим Rotation, добавляем номер строки
                    line_number = self.main_list_widget.count() + 1
                    preview = f"{line_number}. {preview}"
                self.main_list_widget.addItem(preview)
            elif isinstance(item, dict) and item.get('type') == 'folder':
                folder_name = item.get('name', 'Безымянная папка')
                display_text = f"📁 {folder_name}"
                list_item = QtWidgets.QListWidgetItem(display_text)
                # Optional: Add folder icon
                # list_item.setIcon(QIcon(resource_path("assets/folder.svg"))) 
                self.main_list_widget.addItem(list_item)
            # else: handle unknown types if necessary

    def add_root_text(self):
        """Добавляет новый текстовый элемент в корень АКТИВНОГО профиля."""
        new_text, ok = QInputDialog.getMultiLineText(
            self, "Добавление текста", "Введите текст для добавления в активный профиль:", ""
        )
        if ok and new_text.strip():
            # Add to the currently active data list
            self.get_current_data().append(new_text.strip()) 
            self.update_main_list_widget() # Refresh list view
            self.save_config()             # Save changes
        elif ok and not new_text.strip():
            QMessageBox.warning(self, "Предупреждение", "Текст не может быть пустым!")

    def add_root_folder(self):
        """Добавляет новую папку в корень АКТИВНОГО профиля."""
        folder_name, ok = QInputDialog.getText(
            self, "Добавление папки", "Введите имя новой папки для активного профиля:", QLineEdit.Normal, "Новая папка"
        )
        if ok and folder_name.strip():
            # Optional: Check for unique name within the current profile
            # ...
            new_folder = {
                "type": "folder",
                "name": folder_name.strip(),
                "items": []
            }
            # Add to the currently active data list
            self.get_current_data().append(new_folder) 
            self.update_main_list_widget() # Refresh list view
            self.save_config()             # Save changes
        elif ok and not folder_name.strip():
            QMessageBox.warning(self, "Предупреждение", "Имя папки не может быть пустым!")

    def delete_selected_item(self):
        """Удаляет выбранный элемент из АКТИВНОГО профиля."""
        current_row = self.main_list_widget.currentRow()
        current_data = self.get_current_data() # Get the active list

        if current_row < 0 or current_row >= len(current_data):
            QMessageBox.warning(self, "Предупреждение", "Выберите элемент для удаления!")
            return

        item_to_delete = current_data[current_row]
        item_description = ""
        confirm_message = ""

        if isinstance(item_to_delete, str):
            item_description = f"текст " + item_to_delete[:30] + ("..." if len(item_to_delete) > 30 else "")
            confirm_message = f"Вы уверены, что хотите удалить {item_description} из текущего профиля?"
        elif isinstance(item_to_delete, dict) and item_to_delete.get('type') == 'folder':
            folder_name = item_to_delete.get('name', '')
            item_description = f"папку '{folder_name}' и всё её содержимое"
            confirm_message = f"Вы уверены, что хотите удалить {item_description} из текущего профиля?"
        else:
            QMessageBox.warning(self, "Ошибка", "Неизвестный тип элемента для удаления.")
            return
            
        reply = QMessageBox.question(self, 'Подтверждение', confirm_message,
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
        if reply == QMessageBox.Yes:
            del current_data[current_row] # Delete from the active list
            self.update_main_list_widget() # Refresh list view
            self.save_config()             # Save changes

    def move_item_up(self):
        """Перемещает выбранный элемент вверх в списке АКТИВНОГО профиля."""
        current_row = self.main_list_widget.currentRow()
        current_data = self.get_current_data() # Get the active list
        
        if current_row > 0:
            # Modify the active list directly
            current_data.insert(current_row - 1, current_data.pop(current_row)) 
            self.update_main_list_widget() # Refresh list view
            self.main_list_widget.setCurrentRow(current_row - 1) # Keep selection
            self.save_config()             # Save changes
        elif current_row == 0:
            QMessageBox.information(self, "Информация", "Элемент уже находится вверху списка!")
        else:
            QMessageBox.warning(self, "Предупреждение", "Выберите элемент для перемещения!")
            
    def move_item_down(self):
        """Перемещает выбранный элемент вниз в списке АКТИВНОГО профиля."""
        current_row = self.main_list_widget.currentRow()
        current_data = self.get_current_data() # Get the active list
        
        if 0 <= current_row < len(current_data) - 1:
             # Modify the active list directly
            current_data.insert(current_row + 1, current_data.pop(current_row))
            self.update_main_list_widget() # Refresh list view
            self.main_list_widget.setCurrentRow(current_row + 1) # Keep selection
            self.save_config()             # Save changes
        elif current_row == len(current_data) - 1:
            QMessageBox.information(self, "Информация", "Элемент уже находится внизу списка!")
        else:
            QMessageBox.warning(self, "Предупреждение", "Выберите элемент для перемещения!")

    def edit_selected_item(self, item_widget):
        """Редактирует текст или ОТКРЫВАЕТ папку в АКТИВНОМ профиле."""
        current_row = self.main_list_widget.row(item_widget)
        current_data = self.get_current_data() # Get the active list

        if current_row < 0 or current_row >= len(current_data):
            return

        item_data = current_data[current_row] # Get the item from the active list

        if isinstance(item_data, str):
            # Edit text
            new_text, ok = QInputDialog.getMultiLineText(
                self, "Редактирование текста", "Отредактируйте текст:", item_data
            )
            if ok and new_text.strip():
                 # Update item in the active list
                current_data[current_row] = new_text.strip() 
                self.update_main_list_widget() # Refresh view
                self.save_config()             # Save changes
            elif ok and not new_text.strip():
                 QMessageBox.warning(self, "Предупреждение", "Текст не может быть пустым!")

        elif isinstance(item_data, dict) and item_data.get('type') == 'folder':
            # Open folder edit dialog, passing the dictionary reference from the active list
            dialog = FolderEditDialog(item_data, self) # Pass the dict reference
            # The dialog modifies item_data in place
            dialog.folder_renamed.connect(self.update_main_list_widget) 
            
            dialog.exec_() 
            
            # After dialog closes, refresh list (in case name changed) and save
            self.update_main_list_widget() 
            self.save_config()
            
            # Disconnect signal
            try:
                dialog.folder_renamed.disconnect(self.update_main_list_widget)
            except TypeError:
                 pass 
                 
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
    
    def close_app(self):
        try:
            if self.is_running:
                if self.hotkey_listener_thread and self.hotkey_listener_thread.isRunning():
                    self.hotkey_listener_thread.stop()
                    self.hotkey_listener_thread.wait()
            self.save_config()
            QtWidgets.QApplication.quit()
        except Exception as e:
            QMessageBox.critical(self, "Критическая ошибка", f"Ошибка при закрытии приложения: {str(e)}")
            # Дополнительное логирование для отладки
            print(f"Критическая ошибка при закрытии: {e}")
            sys.exit(1)
    
    def closeEvent(self, event):
        if self.is_running:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Text Rotator",
                "Приложение продолжает работать в трее",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            self.close_app()

    def changeEvent(self, event):
        """Обрабатывает события изменения состояния окна, включая изменение темы системы (только в режиме 'auto')."""
        if event.type() == QtCore.QEvent.ActivationChange:
            # Check system theme change only if in auto mode
            if self.theme_mode == "auto":
                current_dark_theme = is_system_dark_theme()
                if current_dark_theme != self.is_dark_theme:
                    print("System theme changed (in auto mode), applying theme...")
                    self.apply_theme() # Re-apply theme using "auto" logic
                    # Icons are updated within apply_theme now
        super(TextRotator, self).changeEvent(event)

    def update_button_icons(self):
        """Обновляет иконки кнопок после смены темы."""
        # Кнопки уже должны существовать
        for widget in self.findChildren(QPushButton):
            if hasattr(widget, 'toolTip'):
                tooltip = widget.toolTip()
                if "Добавить текст" in tooltip:
                    widget.setIcon(self.get_themed_icon("add.svg"))
                elif "Добавить папку" in tooltip:
                    widget.setIcon(self.get_themed_icon("folder.svg"))
                elif "Удалить" in tooltip:
                    widget.setIcon(self.get_themed_icon("delete.svg"))
                elif "Вверх" in tooltip:
                    widget.setIcon(self.get_themed_icon("move_up.svg"))
                elif "Вниз" in tooltip:
                    widget.setIcon(self.get_themed_icon("move_down.svg"))

    def get_themed_icon(self, icon_name):
        """Загружает SVG иконку с учетом текущей темы.
        Для темной темы добавляет суффикс _d к имени файла."""
        # Извлекаем только базовое имя файла без пути
        base_name = os.path.basename(icon_name).replace('.svg', '')
        
        if self.is_dark_theme:
            # Для темной темы пытаемся загрузить версию с суффиксом _d
            icon_path = resource_path(f"assets/{base_name}_d.svg")
            # Проверяем существование файла
            print(f"Проверка наличия темной иконки: {icon_path}")
            if os.path.exists(icon_path):
                print(f"Используем темную иконку: {icon_path}")
                return QIcon(icon_path)
            else:
                # Если нет темной версии, используем обычную
                icon_path = resource_path(f"assets/{base_name}.svg")
                print(f"Темная иконка не найдена, используем стандартную: {icon_path}")
                return QIcon(icon_path)
        else:
            # Для светлой темы просто загружаем обычную версию
            icon_path = resource_path(f"assets/{base_name}.svg")
            print(f"Используем светлую иконку: {icon_path}")
            return QIcon(icon_path)

    def open_settings(self):
        """Открывает диалог настроек."""
        # Создаем диалог только если он еще не открыт
        # Или можно создавать каждый раз новый экземпляр:
        # settings_dialog = SettingsDialog(self)
        # settings_dialog.exec_()
        
        # Вариант с одним экземпляром (чтобы не плодить окна):
        if not self.settings_dialog:
            self.settings_dialog = SettingsDialog(self)
        self.settings_dialog.show() # Используем show() для немодального окна
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def eventFilter(self, obj, event):
        """Фильтрует события для объекта, чтобы перехватить клик по полю с хоткеем."""
        if obj is self.hotkey_display and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.record_hotkey()
                return True # Событие обработано
        # Возвращаем False для всех других событий, чтобы они обрабатывались по умолчанию
        return super(TextRotator, self).eventFilter(obj, event)

    def set_theme_mode(self, mode):
        """Устанавливает режим темы, сохраняет и применяет его."""
        if mode in ["light", "dark", "auto"]:
            if self.theme_mode != mode:
                print(f"Setting theme mode to: {mode}")
                self.theme_mode = mode
                self.save_config()
                self.apply_theme() # Apply the newly set theme mode
        else:
            print(f"Warning: Invalid theme mode provided: {mode}")

    def check_for_updates(self):
        """Checks for application updates on GitHub."""
        # TODO: Implement the actual update check logic (Steps 2-4)
        print(f"Checking for updates... Current version: {__version__}")
        # Placeholder: Simulate a check and re-enable button
        try:
            # Simulate network delay
            time.sleep(1) 
            QMessageBox.information(self, "Обновления", "Функция проверки обновлений еще не реализована.")
        except Exception as e:
             QMessageBox.warning(self, "Ошибка", f"Произошла ошибка: {e}")
        finally:
            # Ensure the button in the settings dialog is re-enabled
            if self.settings_dialog and hasattr(self.settings_dialog, 'enable_update_button'):
                # Call it via singleshot to ensure it runs in the main thread after this method finishes
                QtCore.QTimer.singleShot(0, self.settings_dialog.enable_update_button)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    # Включаем использование стиля Fusion для более современного вида
    app.setStyle("Fusion")
    
    # Устанавливаем иконку приложения (используем resource_path)
    app_icon_path = resource_path("assets/app.ico")
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))
    else:
        print(f"Warning: Application icon not found at {app_icon_path}")
        
    app.setQuitOnLastWindowClosed(False)
    window = TextRotator()
    sys.exit(app.exec_())