from typing import Optional
from shiftago.core import Colour, Slot, Side, ShiftagoObserver
from PyQt5.QtCore import QObject, pyqtSignal


class ShiftagoModelEvent:

    def __init__(self) -> None:
        pass


class MarbleShiftedEvent(ShiftagoModelEvent):

    def __init__(self, slot: Slot, direction: Side) -> None:
        super().__init__()
        self._slot = slot
        self._direction = direction

    def __str__(self) -> str:
        return f"MarbleShiftedEvent(slot: {self._slot} => {self._direction})"

    @property
    def slot(self) -> Slot:
        return self._slot

    @property
    def direction(self) -> Side:
        return self._direction


class MarbleInsertedEvent(ShiftagoModelEvent):

    def __init__(self, slot: Slot) -> None:
        super().__init__()
        self._slot = slot

    def __str__(self) -> str:
        return f"MarbleInsertedEvent(slot: {self._slot})"

    @property
    def slot(self) -> Slot:
        return self._slot


class BoardViewModel(ShiftagoObserver, QObject):

    model_changed_notifier = pyqtSignal(ShiftagoModelEvent)

    def __init__(self) -> None:
        super().__init__()

    def current_player(self) -> Optional[Colour]:
        raise NotImplementedError

    def colour_at(self, position: Slot) -> Optional[Colour]:
        raise NotImplementedError

    def is_insertion_possible(self, side: Side, insert_pos: int) -> bool:
        raise NotImplementedError

    def notify_marble_shifted(self, slot: Slot, direction: Side):
        self.model_changed_notifier.emit(MarbleShiftedEvent(slot, direction))

    def notify_marble_inserted(self, slot: Slot):
        self.model_changed_notifier.emit(MarbleInsertedEvent(slot))
