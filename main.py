import sys
import os
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QHBoxLayout,
    QSlider,
    QStyle,
    QFrame,
)
from PyQt5.QtCore import Qt, QUrl, QTime, QTimer, QPoint, QSize
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget


class ControlPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box)
        self.setFixedHeight(50)
        self.setMouseTracking(True)

        # Set background color and opacity
        self.setStyleSheet(
            """
            ControlPanel {
                background-color: rgba(0, 0, 0, 180);
                border: none;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QSlider::handle:horizontal {
                background: white;
                border: 1px solid #5c5c5c;
                width: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 3px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
            }
        """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(0)

        # Create main controls layout (all in one line)
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        # Time and progress section
        self.current_time_label = QLabel("00:00:00")
        controls_layout.addWidget(self.current_time_label)

        self.progress_slider = ClickableSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 0)
        controls_layout.addWidget(self.progress_slider)

        self.remaining_time_label = QLabel("-00:00:00")
        controls_layout.addWidget(self.remaining_time_label)

        # Add small spacing
        controls_layout.addSpacing(20)

        # Playback controls
        self.backward_button = QPushButton()
        self.backward_button.setIcon(
            self.style().standardIcon(QStyle.SP_MediaSkipBackward)
        )
        self.backward_button.setFixedSize(32, 32)
        controls_layout.addWidget(self.backward_button)

        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.setFixedSize(32, 32)
        self.play_button.setEnabled(False)
        controls_layout.addWidget(self.play_button)

        self.forward_button = QPushButton()
        self.forward_button.setIcon(
            self.style().standardIcon(QStyle.SP_MediaSkipForward)
        )
        self.forward_button.setFixedSize(32, 32)
        controls_layout.addWidget(self.forward_button)

        # Add small spacing
        controls_layout.addSpacing(20)

        # Volume controls
        volume_label = QLabel("Volume:")
        controls_layout.addWidget(volume_label)

        self.volume_slider = ClickableSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(100)
        controls_layout.addWidget(self.volume_slider)

        self.volume_label = QLabel("100%")
        self.volume_label.setFixedWidth(45)
        controls_layout.addWidget(self.volume_label)

        layout.addLayout(controls_layout)


class ClickableSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Calculate the relative position clicked
            value = QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(), event.x(), self.width()
            )
            self.setValue(value)
            # Emit the sliderMoved signal for consistency with drag behavior
            self.sliderMoved.emit(value)
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Player")
        self.setGeometry(100, 100, 800, 600)
        self.setMouseTracking(True)

        # Create central widget and layout
        central_widget = QWidget()
        central_widget.setMouseTracking(True)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setMouseTracking(True)
        layout.addWidget(self.video_widget)

        # Create control panel as overlay
        self.control_panel = ControlPanel(self)
        self.update_control_panel_position()

        # Create media player
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.error.connect(self.handle_error)

        # Connect control panel signals
        self.control_panel.play_button.clicked.connect(self.toggle_playback)
        self.control_panel.backward_button.clicked.connect(
            lambda: self.seek_relative(-10000)
        )
        self.control_panel.forward_button.clicked.connect(
            lambda: self.seek_relative(10000)
        )
        self.control_panel.progress_slider.sliderMoved.connect(self.set_position)
        self.control_panel.volume_slider.valueChanged.connect(self.set_volume)

        # Setup hide timer
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.maybe_hide_controls)
        self.mouse_over_controls = False
        self.start_hide_timer()

        # Auto load and play demo video
        self.load_demo_video()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_control_panel_position()

    def update_control_panel_position(self):
        # Position the control panel at the bottom of the window
        panel_width = self.width()
        panel_height = self.control_panel.height()
        self.control_panel.setFixedWidth(panel_width)
        self.control_panel.move(0, self.height() - panel_height)

    def mouseMoveEvent(self, event):
        self.control_panel.show()
        self.start_hide_timer()
        super().mouseMoveEvent(event)

    def enterEvent(self, event):
        self.control_panel.show()
        self.start_hide_timer()
        super().enterEvent(event)

    def start_hide_timer(self):
        if (
            self.media_player.state() == QMediaPlayer.PlayingState
            and not self.mouse_over_controls
        ):
            self.hide_timer.start(3000)

    def maybe_hide_controls(self):
        if (
            self.media_player.state() == QMediaPlayer.PlayingState
            and not self.mouse_over_controls
        ):
            self.control_panel.hide()

    def toggle_playback(self):
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.hide_timer.stop()
            self.control_panel.show()
        else:
            self.media_player.play()
            self.start_hide_timer()
        self.update_play_button_icon()

    def load_demo_video(self):
        video_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "demo.mp4"
        )
        if os.path.exists(video_path):
            self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
            self.control_panel.play_button.setEnabled(True)
            self.control_panel.backward_button.setEnabled(True)
            self.control_panel.forward_button.setEnabled(True)
            self.media_player.play()
            self.update_play_button_icon()
        else:
            print(
                f"Error: demo.mp4 not found in {os.path.dirname(os.path.abspath(__file__))}"
            )

    def update_play_button_icon(self):
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.control_panel.play_button.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPause)
            )
        else:
            self.control_panel.play_button.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPlay)
            )

    def handle_error(self):
        print(f"Error: {self.media_player.errorString()}")
        self.control_panel.play_button.setEnabled(False)

    def duration_changed(self, duration):
        self.control_panel.progress_slider.setRange(0, duration)
        self.update_duration_info(duration)

    def position_changed(self, position):
        self.control_panel.progress_slider.setValue(position)
        self.update_time_info(position)

    def set_position(self, position):
        self.media_player.setPosition(position)

    def seek_relative(self, offset):
        current_pos = self.media_player.position()
        new_pos = max(0, min(current_pos + offset, self.media_player.duration()))
        self.media_player.setPosition(new_pos)

    def set_volume(self, volume):
        self.media_player.setVolume(volume)
        self.control_panel.volume_label.setText(f"{volume}%")

    def update_time_info(self, position):
        current = QTime(0, 0).addMSecs(position)
        remaining = QTime(0, 0).addMSecs(self.media_player.duration() - position)
        self.control_panel.current_time_label.setText(current.toString("hh:mm:ss"))
        self.control_panel.remaining_time_label.setText(
            f"-{remaining.toString('hh:mm:ss')}"
        )

    def update_duration_info(self, duration):
        total = QTime(0, 0).addMSecs(duration)
        self.control_panel.remaining_time_label.setText(
            f"-{total.toString('hh:mm:ss')}"
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.control_panel.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.control_panel:
            if event.type() == event.Enter:
                self.mouse_over_controls = True
                self.hide_timer.stop()
                return True
            elif event.type() == event.Leave:
                self.mouse_over_controls = False
                self.start_hide_timer()
                return True
        return super().eventFilter(obj, event)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
