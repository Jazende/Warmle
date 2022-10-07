import os
import sys
import itertools
import random

from enum              import Enum

from PySide6.QtCore    import Qt, QThread, QObject, QSize, Signal
from PySide6.QtGui     import QIcon
from PySide6.QtWidgets import QApplication, QGridLayout, QMainWindow
from PySide6.QtWidgets import QLineEdit, QLabel, QWidget, QSizePolicy
from PySide6.QtWidgets import QButtonGroup, QRadioButton, QPushButton
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from lw5 import words as all_words_5
from lw4 import words as all_words_4
from lw3 import words as all_words_3
from lw2 import words as all_words_2
from lw1 import words as all_words_1

class Results(Enum):
    NONE = -1
    FAR = 0
    CLOSE = 1
    CORRECT = 2

class MainScreen(QMainWindow):
    # Subclassed versions of QMainWindow as to not clutter the main code with boilerplate.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        super().setWindowIcon(QIcon(os.path.join(os.getcwd(), 'warmle.ico')))
        self._title = ""

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value
        self.setWindowTitle(value)

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        width, height = value
        width = max(width, 300)
        height = max(height, 300)
        self._size = (width, height)
        new_size = QSize(width, height)
        self.resize(new_size)

    @size.getter
    def size(self):
        return self._size

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        x, y = value
        x = max(x, 5)
        y = max(y, 30)
        self._position = value
        self.setGeometry(x, y, self._size[0], self._size[1])

class LineEditWithObject(QLineEdit):
    focused = Signal(QObject)

    def __init__(self, row, col, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet("background-color: white; color: black; font: bold;")
        self.parent = parent
        self.row    = row
        self.col    = col
        self.result = 0
        super().textEdited.connect(self.fn_text_edited) # Edited: whenever user changes, Changed: whenever user or code changes
        super().returnPressed.connect(self.fn_line_completed) # Send via function so can send info with it

    @property
    def result(self):
        return self._result
    
    @result.setter
    def result(self, value):
        if hasattr(self, '_result') and not value == self._result:
            if value == Results.FAR or value == Results.NONE:
                self.setStyleSheet("background-color: white; color: black; font: bold;")
            if value == Results.CLOSE:
                self.setStyleSheet("background-color: yellow; color: black; font: bold;")
            if value == Results.CORRECT:
                self.setStyleSheet("background-color: green; color: yellow; font: bold;")
        self._result = value

    def fn_text_edited(self, new_text):
        # Fires whenever the user made any changes
        if not new_text.upper() == new_text:
            self.setText(new_text.upper())
        self.parent.focus_item(self.row, self.col+1)
    
    def fn_line_completed(self):
        self.parent.line_completed(self.row)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if event.key() == 16777219 and self.text() == "":
            self.parent.focus_item(self.row, self.col-1)

    def focusInEvent(self, event):
        if self.isReadOnly():
            return
        self.focused.emit(self)

class VersionSelectRadioButton(QRadioButton):
    def __init__(self, id_, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id_    = id_
        self.offset = 4 - id_

class ShowWordsSelectRadiobutton(QRadioButton):
    def __init__(self, show_words, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_words = show_words

class AvailableLetterWidget(QLineEdit):
    clicked = Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # super().textEdited.connect(self.fn_text_edited
        super().selectionChanged.connect(self.fn_selection_changed)
        self.selection_funcction = None

    # def fn_text_edited(self, new_text):
        # self.parent().focus_widget().setText(new_text)

    def fn_selection_changed(self):
        # self.setSelection(0, 0)
        self.deselect()

    def mouseReleaseEvent(self, event):
        self.clicked.emit(self.text())

    def focusChangedEvent(self, event):
        print(f'{event=}')

class KeyBoardWidget(QWidget):
    clicked = Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_ui()

    def setup_ui(self):
        self.layout = QGridLayout()
        self.letters     = [AvailableLetterWidget(letter) for letter in self.parent().base_letters[:26]]
        self.letters.append(AvailableLetterWidget(' '))
        self.letters.append(AvailableLetterWidget('↲'))
        for row in range(4):
            for col in range(7):
                widget = self.letters[row*7+col]
                widget.setAlignment(Qt.AlignCenter)
                widget.setContextMenuPolicy(Qt.PreventContextMenu)
                widget.setMaxLength(1)
                widget.setFixedSize(40, 40)
                widget.setReadOnly(True)
                widget.clicked.connect(self.fn_letter_clicked)
                self.layout.addWidget(widget, row, col)
        self.setLayout(self.layout)

    def set_letters(self, allowed_letters, result):
        for widget in self.letters:
            t = widget.text()
            match (t, t in allowed_letters, result):
                case '⟵', _, _:
                    continue
                case '↲', _, _:
                    continue
                case '#', _, _:
                    continue
                case _, False, _:
                    widget.setStyleSheet("background-color: grey; color: grey;")
                case _, True, Results.FAR:
                    widget.setStyleSheet("background-color: white; color: black; font: bold;")
                case _, True, Results.CLOSE:
                    widget.setStyleSheet("background-color: yellow; color: black; font: bold;")
                case _, True, Results.CORRECT:
                    widget.setStyleSheet("background-color: green; color: yellow; font: bold;")

    def fn_letter_clicked(self, letter):
        self.clicked.emit(letter)

class Warmle(MainScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_letters       = "ABCDEFGHIJKLMNOPQRSTUVWXYZ####### "
        self.title              = "Play Warmle"
        self.size               = (300, 400)
        self.position           = (300, 300)
        self.lines              = 8
        self.columns            = 5
        self.possibilities      = { x: "".join(l for l in self.base_letters) for x in range(self.columns) }
        self.all_words          = [word.upper()          for word in all_words_5]
        self.all_words         += [word.upper() + ' '    for word in all_words_4]
        self.all_words         += [word.upper() + '  '   for word in all_words_3]
        self.all_words         += [word.upper() + '   '  for word in all_words_2]
        self.all_words         += [word.upper() + '    ' for word in all_words_1]
        self.all_words.sort()
        self.possible_solutions = []
        self.setup_ui()
        self.game_version       = self.version_warmle
        self.offset             = self.game_version.offset
        self.word_to_find       = None
        self.current_line       = 0
        self.last_selected      = None
        self.new_game()

    @property
    def current_line(self):
        return self._current_line
    
    @current_line.setter
    def current_line(self, value):
        self._current_line = min(self.lines-1, max(0, value))

    def setup_ui(self):
        self.setup_version_widget()
        self.setup_warmle_widget()
        self.setup_show_words_widget()

        self.new_game_button = QPushButton('New Game')
        self.new_game_button.clicked.connect(self.new_game)

        self.keyboard = KeyBoardWidget(self)
        self.keyboard.clicked.connect(self.letter_clicked)

        layout = QGridLayout()
        layout.setAlignment(Qt.AlignTop)
        layout.addWidget(self.version_widget,     0, 0)
        layout.addWidget(self.new_game_button,    1, 0)
        layout.addWidget(self.warmle_widget,      2, 0)
        layout.addWidget(self.show_words_widget,  3, 0)
        layout.addWidget(self.keyboard,           4, 0)
        layout.setRowStretch(1, 1)
       
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def setup_version_widget(self):
        self.version_widget = QWidget()
        self.version_layout = QGridLayout()

        self.version_container         = QButtonGroup()
        self.version_warmle            = VersionSelectRadioButton(1, text="Warmle")
        self.version_warmle_super      = VersionSelectRadioButton(2, text="Warmle SUPER")
        self.version_warmle_super_plus = VersionSelectRadioButton(3, text="Warmle SUPER +")
        self.version_container.addButton(self.version_warmle)
        self.version_container.addButton(self.version_warmle_super)
        self.version_container.addButton(self.version_warmle_super_plus)
        self.version_warmle.setChecked(True)
        self.version_container.buttonClicked.connect(self.select_version)

        self.version_layout.addWidget(self.version_warmle,            0, 0, 1, 1)
        self.version_layout.addWidget(self.version_warmle_super,      0, 1, 1, 1)
        self.version_layout.addWidget(self.version_warmle_super_plus, 0, 2, 1, 1)
        self.version_widget.setLayout(self.version_layout)
        self.version_widget.setContextMenuPolicy(Qt.PreventContextMenu)
        self.version_widget.setMaximumHeight(35)

    def setup_warmle_widget(self):
        self.warmle_widget = QWidget()
        self.warmle_layout = QGridLayout()
        self.warmle_layout.setHorizontalSpacing(5)
        self.warmle_layout.setVerticalSpacing(5)
        self.inputs = []
        for row in range(self.lines):
            new_line = []
            for col in range(self.columns):
                new_qle = LineEditWithObject(row, col, self)
                new_qle.focused.connect(self.update_keyboard)
                new_qle.setAlignment(Qt.AlignCenter)
                # Prevent right click menu
                new_qle.setContextMenuPolicy(Qt.PreventContextMenu)
                new_qle.setMaxLength(1)
                new_qle.setFixedSize(40, 40)
                new_line.append(new_qle)
                self.warmle_layout.addWidget(new_qle, row, col, 1, 1)
            self.inputs.append(new_line)

        self.possible_solutions_list = QListWidget()
        self.possible_solutions_list.itemClicked.connect(self.select_word_from_list)
        self.possible_solutions_list.setVisible(False)
        self.warmle_layout.addWidget(self.possible_solutions_list, 0, 6, self.lines, 1)

        self.warmle_widget.setLayout(self.warmle_layout)
        # Prevent right click menu
        self.warmle_widget.setContextMenuPolicy(Qt.PreventContextMenu)

    def setup_show_words_widget(self):
        self.show_words_widget = QWidget()
        self.show_words_layout = QGridLayout()

        self.show_words_container = QButtonGroup()
        self.show_words_true      = ShowWordsSelectRadiobutton(show_words=True,  text="Show Words")
        self.show_words_false     = ShowWordsSelectRadiobutton(show_words=False, text="Don't Show Words")
        self.show_words_container.addButton(self.show_words_true)
        self.show_words_container.addButton(self.show_words_false)
        self.show_words_container.buttonClicked.connect(self.toggle_show_words)
        self.show_words_false.setChecked(True)

        self.show_words_layout.addWidget(self.show_words_true,  0, 0)
        self.show_words_layout.addWidget(self.show_words_false, 0, 1)

        self.show_words_widget.setLayout(self.show_words_layout)

    def new_game(self):
        self.current_line  = 0
        self.word_to_find  = random.choice(self.all_words)
        self.offset        = self.game_version.offset

        for row in self.inputs:
            for qle in row:
                qle.setText("")
                qle.setReadOnly(True if not qle.row == 1 else False)
                qle.result = Results.NONE
        
        first_letters = [random.choice(self.base_letters[:26]+self.base_letters[-1]) for _ in range(5)]
        for idx, qle in enumerate(self.inputs[0]):
            qle.setText(first_letters[idx])
        self.line_completed(0)

        # self.inputs[0][0].setFocus()
        # self.possible_solutions_list.clear()

        # for word in self.all_words:
        #     QListWidgetItem(word, self.possible_solutions_list)

    def focus_item(self, row, col):
        row = min(self.lines-1, max(0, row))
        col = min(self.columns-1, max(0, col))
        self.inputs[row][col].setFocus()
        self.inputs[row][col].selectAll()
        self.last_selected = self.inputs[row][col]

    def select_version(self):
        self.game_version  = self.version_container.checkedButton()

    def select_word_from_list(self, item):
        text = item.text()
        for qle in self.inputs[self.current_line]:
            qle.setText(text[qle.col])
        self.focus_item(self.current_line, self.columns-1)

    def compare_letters(self, target, inputted, offset):
        idx_target   = self.base_letters.find(target)
        idx_inputted = self.base_letters.find(inputted)
        if idx_target == idx_inputted:
            return Results.CORRECT
        elif abs(idx_target - idx_inputted) <= offset:
            return Results.CLOSE
        else:
            return Results.FAR

    def line_completed(self, row):
        if any(qle.text() == "" for qle in self.inputs[self.current_line]):
            return
        for qle in self.inputs[self.current_line]:
            qle.setReadOnly(True)
            qle.result = self.compare_letters(self.word_to_find[qle.col], qle.text(), self.offset)

        if all(qle.result == Results.CORRECT for qle in self.inputs[self.current_line]): # All letters correct: game is won
            return

        self.calculate_valid_words()

        self.current_line += 1
        if self.current_line == self.lines: # Reached last line: 
            return                          # Game is over

        for qle in self.inputs[min(self.lines-1, self.current_line)]:
            qle.setReadOnly(False)
        self.focus_item(self.current_line, 0)

    def calculate_valid_words(self):
        # Calculating valid letters per column into self.possibilities
        for column in range(self.columns):
            possible_letters = {letter for letter in self.base_letters}

            for qle in [self.inputs[row][column] for row in range(self.lines)]:
                if (text := qle.text()) == "":
                    continue
                
                start_index = max(0, self.base_letters.find(text) - self.offset)
                stop_index  = min(len(self.base_letters)-1, self.base_letters.find(text) + self.offset)

                res_letters = {x for x in self.base_letters[start_index:stop_index+1]}

                if qle.result == Results.FAR or qle.result == Results.NONE:
                    possible_letters = possible_letters - res_letters
                elif qle.result == Results.CLOSE:
                    possible_letters = possible_letters & res_letters - {text, }
                elif qle.result == Results.CORRECT:
                    possible_letters = {text}
                else:
                    print(f'Shouldn\'t get to this point in self.calculate_valid_words')
                    possible_letters = self.base_letters
            self.possibilities[column] = possible_letters
        
        self.possible_solutions_list.clear()
        for word in self.all_words:
            if all(word[idx] in self.possibilities[idx] for idx in range(self.columns)):
                QListWidgetItem(word, self.possible_solutions_list)

    def toggle_show_words(self):
        if self.show_words_container.checkedButton().show_words:
            self.possible_solutions_list.setVisible(True)
        else:
            self.possible_solutions_list.setVisible(False)

    def update_keyboard(self, qle):
        self.last_selected = qle
        self.keyboard.set_letters(self.possibilities[qle.col], self.inputs[qle.row-1][qle.col].result)

    def letter_clicked(self, letter):
        if letter == '↲':
            self.line_completed(self.last_selected.row)
        else:
            self.last_selected.setText(letter)
            self.last_selected.fn_text_edited(letter)

def main(*args):
    app  = QApplication(*args)
    warmle = Warmle()
    warmle.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main(sys.argv)
