from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QListWidget, QMessageBox,
                             QInputDialog)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from utils.resource_path import resource_path
import os

class FolderEditDialog(QDialog):
    """Диалог для редактирования содержимого папки."""
    # Сигнал, который будет отправлен при переименовании папки
    folder_renamed = pyqtSignal(str) 
    
    def __init__(self, folder_data, parent=None):
        super(FolderEditDialog, self).__init__(parent)
        # Принимаем весь словарь папки
        self.folder_data = folder_data 
        # Получаем ссылку на список элементов для удобства
        self.folder_items = self.folder_data.setdefault('items', []) 
        # Получаем текущее имя
        self.folder_name = self.folder_data.get('name', 'Безымянная папка') 
        
        # Получаем тему из родительского окна
        self.is_dark_theme = False
        if parent and hasattr(parent, 'is_dark_theme'):
            self.is_dark_theme = parent.is_dark_theme
        
        self.setWindowTitle(f"Редактирование папки: {self.folder_name}")
        self.setModal(True)
        self.setGeometry(400, 400, 500, 450)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Поле для имени папки
        name_layout = QHBoxLayout()
        name_label = QLabel("Имя папки:")
        self.name_edit = QLineEdit(self.folder_name)
        rename_button = QPushButton("Переименовать")
        rename_button.clicked.connect(self.rename_folder)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)
        name_layout.addWidget(rename_button)
        main_layout.addLayout(name_layout)
        
        list_label = QLabel("Тексты в папке:")
        main_layout.addWidget(list_label)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.edit_item)
        self.update_list_widget()
        main_layout.addWidget(self.list_widget)

        # Кнопки управления списком
        buttons_layout = QHBoxLayout()
        
        # Используем иконки с учетом темы
        add_icon = self.get_themed_icon("add.svg")
        delete_icon = self.get_themed_icon("delete.svg")
        move_up_icon = self.get_themed_icon("move_up.svg")
        move_down_icon = self.get_themed_icon("move_down.svg")
        
        add_button = QPushButton()
        add_button.setIcon(add_icon)
        add_button.setToolTip("Добавить текст в папку")
        add_button.clicked.connect(self.add_item)
        
        delete_button = QPushButton()
        delete_button.setIcon(delete_icon)
        delete_button.setToolTip("Удалить текст")
        delete_button.clicked.connect(self.delete_item)
        
        move_up_button = QPushButton()
        move_up_button.setIcon(move_up_icon)
        move_up_button.setToolTip("Вверх")
        move_up_button.clicked.connect(self.move_item_up)
        
        move_down_button = QPushButton()
        move_down_button.setIcon(move_down_icon)
        move_down_button.setToolTip("Вниз")
        move_down_button.clicked.connect(self.move_item_down)

        buttons_layout.addWidget(add_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(move_up_button)
        buttons_layout.addWidget(move_down_button)
        buttons_layout.addWidget(delete_button)
        
        main_layout.addLayout(buttons_layout)

    def get_themed_icon(self, icon_name):
        """Загружает SVG иконку с учетом текущей темы.
        Для темной темы добавляет суффикс _d к имени файла."""
        # Извлекаем только базовое имя файла без пути
        base_name = os.path.basename(icon_name).replace('.svg', '')
        
        if self.is_dark_theme:
            # Для темной темы пытаемся загрузить версию с суффиксом _d
            icon_path = resource_path(f"assets/{base_name}_d.svg")
            # Проверяем существование файла
            if os.path.exists(icon_path):
                return QIcon(icon_path)
            else:
                # Если нет темной версии, используем обычную
                icon_path = resource_path(f"assets/{base_name}.svg")
                return QIcon(icon_path)
        else:
            # Для светлой темы просто загружаем обычную версию
            icon_path = resource_path(f"assets/{base_name}.svg")
            return QIcon(icon_path)

    def rename_folder(self):
        new_name = self.name_edit.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Предупреждение", "Имя папки не может быть пустым!")
            self.name_edit.setText(self.folder_name) # Вернуть старое имя в поле
            return
            
        if new_name != self.folder_name:
            # TODO: Проверка на уникальность имени (если нужно) в основном окне
            # Обновляем имя в словаре, переданном по ссылке
            self.folder_data['name'] = new_name
            self.folder_name = new_name # Обновляем локальное имя
            self.setWindowTitle(f"Редактирование папки: {self.folder_name}")
            QMessageBox.information(self, "Успех", "Папка переименована.")
            # Оповещаем родительское окно, что имя изменилось
            self.folder_renamed.emit(new_name) 

    def update_list_widget(self):
        self.list_widget.clear()
        # Отображаем только строки, т.к. в папках пока только текст
        for item in self.folder_items:
             if isinstance(item, str):
                preview = item.replace('\n', ' ')[:80] + ('...' if len(item.replace('\n', ' ')) > 80 else '')
                self.list_widget.addItem(preview)
             # Сюда можно добавить обработку вложенных папок, если потребуется

    def add_item(self):
        new_text, ok = QInputDialog.getMultiLineText(
            self, "Добавление текста", f"Введите текст для добавления в папку '{self.folder_name}':", ""
        )
        if ok and new_text.strip():
            # Напрямую модифицируем список, переданный из TextRotator
            self.folder_items.append(new_text.strip())
            self.update_list_widget()
            # Сохранение будет вызвано в TextRotator после закрытия диалога
        elif ok and not new_text.strip():
            QMessageBox.warning(self, "Предупреждение", "Текст не может быть пустым!")

    def edit_item(self, item_widget):
        current_row = self.list_widget.row(item_widget)
        if 0 <= current_row < len(self.folder_items):
            # Убедимся, что редактируем строку
            if isinstance(self.folder_items[current_row], str):
                current_text = self.folder_items[current_row]
                new_text, ok = QInputDialog.getMultiLineText(
                    self, "Редактирование текста", "Отредактируйте текст:", current_text
                )
                if ok and new_text.strip():
                    self.folder_items[current_row] = new_text.strip()
                    self.update_list_widget()
                elif ok and not new_text.strip():
                     QMessageBox.warning(self, "Предупреждение", "Текст не может быть пустым!")
            # Сюда можно добавить логику для редактирования вложенных папок

    def delete_item(self):
        current_row = self.list_widget.currentRow()
        if 0 <= current_row < len(self.folder_items):
            if isinstance(self.folder_items[current_row], str):
                item_description = f"текст " + self.folder_items[current_row][:30] + ("..." if len(self.folder_items[current_row]) > 30 else "")
                reply = QMessageBox.question(self, 'Подтверждение',
                                           f"Вы уверены, что хотите удалить {item_description} из папки '{self.folder_name}'?",
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    del self.folder_items[current_row]
                    self.update_list_widget()
            # Добавить логику для удаления вложенных папок
        else:
            QMessageBox.warning(self, "Предупреждение", "Выберите текст для удаления!")

    def move_item_up(self):
        current_row = self.list_widget.currentRow()
        if current_row > 0:
            self.folder_items.insert(current_row - 1, self.folder_items.pop(current_row))
            self.update_list_widget()
            self.list_widget.setCurrentRow(current_row - 1)

    def move_item_down(self):
        current_row = self.list_widget.currentRow()
        if 0 <= current_row < len(self.folder_items) - 1:
            self.folder_items.insert(current_row + 1, self.folder_items.pop(current_row))
            self.update_list_widget()
            self.list_widget.setCurrentRow(current_row + 1) 