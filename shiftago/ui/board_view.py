import logging
from collections import defaultdict, deque
from typing import Dict, Optional, NamedTuple, Deque
from PyQt5.QtCore import Qt, QSize, QPoint, QRectF, pyqtBoundSignal, pyqtSlot, QPropertyAnimation
from PyQt5.QtWidgets import QWidget, QGraphicsView, QGraphicsScene, QGraphicsObject, QStyleOptionGraphicsItem, QMessageBox
from PyQt5.QtGui import QPixmap, QPainter, QMouseEvent, QCursor
from shiftago.core import NUM_SLOTS_PER_SIDE, Colour, Slot, Side, Move, GameOverCondition
from shiftago.ui import load_image
from shiftago.ui.app_events import AnimationFinishedEvent, MoveSelectedEvent, ExitRequestedEvent
from shiftago.ui.hmvc import AppEventEmitter
from shiftago.ui.board_view_model import BoardViewModel, ShiftagoModelEvent, MarbleInsertedEvent, MarbleShiftedEvent

logger = logging.getLogger(__name__)


class BoardView(AppEventEmitter, QGraphicsView):

    TOTAL_SIZE = QSize(700, 700)
    IMAGE_SIZE = QSize(600, 600)
    IMAGE_OFFSET_X = (TOTAL_SIZE.width() - IMAGE_SIZE.width()) // 2
    IMAGE_OFFSET_Y = (TOTAL_SIZE.height() - IMAGE_SIZE.height()) // 2
    SLOT_SIZE = QSize(59, 59)

    class CursorPair(NamedTuple):
        enabled: QCursor
        disabled: QCursor

    class BoardScene(QGraphicsScene):

        class Marble(QGraphicsObject):

            SIZE = QSize(70, 70)

            def __init__(self, slot: Slot, pixmap: QPixmap, position: QPoint) -> None:
                super().__init__()
                self.setPos(position)
                self._pixmap = pixmap

            def boundingRect(self) -> QRectF:
                return QRectF(0, 0, self.SIZE.width(), self.SIZE.height())

            def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget]) -> None:
                painter.drawPixmap(0, 0, self._pixmap)

        def __init__(self, app_event_emitter: AppEventEmitter, model: BoardViewModel) -> None:
            super().__init__()
            board_pixmap = load_image('shiftago_board.jpg').scaled(BoardView.IMAGE_SIZE)
            self._app_event_emitter = app_event_emitter
            self._model = model
            self._marble_pixmaps: Dict[Colour, QPixmap] = dict()
            self._marble_pixmaps[Colour.BLUE] = load_image('blue_marble.png').scaled(self.Marble.SIZE)
            self._marble_pixmaps[Colour.ORANGE] = load_image('orange_marble.png').scaled(self.Marble.SIZE)
            self.setSceneRect(0, 0, BoardView.TOTAL_SIZE.width(), BoardView.TOTAL_SIZE.height())
            self.addPixmap(board_pixmap).setPos(QPoint(BoardView.IMAGE_OFFSET_X, BoardView.IMAGE_OFFSET_Y))
            self._marbles: Dict[Slot, BoardView.BoardScene.Marble] = dict()
            self._running_animation: Optional[QPropertyAnimation] = None
            self._waiting_animations: Deque[QPropertyAnimation] = deque()

        @pyqtSlot(ShiftagoModelEvent)
        def update_from_model(self, event: ShiftagoModelEvent) -> None:
            logger.debug(f"Event occurred: {event}")
            if event.__class__ == MarbleInsertedEvent:
                slot: Slot = event.slot  # type: ignore
                colour = self._model.colour_at(slot)
                assert colour, f"{slot} is not occupied!"
                marble = self.Marble(slot, self._marble_pixmaps[colour], self.position_of(slot))
                self._marbles[slot] = marble
                marble.setOpacity(0.0)
                self.addItem(marble)
                animation = QPropertyAnimation(marble, b'opacity')
                animation.setEndValue(1.0)
                animation.setDuration(500)
                self.run_animation(animation)
            elif event.__class__ == MarbleShiftedEvent:
                from_slot: Slot = event.slot  # type: ignore
                to_slot = from_slot.neighbour(event.direction)  # type: ignore
                marble = self._marbles.pop(from_slot)
                self._marbles[to_slot] = marble
                animation = QPropertyAnimation(marble, b'pos')
                animation.setEndValue(self.position_of(to_slot))
                animation.setDuration(500)
                self.run_animation(animation)
            else:
                raise ValueError(f"Unknown event type: {event.__class__.__class__}")

        def run_animation(self, animation: QPropertyAnimation) -> None:
            animation.finished.connect(self.animation_finished)  # type: ignore
            if self._running_animation:
                self._waiting_animations.append(animation)
            else:
                self._running_animation = animation
                self._running_animation.start()

        @pyqtSlot()
        def animation_finished(self) -> None:
            if len(self._waiting_animations) > 0:
                self._running_animation = self._waiting_animations.popleft()
                self._running_animation.start()
            else:
                self._running_animation = None
                self._app_event_emitter.emit(AnimationFinishedEvent())

        def position_of(self, slot: Slot) -> QPoint:
            return QPoint(BoardView.IMAGE_OFFSET_X + 36 + slot.hor_pos * (self.Marble.SIZE.width() + 6),
                          BoardView.IMAGE_OFFSET_Y + 36 + slot.ver_pos * (self.Marble.SIZE.height() + 6))

    def __init__(self, model: BoardViewModel) -> None:
        super().__init__()

        self._model = model

        self._board_scene = self.BoardScene(self, self._model)
        self.setScene(self._board_scene)

        model.model_changed_notifier.connect(self._board_scene.update_from_model)  # type: ignore

        self._neutral_cursor = QCursor(Qt.CursorShape.ArrowCursor)

        cursor_sizes: Dict[Side, QSize] = dict()

        cursor_sizes[Side.LEFT] = QSize(122, 70)
        cursor_sizes[Side.RIGHT] = cursor_sizes[Side.LEFT]
        cursor_sizes[Side.TOP] = QSize(70, 122)
        cursor_sizes[Side.BOTTOM] = cursor_sizes[Side.TOP]

        self._insert_cursors: Dict[Colour, Dict[Side, BoardView.CursorPair]] = defaultdict(lambda: dict())
        for colour in (Colour.BLUE, Colour.ORANGE):
            cn = colour.name.lower()
            for side in Side:
                sn = side.name.lower()
                csize = cursor_sizes[side]
                self._insert_cursors[colour][side] = self.CursorPair(
                    QCursor(load_image(f'insert_{cn}_{sn}_enabled.png').scaled(csize), -1, -1),
                    QCursor(load_image(f'insert_{cn}_{sn}_disabled.png').scaled(csize), -1, -1))

    @property
    def model(self) -> Optional[BoardViewModel]:
        return self._model

    @model.setter
    def model(self, model: BoardViewModel) -> None:
        self._model = model

    def reset_cursor(self) -> None:
        self.setCursor(self._neutral_cursor)

    def mouseMoveEvent(self, ev: QMouseEvent) -> None:
        new_cursor = self._neutral_cursor
        ev_pos = ev.pos()
        side = self._determine_side(ev_pos)
        if side:
            insert_pos = self._determine_insert_pos(side, ev_pos.y()
                                                    if side == Side.LEFT or side == Side.RIGHT else ev_pos.x())
            if self._model.current_player:
                cursor_pair = self._insert_cursors[self._model.current_player][side]  # type: ignore
                new_cursor = cursor_pair.enabled if (insert_pos is not None and
                                                     self._model.is_insertion_possible(side, insert_pos)) else cursor_pair.disabled
        self.setCursor(new_cursor)

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        if ev.button() == Qt.MouseButton.LeftButton and self._model:
            move: Optional[Move] = self._determine_move(ev.pos())
            if move:
                self.emit(MoveSelectedEvent(move))

    def show_game_over(self, game_over_condition: GameOverCondition):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Shiftago-Qt")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText("Game over!")
        if game_over_condition.winner:
            msg_box.setInformativeText(f"{game_over_condition._winner.name} has won.")
        else:
            msg_box.setInformativeText("It has ended in a draw.")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
        self.emit(ExitRequestedEvent())

    def _determine_move(self, cursor_pos: QPoint) -> Optional[Move]:
        side = self._determine_side(cursor_pos)
        if side:
            insert_pos = self._determine_insert_pos(side, cursor_pos.y() if side.is_vertical else cursor_pos.x())
            if insert_pos is not None and self._model.is_insertion_possible(side, insert_pos):
                return Move(side, insert_pos)
        return None

    def _determine_insert_pos(self, side: Side, cursor_pos: int) -> Optional[int]:
        if side.is_vertical:
            board_relative_pos = cursor_pos - (BoardView.IMAGE_OFFSET_Y + 38)
            insert_pos = board_relative_pos // (self.SLOT_SIZE.height() + 18)
            if insert_pos >= 0 and insert_pos <= 6 and (
                    board_relative_pos % (self.SLOT_SIZE.height() + 18)) < self.SLOT_SIZE.height():
                return insert_pos
        else:
            board_relative_pos = cursor_pos - (BoardView.IMAGE_OFFSET_X + 38)
            insert_pos = board_relative_pos // (self.SLOT_SIZE.width() + 18)
            if insert_pos >= 0 and insert_pos <= 6 and (
                    board_relative_pos % (self.SLOT_SIZE.width() + 18)) < self.SLOT_SIZE.width():
                return insert_pos
        return None

    def _determine_side(self, cursor_pos: QPoint) -> Optional[Side]:
        cursor_pos_x = cursor_pos.x()
        cursor_pos_y = cursor_pos.y()

        left_bound = BoardView.IMAGE_OFFSET_X + self.BoardScene.Marble.SIZE.width() // 3
        right_bound = BoardView.IMAGE_OFFSET_X + BoardView.IMAGE_SIZE.width() - self.BoardScene.Marble.SIZE.width() // 3
        top_bound = BoardView.IMAGE_OFFSET_Y + self.BoardScene.Marble.SIZE.height() // 3
        bottom_bound = BoardView.IMAGE_OFFSET_Y + BoardView.IMAGE_SIZE.height() - self.BoardScene.Marble.SIZE.height() // 3

        if cursor_pos_x < left_bound:
            if cursor_pos_y > top_bound and cursor_pos_y < bottom_bound:
                return Side.LEFT
        elif cursor_pos_x > right_bound:
            if cursor_pos_y > top_bound and cursor_pos_y < bottom_bound:
                return Side.RIGHT
        elif cursor_pos_y < top_bound:
            if cursor_pos_x > left_bound and cursor_pos_x < right_bound:
                return Side.TOP
        elif cursor_pos_y > bottom_bound:
            if cursor_pos_x > left_bound and cursor_pos_x < right_bound:
                return Side.BOTTOM
        return None
