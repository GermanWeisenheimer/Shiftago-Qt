# pylint: disable=no-name-in-module
from importlib.resources import path as resrc_path
from PyQt5.QtGui import QPixmap
import shiftago.ui.images as images


def load_image(image_resource: str) -> QPixmap:
    with resrc_path(images, image_resource) as path:
        return QPixmap(str(path))
