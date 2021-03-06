#
# ImageViewCanvasMock.py -- A FITS image widget with canvas drawing in mock
#                             widget set
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.mockw import ImageViewMock
from ginga.mockw.ImageViewCanvasTypesMock import *


class ImageViewCanvasError(ImageViewMock.ImageViewMockError):
    pass

class ImageViewCanvas(ImageViewMock.ImageViewZoom,
                      DrawingMixin, CanvasMixin, CompoundMixin):

    def __init__(self, logger=None, settings=None,
                 rgbmap=None, bindmap=None, bindings=None):
        ImageViewMock.ImageViewZoom.__init__(self, logger=logger,
                                             settings=settings,
                                             rgbmap=rgbmap,
                                             bindmap=bindmap,
                                             bindings=bindings)
        CompoundMixin.__init__(self)
        CanvasMixin.__init__(self)
        DrawingMixin.__init__(self, drawCatalog)

        self.setSurface(self)
        self.ui_setActive(True)

    def canvascoords(self, data_x, data_y, center=True):
        # data->canvas space coordinate conversion
        x, y = self.get_canvas_xy(data_x, data_y, center=center)
        return (x, y)

    def redraw_data(self, whence=0):
        super(ImageViewCanvas, self).redraw_data(whence=whence)

        if not self.pixmap:
            return
        self.draw()

    # METHODS THAT WERE IN IPG

    def add_canvas(self, tag=None):
        # add a canvas to the view
        DrawingCanvas = self.getDrawClass('drawingcanvas')
        canvas = DrawingCanvas()
        # enable drawing on the canvas
        canvas.enable_draw(True)
        canvas.ui_setActive(True)
        canvas.setSurface(self)
        # add the canvas to the view.
        self.add(canvas, tag=tag)
        return canvas

    def show(self):
        from IPython.display import Image
        return Image(data=bytes(self.get_rgb_image_as_bytes(format='png')),
                     format='png', embed=True)

#END
