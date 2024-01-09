import logging
from collections import defaultdict, deque
from functools import singledispatchmethod
from typing import Optional, NamedTuple
from importlib.resources import path as resrc_path
from PySide2.QtCore import Qt, QSize, QPoint, QRectF, QByteArray, QPropertyAnimation
from PySide2.QtWidgets import QWidget, QMessageBox, QGraphicsView, QGraphicsScene, QGraphicsObject, \
    QStyleOptionGraphicsItem
from PySide2.QtGui import QPixmap, QPainter, QMouseEvent, QCursor
from shiftago.core import Colour, Slot, Side, Move
import shiftago.ui.images
from .hmvc import AppEvent, AppEventEmitter
from .app_events import ReadyForFirstMoveEvent, AnimationFinishedEvent, MoveSelectedEvent, MarbleInsertedEvent, \
    MarbleShiftedEvent
from .game_model import BoardViewModel, PlayerNature

BOARD_VIEW_SIZE = QSize(700, 700)


_logger = logging.getLogger(__name__)


def _load_image(image_resource: str) -> QPixmap:
    with resrc_path(shiftago.ui.images, image_resource) as path:
        return QPixmap(str(path))


class BoardView(AppEventEmitter, QGraphicsView):

    class CursorPair(NamedTuple):
        enabled: QCursor
        disabled: QCursor

        def get(self, enabled: bool) -> QCursor:
            return self.enabled if enabled else self.disabled

    class BoardScene(QGraphicsScene):

        IMAGE_SIZE = QSize(600, 600)
        IMAGE_OFFSET_X = (BOARD_VIEW_SIZE.width() - IMAGE_SIZE.width()) // 2
        IMAGE_OFFSET_Y = (BOARD_VIEW_SIZE.height() - IMAGE_SIZE.height()) // 2
        SLOT_SIZE = QSize(59, 59)

        class Marble(QGraphicsObject):

            SIZE = QSize(70, 70)

            def __init__(self, pixmap: QPixmap, position: QPoint) -> None:
                super().__init__()
                self.setPos(position)
                self._pixmap = pixmap

            def boundingRect(self) -> QRectF:  # pylint: disable=invalid-name
                return QRectF(0, 0, self.SIZE.width(), self.SIZE.height())

            def paint(self, painter: QPainter,
                      option: QStyleOptionGraphicsItem,  # pylint: disable=unused-argument
                      widget: Optional[QWidget]) -> None:  # pylint: disable=unused-argument
                painter.drawPixmap(0, 0, self._pixmap)

        def __init__(self, app_event_emitter: AppEventEmitter, model: BoardViewModel) -> None:
            super().__init__()
            board_pixmap = _load_image('shiftago_board.jpg').scaled(self.IMAGE_SIZE)
            model.connect_with(self.update_from_model)
            self._app_event_emitter = app_event_emitter
            self._model = model
            self._marble_pixmaps: dict[Colour, QPixmap] = {
                Colour.BLUE: _load_image('blue_marble.png').scaled(self.Marble.SIZE),
                Colour.ORANGE: _load_image('orange_marble.png').scaled(self.Marble.SIZE)
            }
            self.setSceneRect(0, 0, BOARD_VIEW_SIZE.width(), BOARD_VIEW_SIZE.height())
            self.addPixmap(board_pixmap).setPos(QPoint(self.IMAGE_OFFSET_X, self.IMAGE_OFFSET_Y))
            self._marbles: dict[Slot, BoardView.BoardScene.Marble] = {}
            self._running_animation: Optional[QPropertyAnimation] = None
            self._waiting_animations: deque[QPropertyAnimation] = deque()
            self._move_selection_enabled: bool = False

        @singledispatchmethod
        def update_from_model(self, event: AppEvent) -> None:
            raise ValueError(f"Unsupported event type: {event.__class__}")

        @update_from_model.register
        def _(self, event: MarbleInsertedEvent) -> None:
            _logger.debug("Model event occurred: %s", event)
            slot: Slot = event.slot
            colour = self._model.colour_at(slot)
            assert colour is not None, f"{slot} is not occupied!"
            marble = self.Marble(self._marble_pixmaps[colour], self.position_of(slot))
            self._marbles[slot] = marble
            marble.setOpacity(0.0)
            self.addItem(marble)
            animation = QPropertyAnimation(marble, QByteArray(b'opacity'))
            animation.setEndValue(1.0)
            animation.setDuration(500)
            self.run_animation(animation)

        @update_from_model.register
        def _(self, event: MarbleShiftedEvent) -> None:
            _logger.debug("Model event occurred: %s", event)
            from_slot: Slot = event.slot
            to_slot = from_slot.neighbour(event.direction)
            marble = self._marbles.pop(from_slot)
            self._marbles[to_slot] = marble
            animation = QPropertyAnimation(marble, QByteArray(b'pos'))
            animation.setEndValue(self.position_of(to_slot))
            animation.setDuration(500)
            self.run_animation(animation)

        def run_animation(self, animation: QPropertyAnimation) -> None:
            def finished() -> None:
                if len(self._waiting_animations) > 0:
                    self._running_animation = self._waiting_animations.popleft()
                    self._running_animation.start()
                else:
                    self._running_animation = None
                    self._app_event_emitter.emit(AnimationFinishedEvent())
            animation.finished.connect(finished)
            if self._running_animation:
                self._waiting_animations.append(animation)
            else:
                self._running_animation = animation
                self._running_animation.start()

        @classmethod
        def position_of(cls, slot: Slot) -> QPoint:
            return QPoint(cls.IMAGE_OFFSET_X + 36 + slot.hor_pos * (cls.Marble.SIZE.width() + 6),
                          cls.IMAGE_OFFSET_Y + 36 + slot.ver_pos * (cls.Marble.SIZE.height() + 6))

        @classmethod
        def determine_side(cls, cursor_pos: QPoint) -> Optional[Side]:
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
        super().__init__()

        self.setScene(self.BoardScene(self, model))

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
                    QCursor(_load_image(f'insert_{cn}_{sn}_enabled.png').scaled(csize), -1, -1),
                    QCursor(_load_image(f'insert_{cn}_{sn}_disabled.png').scaled(csize), -1, -1))

    @property
    def model(self) -> BoardViewModel:
        return self._model

    @property
    def move_selection_enabled(self) -> bool:
        return self._move_selection_enabled

    @move_selection_enabled.setter
    def move_selection_enabled(self, new_val: bool) -> None:
        self._move_selection_enabled = new_val
        self.setMouseTracking(new_val)
        if not new_val:
            self.setCursor(self._neutral_cursor)

    def mouseMoveEvent(self, ev: QMouseEvent) -> None:  # pylint: disable=invalid-name
        if self._move_selection_enabled:
            assert self._model.current_player is not None, "current_player not set!"
            side, insert_pos = self._determine_move_args(ev.pos())
            new_cursor = self._neutral_cursor
            if side is not None:
                cursor_pair = self._insert_cursors[self._model.current_player.colour][side]
                new_cursor = cursor_pair.get(insert_pos is not None)
            self.setCursor(new_cursor)

    def mousePressEvent(self, ev: QMouseEvent) -> None:  # pylint: disable=invalid-name
        if (self._move_selection_enabled and
                ev.button() == Qt.MouseButton.LeftButton):
            side, insert_pos = self._determine_move_args(ev.pos())
            if side is not None and insert_pos is not None:
                self.emit(MoveSelectedEvent(Move(side, insert_pos)))

    def _determine_move_args(self, ev_pos: QPoint) -> tuple[Optional[Side], Optional[int]]:
        side = self.BoardScene.determine_side(ev_pos)
        if side is not None:
            insert_pos = self.BoardScene.determine_insert_pos(
                side, ev_pos.y() if side.is_vertical else ev_pos.x())
            if insert_pos is not None and self._model.is_insertion_possible(side, insert_pos):
                return (side, insert_pos)
            return (side, None)
        return (None, None)

    def show_game_over(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(self._main_window_title)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText("Game over!")
        game_over_condition = self._model.game_over_condition
        assert game_over_condition is not None, "Game not yet over!"
        if game_over_condition.winner:
            msg_box.setInformativeText(f"{game_over_condition.winner.name} has won.")
        else:
            msg_box.setInformativeText("It has ended in a draw.")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def show_starting_player(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(self._main_window_title)
        msg_box.setIcon(QMessageBox.Information)
        current_player = self._model.current_player
        assert self._model.count_occupied_slots() == 0
        msg_box.setText(f"Starting player: {current_player.colour.name}")
        if current_player.nature is PlayerNature.HUMAN:
            msg_box.setInformativeText("That's you.")
        else:
            msg_box.setInformativeText("That's the computer.")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
        self.emit(ReadyForFirstMoveEvent())
