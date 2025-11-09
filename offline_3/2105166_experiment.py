import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QGridLayout, QPushButton,
    QVBoxLayout, QLabel, QHBoxLayout, QMessageBox, QStackedLayout, QComboBox
)
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QRadialGradient, QFont
from PyQt6.QtCore import QSize, Qt, QTimer
from game_logic import GameState, AIPlayer, RandomAgent


class CellButton(QPushButton):
    def __init__(self, row, col):
        super().__init__()
        self.row = row
        self.col = col
        self.orb_count = 0
        self.color = None
        self.setFixedSize(QSize(60, 60))
        self.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border-radius: 8px;
                border: 1px solid #bbb;
            }
            QPushButton:hover {
                background-color: #e0e0ff;
            }
        """)

    def set_orb(self, count, color):
        self.orb_count = count
        self.color = color
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.orb_count > 0 and self.color:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            glow_color, orb_color = {
                'R': (QColor(255, 0, 0, 120), QColor("red")),
                'B': (QColor(0, 0, 255, 120), QColor("blue"))
            }.get(self.color, (None, None))

            if not orb_color:
                return

            center_x = self.width() // 2
            center_y = self.height() // 2

            gradient = QRadialGradient(center_x, center_y, 20)
            gradient.setColorAt(0, glow_color)
            gradient.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center_x - 20, center_y - 20, 40, 40)

            painter.setBrush(QBrush(orb_color))
            painter.setPen(QPen(Qt.GlobalColor.black, 1))

            radius = 15
            spacing = 15
            start_x = center_x - spacing * (self.orb_count - 1) / 2
            offset = radius // 2

            for i in range(self.orb_count):
                x = int(start_x + i * spacing - offset)
                y = center_y - offset
                painter.drawEllipse(x, y, radius, radius)


class ChainReactionGame(QWidget):
    def __init__(self, rows=6, cols=9, ai_players=None, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.game_state = GameState(rows, cols)
        self.ai_players = ai_players or {'R': None, 'B': None}
        self.move_delay_ms = 600

        self.timer = QTimer()
        self.timer.timeout.connect(self.ai_move)
        self.timer.setSingleShot(True)

        self.initUI()

        if self.is_ai_turn():
            self.safe_ai_move_start()

    def initUI(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        font = QFont("Arial", 14, QFont.Weight.Bold)
        self.status_label = QLabel("Red Player's Turn")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(font)
        main_layout.addWidget(self.status_label)

        self.grid = QGridLayout()
        self.grid.setSpacing(8)
        main_layout.addLayout(self.grid)

        self.cells = []
        for r in range(self.rows):
            row_cells = []
            for c in range(self.cols):
                cell = CellButton(r, c)
                cell.clicked.connect(self.cell_clicked)
                self.grid.addWidget(cell, r, c)
                row_cells.append(cell)
            self.cells.append(row_cells)

        btn_layout = QHBoxLayout()
        self.reset_btn = QPushButton("Reset Game")
        self.reset_btn.clicked.connect(self.reset_game)
        btn_layout.addWidget(self.reset_btn)

        self.back_btn = QPushButton("Back to Menu")
        self.back_btn.clicked.connect(self.go_back_to_menu)
        btn_layout.addWidget(self.back_btn)

        main_layout.addLayout(btn_layout)
        self.setWindowTitle('Chain Reaction')
        self.setStyleSheet("""
            ChainReactionGame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #d0e7ff, stop:1 #7aaaff);
                border-radius: 12px;
            }
        """)

    def safe_ai_move_start(self):
        if not self.timer.isActive():
            self.timer.start(self.move_delay_ms)

    def safe_ai_move_stop(self):
        if self.timer.isActive():
            self.timer.stop()

    def go_back_to_menu(self):
        self.safe_ai_move_stop()
        self.setParent(None)
        self.deleteLater()
        parent = self.parent()
        if isinstance(parent, QStackedLayout):
            parent.setCurrentIndex(0)
            return
        widget = self
        while widget:
            widget = widget.parentWidget()
            if widget:
                layout = widget.layout()
                if isinstance(layout, QStackedLayout):
                    layout.setCurrentIndex(0)
                    break

    def update_ui_from_state(self):
        self.setUpdatesEnabled(False)
        for r in range(self.rows):
            for c in range(self.cols):
                cell_state = self.game_state.grid[r][c]
                cell = self.cells[r][c]
                if cell.orb_count != cell_state['orb_count'] or cell.color != cell_state['color']:
                    cell.set_orb(cell_state['orb_count'], cell_state['color'])
        self.status_label.setText(
            f"{'Red' if self.game_state.current_player == 'R' else 'Blue'} Player's Turn"
        )
        self.setUpdatesEnabled(True)

    def cell_clicked(self):
        if self.game_state.is_game_over or self.is_ai_turn():
            return

        cell = self.sender()
        r, c = cell.row, cell.col

        print(f"Human {self.game_state.current_player} clicked on ({r},{c})")
        if self.game_state.place_orb(r, c):
            self.game_state.process_explosions()
            winner = self.game_state.check_winner()
            if winner:
                self.finish_game(winner)
            else:
                self.game_state.switch_player()
                self.update_ui_from_state()
                if self.is_ai_turn():
                    self.safe_ai_move_start()

    def is_ai_turn(self):
        return self.ai_players.get(self.game_state.current_player) is not None

    def stop_if_game_over(self):
        if self.game_state.is_game_over:
            self.safe_ai_move_stop()
            return True
        return False

    def ai_move(self):
        if self.stop_if_game_over():
            return

        ai = self.ai_players.get(self.game_state.current_player)
        if ai is None:
            self.safe_ai_move_stop()
            return

        move = ai.best_move(self.game_state)
        if not move:
            print(f"AI {self.game_state.current_player} has no valid moves.")
            self.safe_ai_move_stop()
            return
        print(f"AI {self.game_state.current_player} move: {move}")

        if move:
            r, c = move
            if self.game_state.place_orb(r, c):
                self.game_state.process_explosions()
                winner = self.game_state.check_winner()
                if winner:
                    self.finish_game(winner)
                    return
                else:
                    self.game_state.switch_player()
                    self.update_ui_from_state()
                    if self.is_ai_turn():
                        self.safe_ai_move_start()

    def finish_game(self, winner):
        self.game_state.is_game_over = True
        self.status_label.setText(f"{winner} Player Wins!")
        self.safe_ai_move_stop()
        QMessageBox.information(self, "Game Over", f"{winner} Player Wins!")
        self.update_ui_from_state()

    def reset_game(self):
        self.game_state.reset()
        self.update_ui_from_state()
        self.safe_ai_move_stop()


class ChainReactionApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chain Reaction Game")
        self.setMinimumSize(600, 480)
        self.layout = QStackedLayout()
        self.setLayout(self.layout)

        self.menu_widget = QWidget()
        self.menu_layout = QVBoxLayout(self.menu_widget)

        label_font = QFont("Arial", 16, QFont.Weight.Bold)

        self.menu_label = QLabel("Select Game Mode and AI Heuristic")
        self.menu_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.menu_label.setFont(label_font)
        self.menu_layout.addWidget(self.menu_label)

        self.ai_options = [
            'None (Human)', 
            'Random Move', 
            'AI Heuristic 1', 
            'AI Heuristic 2', 
            'AI Heuristic 3', 
            'AI Heuristic 4', 
            'AI Heuristic 5'
        ]

        h_layout = QHBoxLayout()
        self.red_player_combo = QComboBox()
        self.red_player_combo.addItems(self.ai_options)
        self.blue_player_combo = QComboBox()
        self.blue_player_combo.addItems(self.ai_options)

        h_layout.addWidget(QLabel("Red Player:"))
        h_layout.addWidget(self.red_player_combo)
        h_layout.addSpacing(30)
        h_layout.addWidget(QLabel("Blue Player:"))
        h_layout.addWidget(self.blue_player_combo)
        self.menu_layout.addLayout(h_layout)

        self.start_btn = QPushButton("Start Game")
        self.start_btn.clicked.connect(self.start_game)
        self.menu_layout.addWidget(self.start_btn)

        self.layout.addWidget(self.menu_widget)

    @staticmethod
    def create_ai(color, choice):
        if choice == 0:
            return None
        elif choice == 1:
            return RandomAgent(color)
        else:
            return AIPlayer(color, heuristic_id=choice)

    def start_game(self):
        red_choice = self.red_player_combo.currentIndex()
        blue_choice = self.blue_player_combo.currentIndex()

        ai_red = self.create_ai('R', red_choice)
        ai_blue = self.create_ai('B', blue_choice)

        if hasattr(self, "game_widget"):
            self.layout.removeWidget(self.game_widget)
            self.game_widget.deleteLater()

        self.game_widget = ChainReactionGame(ai_players={'R': ai_red, 'B': ai_blue})
        self.layout.addWidget(self.game_widget)
        self.layout.setCurrentWidget(self.game_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChainReactionApp()
    window.show()
    sys.exit(app.exec())
