import sys
import numpy as np

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QImage, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class FieldPanel(QFrame):
    def __init__(self, title: str, subtitle: str, index: int, fullscreen_callback):
        super().__init__()

        self.index = index
        self.fullscreen_callback = fullscreen_callback

        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()

        title_box = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 700; font-size: 14px;")

        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")

        title_box.addWidget(title_label)
        title_box.addWidget(subtitle_label)

        self.fullscreen_button = QPushButton("На весь екран")
        self.fullscreen_button.clicked.connect(lambda: self.fullscreen_callback(self.index))

        header.addLayout(title_box, stretch=1)
        header.addWidget(self.fullscreen_button)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: black; border-radius: 6px;")
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setMinimumSize(160, 160)

        layout.addLayout(header)
        layout.addWidget(self.image_label, stretch=1)

    def set_fullscreen_mode(self, enabled: bool):
        self.fullscreen_button.setText("Повернути 4 вікна" if enabled else "На весь екран")

    def set_pixmap(self, pixmap: QPixmap):
        self.image_label.setPixmap(pixmap)


class DifferenceFieldWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Difference Field D and Folding Levels — PySide6")
        self.resize(1200, 800)

        self.size = 128
        self.iteration = 0

        # Base immutable field
        self.D = None

        # Evolving folding levels
        self.D1 = None
        self.D2 = None
        self.D3 = None

        self.levels = []

        # Evolution parameters
        self.inertia = 0.85
        self.contrast = 0.18
        self.source_strength = 1.0 - self.inertia

        self.fullscreen_panel = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.step)

        self.panels = []

        self.build_ui()
        self.create_actions()
        self.reset_field()

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        controls = QHBoxLayout()

        self.step_button = QPushButton("Крок")
        self.step_button.clicked.connect(self.step)

        self.auto_button = QPushButton("Авто: вимкнено")
        self.auto_button.clicked.connect(self.toggle_auto)

        self.reset_button = QPushButton("Нове поле D")
        self.reset_button.clicked.connect(self.reset_field)

        self.size_input = QLineEdit(str(self.size))
        self.size_input.setFixedWidth(80)

        self.delay_input = QLineEdit("500")
        self.delay_input.setFixedWidth(80)

        self.iteration_label = QLabel("Ітерація: 0")

        controls.addWidget(self.step_button)
        controls.addWidget(self.auto_button)
        controls.addWidget(self.reset_button)

        controls.addSpacing(16)
        controls.addWidget(QLabel("Розмір D:"))
        controls.addWidget(self.size_input)

        controls.addSpacing(16)
        controls.addWidget(QLabel("Інтервал, мс:"))
        controls.addWidget(self.delay_input)

        controls.addSpacing(16)
        controls.addWidget(self.iteration_label)
        controls.addStretch(1)

        self.grid_container = QWidget()
        self.grid = QGridLayout(self.grid_container)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(10)

        titles = [
            ("D — базове поле", "Незмінна матриця унікальних значень у (0, 1)"),
            ("D₁ — згортання 1", "Згортання D + власна еволюція"),
            ("D₂ — згортання 2", "Згортання D₁ + власна еволюція"),
            ("D₃ — згортання 3", "Згортання D₂ + власна еволюція"),
        ]

        for i, (title, subtitle) in enumerate(titles):
            panel = FieldPanel(title, subtitle, i, self.toggle_fullscreen_panel)
            self.panels.append(panel)
            self.grid.addWidget(panel, i // 2, i % 2)

        self.grid.setRowStretch(0, 1)
        self.grid.setRowStretch(1, 1)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)

        main_layout.addLayout(controls)
        main_layout.addWidget(self.grid_container, stretch=1)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #111111;
            }

            QWidget {
                background-color: #111111;
                color: #eeeeee;
                font-family: Arial;
            }

            QFrame {
                background-color: #1c1c1c;
                border: 1px solid #333333;
                border-radius: 8px;
            }

            QLabel {
                color: #eeeeee;
                border: none;
            }

            QPushButton {
                background-color: #222222;
                color: #eeeeee;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 7px 10px;
            }

            QPushButton:hover {
                border-color: #7dd3fc;
            }

            QLineEdit {
                background-color: #222222;
                color: #eeeeee;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 6px;
            }
        """)

    def create_actions(self):
        step_action = QAction(self)
        step_action.setShortcut(QKeySequence(Qt.Key.Key_Space))
        step_action.triggered.connect(self.step)
        self.addAction(step_action)

        escape_action = QAction(self)
        escape_action.setShortcut(QKeySequence(Qt.Key.Key_Escape))
        escape_action.triggered.connect(self.exit_fullscreen_panel)
        self.addAction(escape_action)

    def create_unique_field(self, n: int) -> np.ndarray:
        total = n * n

        values = np.linspace(
            1.0 / (total + 1),
            total / (total + 1),
            total,
            dtype=np.float32,
        )

        np.random.shuffle(values)
        return values.reshape((n, n))

    def fold_2x2(self, field: np.ndarray) -> np.ndarray:
        h, w = field.shape
        h2 = h // 2
        w2 = w // 2

        cropped = field[: h2 * 2, : w2 * 2]

        return (
            cropped[0::2, 0::2]
            + cropped[0::2, 1::2]
            + cropped[1::2, 0::2]
            + cropped[1::2, 1::2]
        ) / 4.0

    def evolve_level(self, current: np.ndarray, source_folded: np.ndarray) -> np.ndarray:
        up = np.roll(current, -1, axis=0)
        down = np.roll(current, 1, axis=0)
        left = np.roll(current, -1, axis=1)
        right = np.roll(current, 1, axis=1)

        local_average = (up + down + left + right) / 4.0

        # Підсилення локальних відмінностей на самому рівні
        contrast_part = current + self.contrast * (current - local_average)

        # Вплив згортання з нижчого рівня
        mixed = self.inertia * contrast_part + self.source_strength * source_folded

        return np.clip(mixed, 0.0, 1.0)

    def calculate_levels(self):
        self.levels = [self.D, self.D1, self.D2, self.D3]

    def field_to_pixmap(self, field: np.ndarray, target_width: int, target_height: int) -> QPixmap:
        # Scale 0.0-1.0 to 0-255
        grayscale = (np.clip(field, 0, 1) * 255).astype(np.uint8)
        h, w = grayscale.shape

        # Create QImage and force a copy so the buffer doesn't disappear
        image = QImage(
            grayscale.data,
            w,
            h,
            w,  # bytesPerLine
            QImage.Format.Format_Grayscale8,
        ).copy()  # <--- CRITICAL: Copy the data

        pixmap = QPixmap.fromImage(image)

        return pixmap.scaled(
            max(1, target_width),
            max(1, target_height),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

    def render(self):
        if self.D is None:
            return

        self.calculate_levels()

        for i, panel in enumerate(self.panels):
            label = panel.image_label
            width = max(1, label.width())
            height = max(1, label.height())

            pixmap = self.field_to_pixmap(self.levels[i], width, height)
            panel.set_pixmap(pixmap)

        self.iteration_label.setText(f"Ітерація: {self.iteration}")

    def step(self):
        # D не змінюється.
        # Еволюціонують тільки D1, D2, D3.

        folded_D = self.fold_2x2(self.D)
        self.D1 = self.evolve_level(self.D1, folded_D)

        folded_D1 = self.fold_2x2(self.D1)
        self.D2 = self.evolve_level(self.D2, folded_D1)

        folded_D2 = self.fold_2x2(self.D2)
        self.D3 = self.evolve_level(self.D3, folded_D2)

        self.iteration += 1
        self.render()

    def toggle_auto(self):
        if self.timer.isActive():
            self.timer.stop()
            self.auto_button.setText("Авто: вимкнено")
            return

        try:
            delay = int(self.delay_input.text())
        except ValueError:
            delay = 500

        delay = max(50, delay)

        self.timer.start(delay)
        self.auto_button.setText("Авто: увімкнено")

    def reset_field(self):
        try:
            n = int(self.size_input.text())
        except ValueError:
            n = 128

        n = max(16, n)

        if n % 8 != 0:
            n = round(n / 8) * 8

        n = max(16, n)

        self.size = n
        self.size_input.setText(str(n))

        self.D = self.create_unique_field(self.size)

        self.D1 = self.fold_2x2(self.D)
        self.D2 = self.fold_2x2(self.D1)
        self.D3 = self.fold_2x2(self.D2)

        self.iteration = 0
        self.render()

    def toggle_fullscreen_panel(self, index: int):
        if self.fullscreen_panel == index:
            self.exit_fullscreen_panel()
            return

        self.fullscreen_panel = index

        for panel in self.panels:
            self.grid.removeWidget(panel)
            panel.hide()
            panel.set_fullscreen_mode(False)

        selected = self.panels[index]
        selected.show()
        selected.set_fullscreen_mode(True)
        self.grid.addWidget(selected, 0, 0, 2, 2)

        self.render()

    def exit_fullscreen_panel(self):
        if self.fullscreen_panel is None:
            return

        self.fullscreen_panel = None

        for panel in self.panels:
            self.grid.removeWidget(panel)

        for i, panel in enumerate(self.panels):
            panel.show()
            panel.set_fullscreen_mode(False)
            self.grid.addWidget(panel, i // 2, i % 2)

        self.render()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.render()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = DifferenceFieldWindow()
    window.show()

    sys.exit(app.exec())