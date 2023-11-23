from importlib.resources import path as resrc_path
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QPixmap
from shiftago.ui import images

BOARD_VIEW_SIZE = QSize(700, 700)

def load_image(image_resource: str) -> QPixmap:
    with resrc_path(images, image_resource) as path:
        return QPixmap(str(path))
