import logging
from collections import defaultdict, deque
from functools import singledispatchmethod
from typing import Any, Optional, NamedTuple, Set, override
from PySide6.QtCore import Qt, QSize, QPoint, QRectF, QByteArray, QPropertyAnimation
from PySide6.QtWidgets import QWidget, QMessageBox, QGraphicsView, QGraphicsScene, QGraphicsObject, \
    QStyleOptionGraphicsItem, QGraphicsEllipseItem
from PySide6.QtGui import QPixmap, QPainter, QMouseEvent, QCursor, QPen
from shiftago.core import Colour, Slot, Side, Move, SlotsInLine
from shiftago.ui import load_image, AppEvent, AppEventEmitter
from .app_events import ReadyForFirstMoveEvent, AnimationFinishedEvent, MoveSelectedEvent, MarbleInsertedEvent, \
    MarbleShiftedEvent, BoardResetEvent
from .game_model import BoardViewModel, PlayerNature

BOARD_VIEW_SIZE = QSize(700, 700)


_logger = logging.getLogger(__name__)


class _AnimationManager:
    """
    _AnimationManager is responsible for managing animations in the game.
    It handles the execution and queuing of animations, ensuring that only one animation runs at a time.
    """

    def __init__(self, app_event_emitter: AppEventEmitter) -> None:
        """
        Initializes the _AnimationManager with the given event emitter.
        """
        self._app_event_emitter = app_event_emitter
        self._running_animation: Optional[QPropertyAnimation] = None
        self._waiting_animations: deque[QPropertyAnimation] = deque()

    def perform(self, animation: QPropertyAnimation, end_value: Any, duration: int) -> None:
        """
        Performs the given animation. If another animation is already running, the new animation is queued.

        Parameters:
        animation: The animation to be performed.
        end_value: The end value of the animation.
        duration: The duration of the animation in milliseconds.
        """
        animation.setEndValue(end_value)
        animation.setDuration(duration)
        animation.finished.connect(self._finished)
        if self._running_animation is not None:
            self._waiting_animations.append(animation)
        else:
            self._running_animation = animation
            self._running_animation.start()

    def is_animation_in_progress(self) -> bool:
        """
        Checks if an animation is currently in progress.
        """
        return self._running_animation is not None

    def _finished(self) -> None:
        """
        Handles the completion of the current animation and starts the next animation in the queue, if any.
        """
        if len(self._waiting_animations) > 0:
            self._running_animation = self._waiting_animations.popleft()
            self._running_animation.start()
        else:
            self._running_animation = None
            self._app_event_emitter.emit(AnimationFinishedEvent())


class BoardView(AppEventEmitter, QGraphicsView):

    class CursorPair(NamedTuple):
        """
        CursorPair is a named tuple that holds two QCursor objects: one for the enabled state
        and one for the disabled state. It provides a method to retrieve the appropriate cursor
        based on the enabled state.
        """
        enabled: QCursor
        disabled: QCursor

        def get(self, enabled: bool) -> QCursor:
            """
            Returns the appropriate cursor based on the enabled state.
            """
            return self.enabled if enabled else self.disabled

    class BoardScene(QGraphicsScene):
        """
        BoardScene is a custom QGraphicsScene that represents the game board.
        It handles the rendering of the game board and the interaction with the game elements.
        """

        IMAGE_SIZE = QSize(600, 600)
        IMAGE_OFFSET_X = (BOARD_VIEW_SIZE.width() - IMAGE_SIZE.width()) // 2
        IMAGE_OFFSET_Y = (BOARD_VIEW_SIZE.height() - IMAGE_SIZE.height()) // 2
        SLOT_SIZE = QSize(59, 59)

        class Marble(QGraphicsObject):
            """
            Marble is a custom QGraphicsObject that represents a marble on the game board.
            """

            SIZE = QSize(70, 70)

            def __init__(self, pixmap: QPixmap, position: QPoint) -> None:
                """
                Initializes the Marble with the given pixmap and position.
                """
                super().__init__()
                self.setPos(position)
                self._pixmap = pixmap

            @override
            def boundingRect(self) -> QRectF:  # pylint: disable=invalid-name
                """
                Returns the bounding rectangle of the marble.
                """
                return QRectF(0, 0, self.SIZE.width(), self.SIZE.height())

            @override
            def paint(self, painter: QPainter,
                      option: QStyleOptionGraphicsItem,  # pylint: disable=unused-argument
                      widget: Optional[QWidget]) -> None:  # pylint: disable=unused-argument
                """
                Paints the marble on the game board.
                """
                painter.drawPixmap(0, 0, self._pixmap)

        def __init__(self, animation_manager: _AnimationManager) -> None:
            """
            Initializes the BoardScene with the given animation manager.
            """
            super().__init__()
            board_pixmap = load_image('shiftago_board.jpg').scaled(self.IMAGE_SIZE)
            self._marble_pixmaps: dict[Colour, QPixmap] = {
                Colour.BLUE: load_image('blue_marble.png').scaled(self.Marble.SIZE),
                Colour.ORANGE: load_image('orange_marble.png').scaled(self.Marble.SIZE)
            }
            self.setSceneRect(0, 0, BOARD_VIEW_SIZE.width(), BOARD_VIEW_SIZE.height())
            self.addPixmap(board_pixmap).setPos(QPoint(self.IMAGE_OFFSET_X, self.IMAGE_OFFSET_Y))
            self._marbles: dict[Slot, BoardView.BoardScene.Marble] = {}
            self._winning_line_markers: dict[Slot, QGraphicsEllipseItem] = {}
            self._animation_manager = animation_manager
            self._move_selection_enabled: bool = False

        def insert_marble(self, slot: Slot, colour: Colour) -> None:
            """
            Inserts a marble into the specified slot with the given colour.
            """
            marble = self.Marble(self._marble_pixmaps[colour], self.position_of(slot))
            self._marbles[slot] = marble
            marble.setOpacity(0.0)
            self.addItem(marble)
            self._animation_manager.perform(QPropertyAnimation(marble, QByteArray(b'opacity')),
                                            1.0, 500)

        def shift_marble(self, slot: Slot, direction: Side) -> None:
            """
            Shifts a marble from the specified slot in the given direction.
            """
            target_slot = slot.neighbour(direction)
            marble = self._marbles.pop(slot)
            self._marbles[target_slot] = marble
            self._animation_manager.perform(QPropertyAnimation(marble, QByteArray(b'pos')),
                                            self.position_of(target_slot), 500)

        def reset(self) -> None:
            """
            Resets the game board by removing all marbles and winning line markers.
            """
            for item in self._marbles.values():
                self.removeItem(item)
            self._marbles.clear()
            for item in self._winning_line_markers.values():
                self.removeItem(item)
            self._winning_line_markers.clear()

        def mark_lines(self, lines: Set[SlotsInLine]) -> None:
            """
            Marks the winning lines on the game board.
            """
            pen = QPen(Qt.GlobalColor.darkGreen, 8)
            for line in lines:
                for slot in line.slots:
                    if self._winning_line_markers.get(slot) is None:
                        pos = self.position_of(slot)
                        marker = QGraphicsEllipseItem(pos.x() - 2, pos.y() - 2,
                                                      self.Marble.SIZE.width() + 2, self.Marble.SIZE.height() + 4)
                        marker.setPen(pen)
                        self._winning_line_markers[slot] = marker
                        self.addItem(marker)

        @classmethod
        def position_of(cls, slot: Slot) -> QPoint:
            """
            Returns the position of the given slot on the game board.
            """
            return QPoint(cls.IMAGE_OFFSET_X + 36 + slot.hor_pos * (cls.Marble.SIZE.width() + 6),
                          cls.IMAGE_OFFSET_Y + 38 + slot.ver_pos * (cls.Marble.SIZE.height() + 6))

        @classmethod
        def determine_side(cls, cursor_pos: QPoint) -> Optional[Side]:
            """
            Determines the side of the board based on the cursor position.
            """
            cursor_pos_x = cursor_pos.x()
            cursor_pos_y = cursor_pos.y()

            left_bound = cls.IMAGE_OFFSET_X + cls.Marble.SIZE.width() // 3
            right_bound = cls.IMAGE_OFFSET_X + cls.IMAGE_SIZE.width() - cls.Marble.SIZE.width() // 3
            top_bound = cls.IMAGE_OFFSET_Y + cls.Marble.SIZE.height() // 3
            bottom_bound = cls.IMAGE_OFFSET_Y + cls.IMAGE_SIZE.height() - cls.Marble.SIZE.height() // 3

            if cursor_pos_x < left_bound:
                if top_bound < cursor_pos_y < bottom_bound:
                    return Side.LEFT
            elif cursor_pos_x > right_bound:
                if top_bound < cursor_pos_y < bottom_bound:
                    return Side.RIGHT
            elif cursor_pos_y < top_bound:
                if left_bound < cursor_pos_x < right_bound:
                    return Side.TOP
            elif cursor_pos_y > bottom_bound:
                if left_bound < cursor_pos_x < right_bound:
                    return Side.BOTTOM
            return None

        @classmethod
        def determine_insert_pos(cls, side: Side, cursor_pos: int) -> Optional[int]:
            """
            Determines the insert position on the board based on the side and cursor position.
            """
            if side.is_vertical:
                board_relative_pos = cursor_pos - (cls.IMAGE_OFFSET_Y + 50)
                insert_pos = board_relative_pos // (cls.SLOT_SIZE.height() + 18)
                if 0 <= insert_pos <= 6 and (
                        board_relative_pos % (cls.SLOT_SIZE.height() + 18)) < cls.SLOT_SIZE.height():
                    return insert_pos
            else:
                board_relative_pos = cursor_pos - (cls.IMAGE_OFFSET_X + 50)
                insert_pos = board_relative_pos // (cls.SLOT_SIZE.width() + 18)
                if 0 <= insert_pos <= 6 and (
                        board_relative_pos % (cls.SLOT_SIZE.width() + 18)) < cls.SLOT_SIZE.width():
                    return insert_pos
            return None

    def __init__(self, model: BoardViewModel, main_window_title: str) -> None:
        """
        Initializes the BoardView with the given model and main window title.
        """
        super().__init__()

        self._board_scene = self.BoardScene(_AnimationManager(self))
        self.setScene(self._board_scene)

        model.connect_with(self._update_from_model)
        self._model = model
        self._main_window_title = main_window_title

        self._neutral_cursor = QCursor(Qt.CursorShape.ArrowCursor)

        cursor_hor_size = QSize(70, 122)
        cursor_ver_size = QSize(122, 70)

        self._insert_cursors: dict[Colour, dict[Side, BoardView.CursorPair]] = defaultdict(dict)
        for colour in (Colour.BLUE, Colour.ORANGE):
            cn = colour.name.lower()
            for side in Side:
                sn = side.name.lower()
                csize = cursor_hor_size if side.is_horizontal else cursor_ver_size
                self._insert_cursors[colour][side] = self.CursorPair(
                    QCursor(load_image(f'insert_{cn}_{sn}_enabled.png').scaled(csize), -1, -1),
                    QCursor(load_image(f'insert_{cn}_{sn}_disabled.png').scaled(csize), -1, -1))

    @property
    def model(self) -> BoardViewModel:
        """
        Returns the model associated with the BoardView.
        """
        return self._model

    @property
    def move_selection_enabled(self) -> bool:
        """
        Returns whether move selection is enabled.
        """
        return self._move_selection_enabled

    @move_selection_enabled.setter
    def move_selection_enabled(self, new_val: bool) -> None:
        """
        Sets whether move selection is enabled.
        """
        self._move_selection_enabled = new_val
        self.setMouseTracking(new_val)
        if not new_val:
            self.setCursor(self._neutral_cursor)

    @singledispatchmethod
    def _update_from_model(self, event: AppEvent) -> None:
        """
        Updates the view based on the given model event.
        """
        raise ValueError(f"Unsupported event type: {event.__class__}")

    @_update_from_model.register
    def _(self, event: MarbleInsertedEvent) -> None:
        """
        Handles the MarbleInsertedEvent and updates the view accordingly.
        """
        _logger.debug("Model event occurred: %s", event)
        self._board_scene.insert_marble(event.slot, event.colour)

    @_update_from_model.register
    def _(self, event: MarbleShiftedEvent) -> None:
        """
        Handles the MarbleShiftedEvent and updates the view accordingly.
        """
        _logger.debug("Model event occurred: %s", event)
        self._board_scene.shift_marble(event.slot, event.direction)

    @_update_from_model.register
    def _(self, event: BoardResetEvent) -> None:
        """
        Handles the BoardResetEvent and updates the view accordingly.
        """
        _logger.debug("Model event occurred: %s", event)
        self._board_scene.reset()

    @override
    def mouseMoveEvent(self, ev: QMouseEvent) -> None:  # pylint: disable=invalid-name
        """
        Handles the mouse move event to update the cursor based on the current state.
        """
        if self._move_selection_enabled:
            assert self._model.whose_turn_it_is is not None, "current_player not set!"
            side, insert_pos = self._determine_move_args(ev.pos())
            new_cursor = self._neutral_cursor
            if side is not None:
                cursor_pair = self._insert_cursors[self._model.whose_turn_it_is.colour][side]
                new_cursor = cursor_pair.get(insert_pos is not None)
            self.setCursor(new_cursor)

    @override
    def mousePressEvent(self, ev: QMouseEvent) -> None:  # pylint: disable=invalid-name
        """
        Handles the mouse press event to select a move based on the cursor position.
        """
        if (self._move_selection_enabled and
                ev.button() == Qt.MouseButton.LeftButton):
            side, insert_pos = self._determine_move_args(ev.pos())
            if side is not None and insert_pos is not None:
                self.emit(MoveSelectedEvent(Move(side, insert_pos)))

    def _determine_move_args(self, ev_pos: QPoint) -> tuple[Optional[Side], Optional[int]]:
        """
        Determines the side and insert position for a move based on the cursor position.
        Returns:
        A tuple containing the side of the board and the insert position, or (None, None)
        if the cursor is not near a valid insert position.
        """
        side = self.BoardScene.determine_side(ev_pos)
        if side is not None:
            insert_pos = self.BoardScene.determine_insert_pos(
                side, ev_pos.y() if side.is_vertical else ev_pos.x())
            if insert_pos is not None and self._model.is_insertion_possible(side, insert_pos):
                return (side, insert_pos)
            return (side, None)
        return (None, None)

    def show_game_over(self):
        """
        Displays a message box indicating that the game is over and shows the result.

        The message box will display whether the game ended in a draw or which player won.
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(self._main_window_title)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText("Game over!")
        game_over_condition = self._model.game_over_condition
        assert game_over_condition is not None, "Game not yet over!"
        if game_over_condition.winner is not None:
            msg_box.setInformativeText(f"{game_over_condition.winner.name} has won.")
        else:
            msg_box.setInformativeText("It has ended in a draw.")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec_()

    def mark_lines(self, lines: Set[SlotsInLine]) -> None:
        """
        Marks the winning lines on the game board.
        """
        self._board_scene.mark_lines(lines)

    def show_starting_player(self) -> None:
        """
        Displays a message box indicating the starting player.

        The message box will display the colour of the starting player and whether it is the human or the computer.
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(self._main_window_title)
        msg_box.setIcon(QMessageBox.Icon.Information)
        current_player = self._model.whose_turn_it_is
        assert self._model.count_occupied_slots() == 0
        msg_box.setText(f"Starting player: {current_player.colour.name}")
        if current_player.nature is PlayerNature.HUMAN:
            msg_box.setInformativeText("That's you.")
        else:
            msg_box.setInformativeText("That's the computer.")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec_()
        self.emit(ReadyForFirstMoveEvent())
