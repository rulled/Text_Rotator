from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QHBoxLayout, 
                             QPushButton, QButtonGroup, QWidget, QMessageBox)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QRect
from PyQt5.QtGui import QColor

# We no longer need MacOSToggleSwitch here
# try:
#     from ..text_rotator import MacOSToggleSwitch
# except ImportError:
#     print("Warning: Could not import MacOSToggleSwitch. Theme toggle unavailable.")
#     MacOSToggleSwitch = None

class SettingsDialog(QDialog):
    """Окно настроек приложения с анимированным сегментным контролом."""
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.parent_window = parent

        # --- Define hover colors early ---
        self.hover_color_light = QColor(0, 0, 0, 15) # Light gray hover
        self.hover_color_dark = QColor(255, 255, 255, 20) # Lighter gray hover for dark theme

        self.setWindowTitle("Настройки")
        self.setMinimumSize(400, 200)
        self.setStyleSheet("") # Start with empty stylesheet

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # Заголовок
        self.title_label = QLabel("Настройки приложения")
        self.title_label.setAlignment(Qt.AlignCenter)
        font = self.title_label.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        self.title_label.setFont(font)
        self.layout.addWidget(self.title_label)

        # --- Theme Segmented Control ---
        theme_control_layout = QHBoxLayout()
        theme_label = QLabel("Тема оформления:")

        # Container for the buttons AND the indicator
        self.theme_button_group_widget = QWidget()
        self.theme_button_group_widget.setObjectName("themeSegmentedControlContainer")
        # Set fixed height for the container based on desired button height + padding
        self.control_height = 28 # Desired height
        self.theme_button_group_widget.setFixedHeight(self.control_height)

        # Layout for the container (indicator will be placed here too)
        self.segmented_layout = QHBoxLayout(self.theme_button_group_widget)
        self.segmented_layout.setContentsMargins(1, 1, 1, 1) # Padding inside container for border
        self.segmented_layout.setSpacing(0)

        # --- Indicator Widget ---
        self.theme_indicator = QWidget(self.theme_button_group_widget)
        self.theme_indicator.setObjectName("themeIndicator")
        self.theme_indicator.lower() # Ensure it's behind buttons

        self.indicator_anim = QPropertyAnimation(self.theme_indicator, b"geometry")
        self.indicator_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.indicator_anim.setDuration(200) # Animation duration

        # --- Buttons --- 
        self.theme_button_group = QButtonGroup(self)
        self.theme_button_group.setExclusive(True)

        # Use standard QPushButtons now
        self.btn_light = QPushButton("Светлая")
        self.btn_dark = QPushButton("Темная")
        self.btn_auto = QPushButton("Авто")

        self.theme_map = {self.btn_light: "light", self.btn_dark: "dark", self.btn_auto: "auto"}
        self.theme_map_inv = {v: k for k, v in self.theme_map.items()}

        for i, btn in enumerate([self.btn_light, self.btn_dark, self.btn_auto]):
            btn.setCheckable(True)
            btn.setFlat(True) # Make button background transparent by default
            btn.setObjectName("themeSegmentButton")
            btn.setFixedHeight(self.control_height - 2) # Match container height minus padding
            self.segmented_layout.addWidget(btn)
            self.theme_button_group.addButton(btn, i)
            # Hover effect will be handled by CSS

        self.theme_button_group.buttonClicked.connect(self.theme_button_clicked)

        theme_control_layout.addWidget(theme_label)
        theme_control_layout.addStretch()
        theme_control_layout.addWidget(self.theme_button_group_widget)
        self.layout.addLayout(theme_control_layout)

        self.layout.addStretch()

        # --- Check for Updates Button ---
        self.update_button = QPushButton("Проверить обновления")
        self.update_button.clicked.connect(self.check_for_updates_clicked)
        # Optional: Add some margin above the button
        self.layout.addSpacing(10) 
        self.layout.addWidget(self.update_button)

        # Apply styles AFTER parent styles are potentially set
        QtCore.QTimer.singleShot(0, self.apply_initial_styles_and_position) 

    def apply_initial_styles_and_position(self):
        """Called shortly after init to ensure parent styles are applied first."""
        self.apply_parent_style() # Applies base + segmented style
        self.update_indicator_position(animate=False) # Set initial position

    def apply_segmented_control_style(self):
        """Applies CSS styles for the container, indicator, and buttons."""
        is_dark = self.parent_window.is_dark_theme if self.parent_window else False

        # Define colors
        container_border_color = "#505050" if is_dark else "#C6C6C8"
        button_text_color = "#E0E0E0" if is_dark else "#333333"
        button_hover_bg = "rgba(128, 128, 128, 0.1)" if is_dark else "rgba(128, 128, 128, 0.1)" # Subtle hover
        indicator_bg = "#34C759" # App green
        checked_text_color = "#FFFFFF"

        # Define size adjustments
        font_size = "12px"
        button_padding = "3px 10px"
        container_radius = "7px"
        indicator_radius = "6px" # Slightly smaller radius for the indicator

        style = f"""
            /* Container Style */
            QWidget#themeSegmentedControlContainer {{
                background-color: transparent;
                border: 1px solid {container_border_color};
                border-radius: {container_radius};
                /* Height is set programmatically */
            }}

            /* Indicator Style */
            QWidget#themeIndicator {{
                background-color: {indicator_bg};
                border-radius: {indicator_radius};
            }}

            /* Button Style */
            QWidget#themeSegmentedControlContainer QPushButton#themeSegmentButton {{
                background-color: transparent; /* IMPORTANT: Buttons must be transparent */
                color: {button_text_color};
                border: none;
                padding: {button_padding};
                font-size: {font_size};
                font-weight: 500;
                /* Height is set programmatically */
            }}

            /* Vertical separators (drawn as button borders) */
            QWidget#themeSegmentedControlContainer QPushButton#themeSegmentButton:not(:first-child) {{
                 border-left: 1px solid {container_border_color};
            }}
            
            /* Hover effect for non-checked buttons */
            QWidget#themeSegmentedControlContainer QPushButton#themeSegmentButton:!checked:hover {{
                background-color: {button_hover_bg};
                /* Apply border radius on hover to match indicator */
                border-radius: {indicator_radius};
            }}
            
            /* Text color for the checked button */
            QWidget#themeSegmentedControlContainer QPushButton#themeSegmentButton:checked {{
                color: {checked_text_color};
                background-color: transparent; /* Checked button still transparent */
                font-weight: 600; /* Bolder when selected */
            }}
        """
        # Append to existing styles from parent (ensure no duplicates)
        current_style = self.styleSheet()
        # Simple strategy: Remove old style section if present, then append new one
        # A more robust approach would parse the CSS, but this is often sufficient
        start_marker = "/* Container Style */"
        style_to_set = current_style
        try:
            index = current_style.index(start_marker)
            style_to_set = current_style[:index]
        except ValueError:
            pass # Marker not found, just append
            
        self.setStyleSheet(style_to_set + style)

    def theme_button_clicked(self, button):
        """Handles theme selection and updates indicator position."""
        selected_mode = self.theme_map.get(button)
        if selected_mode and self.parent_window:
             print(f"SettingsDialog: Theme button '{button.text()}' clicked (mode: {selected_mode})")
             self.parent_window.set_theme_mode(selected_mode)
             # Parent applies theme, we just need to update our indicator position
             self.update_indicator_position(animate=True) 

    def apply_parent_style(self):
         """Applies parent style and then segmented control style."""
         if self.parent_window and hasattr(self.parent_window, 'styleSheet'):
             base_style = self.parent_window.styleSheet()
             self.setStyleSheet(base_style)
             # Re-apply/update segmented control styles
             self.apply_segmented_control_style()
             # Indicator position updated separately
             
    def update_indicator_position(self, animate=True):
        """Moves the indicator widget to the position of the checked button."""
        checked_button = self.theme_button_group.checkedButton()
        if not checked_button:
            # If somehow no button is checked, maybe check default (Auto)
            button_to_check = self.theme_map_inv.get("auto")
            if button_to_check:
                button_to_check.setChecked(True)
                checked_button = button_to_check
            else:
                return # Cannot determine position

        target_geo = checked_button.geometry()
        
        # Adjust target geometry slightly for padding/visual fit if needed
        # Example: Add a small margin inside the button bounds
        # margin = 1
        # target_geo.adjust(margin, margin, -margin, -margin)

        if animate:
            if self.indicator_anim.state() == QPropertyAnimation.Running:
                self.indicator_anim.stop()
            self.indicator_anim.setStartValue(self.theme_indicator.geometry())
            self.indicator_anim.setEndValue(target_geo)
            self.indicator_anim.start()
        else:
            self.theme_indicator.setGeometry(target_geo)
            
        # Ensure indicator stays behind buttons after move/resize
        self.theme_indicator.lower() 

    def showEvent(self, event):
        """Ensure correct button checked and indicator positioned on show."""
        if hasattr(self, 'theme_button_group') and self.parent_window:
            current_parent_mode = self.parent_window.theme_mode
            button_to_check = self.theme_map_inv.get(current_parent_mode)

            if button_to_check:
                # Check the button without triggering clicked signal logic
                button_to_check.blockSignals(True)
                button_to_check.setChecked(True)
                button_to_check.blockSignals(False)

            # Apply styles and update indicator position *after* checking the right button
            # Use QTimer to ensure layout is settled before getting geometry
            QtCore.QTimer.singleShot(0, lambda: self.update_indicator_position(animate=False))
            # Apply styles immediately though
            self.apply_parent_style() 

        super().showEvent(event)

    # Need resizeEvent to update indicator position if dialog resizes? Maybe not if fixed size.
    # def resizeEvent(self, event):
    #     super().resizeEvent(event)
    #     # Update position in case button geometries change
    #     QtCore.QTimer.singleShot(0, lambda: self.update_indicator_position(animate=False)) 

    def check_for_updates_clicked(self):
        """Handles the click on the 'Check for Updates' button."""
        if self.parent_window and hasattr(self.parent_window, 'check_for_updates'):
            print("SettingsDialog: 'Check for Updates' clicked, calling parent method...")
            # Disable button temporarily to avoid multiple clicks
            self.update_button.setEnabled(False)
            self.update_button.setText("Проверка...")
            # Call the actual check logic in the main window
            # Use a timer to allow the UI to update before potentially blocking work
            QtCore.QTimer.singleShot(50, self.parent_window.check_for_updates)
        else:
             QMessageBox.warning(self, "Ошибка", "Не удалось найти функцию проверки обновлений.")
             
    # --- Method to re-enable the button, called by parent window ---
    def enable_update_button(self):
         self.update_button.setEnabled(True)
         self.update_button.setText("Проверить обновления") 