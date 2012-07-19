#
# FitsImageQt.py -- classes for the display of FITS files in Qt widgets
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Fri Jun 22 13:48:13 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from PyQt4 import QtGui, QtCore

import numpy
import FitsImage
import Mixins

class FitsImageQtError(FitsImage.FitsImageError):
    pass

    
class RenderGraphicsView(QtGui.QGraphicsView):

    def __init__(self, *args, **kwdargs):
        super(RenderGraphicsView, self).__init__(*args, **kwdargs)
    
        self.fitsimage = None
        self.pixmap = None

    def drawBackground(self, painter, rect):
        """When an area of the window is exposed, we just copy out of the
        server-side, off-screen pixmap to that area.
        """
        if not self.pixmap:
            return
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1

        # redraw the screen from backing pixmap
        rect = QtCore.QRect(x1, y1, width, height)
        painter.drawPixmap(rect, self.pixmap, rect)

    def resizeEvent(self, event):
        rect = self.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1
       
        self.fitsimage.configure(width, height)

    def sizeHint(self):
        return QtCore.QSize(100, 100)
    
        
class RenderWidget(QtGui.QWidget):

    def __init__(self, *args, **kwdargs):
        super(RenderWidget, self).__init__(*args, **kwdargs)

        self.fitsimage = None
        self.pixmap = None
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)
        
    def paintEvent(self, event):
        """When an area of the window is exposed, we just copy out of the
        server-side, off-screen pixmap to that area.
        """
        if not self.pixmap:
            return
        rect = event.rect()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1

        # redraw the screen from backing pixmap
        painter = QtGui.QPainter(self)
        rect = QtCore.QRect(x1, y1, width, height)
        painter.drawPixmap(rect, self.pixmap, rect)
        
    def resizeEvent(self, event):
        rect = self.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1
       
        self.fitsimage.configure(width, height)
        #self.update()

    def sizeHint(self):
        return QtCore.QSize(100, 100)


class FitsImageQt(FitsImage.FitsImageBase):

    def __init__(self, logger=None, render='widget'):
        #super(FitsImageQt, self).__init__(logger=logger)
        FitsImage.FitsImageBase.__init__(self, logger=logger)

        self.wtype = render
        if self.wtype == 'widget':
            self.imgwin = RenderWidget()
        elif self.wtype == 'scene':
            self.scene = QtGui.QGraphicsScene()
            self.imgwin = RenderGraphicsView(self.scene)
        else:
            raise FitsImageQtError("Undefined render type: '%s'" % (render))
        self.imgwin.fitsimage = self
        self.pixmap = None

        self.message = None
        self.msgtimer = QtCore.QTimer()
        QtCore.QObject.connect(self.msgtimer, QtCore.SIGNAL("timeout()"),
                               self.onscreen_message_off)
        self.msgfont = QtGui.QFont('Sans Serif', pointSize=24)
        self.set_bg(0.5, 0.5, 0.5, redraw=False)
        self.set_fg(1.0, 1.0, 1.0, redraw=False)

        # cursors
        self.cursor = {}

    def get_widget(self):
        return self.imgwin

    def _render_offscreen(self, drawable, data, dst_x, dst_y,
                          width, height):
        # NOTE [A]
        daht, dawd, depth = data.shape
        self.logger.debug("data shape is %dx%dx%d" % (dawd, daht, depth))

        # Get qimage for copying pixel data
        qimage = self._get_qimage(data)

        painter = QtGui.QPainter(drawable)

        # fill pixmap with background color
        imgwin_wd, imgwin_ht = self.get_window_size()
        painter.fillRect(QtCore.QRect(0, 0, imgwin_wd, imgwin_ht),
                         self.img_bg)

        # draw image data from buffer to offscreen pixmap
        painter.drawImage(QtCore.QRect(dst_x, dst_y, width, height),
                          qimage,
                          QtCore.QRect(0, 0, width, height))

        # render self.message
        if self.message:
            self.draw_message(painter, imgwin_wd, imgwin_ht,
                              self.message)

    def draw_message(self, painter, width, height, message):
        painter.setPen(self.img_fg)
        ## pen = QtGui.QPen()
        ## pen.setColor(self.img_fg)
        ## painter.setPen(pen)
        painter.setBrush(self.img_fg)
        painter.setFont(self.msgfont)
        rect = painter.boundingRect(0, 0, 1000, 1000, 0, message)
        x1, y1, x2, y2 = rect.getCoords()
        wd = x2 - x1
        ht = y2 - y1
        y = ((height // 3) * 2) - (ht // 2)
        x = (width // 2) - (wd // 2)
        painter.drawText(x, y, message)
        

    def render_offscreen(self, data, dst_x, dst_y, width, height):
        self.logger.debug("redraw pixmap=%s" % (self.pixmap))
        if self.pixmap == None:
            return
        self.logger.debug("drawing to pixmap")
        return self._render_offscreen(self.pixmap, data, dst_x, dst_y,
                                      width, height)

    def configure(self, width, height):
        if hasattr(self, 'scene'):
            self.scene.setSceneRect(0, 0, width, height)
        pixmap = QtGui.QPixmap(width, height)
        #pixmap.fill(QColor("black"))
        self.pixmap = pixmap
        self.imgwin.pixmap = pixmap
        self.set_window_size(width, height, redraw=True)
        
    def get_image_as_widget(self):
        arr = self.get_rgb_array()
        image = self._get_qimage(arr)
        return image
    
    def update_image(self):
        if (not self.pixmap) or (not self.imgwin):
            return
            
        self.logger.debug("updating window from pixmap")
        if hasattr(self, 'scene'):
            imgwin_wd, imgwin_ht = self.get_window_size()
            self.scene.invalidate(0, 0, imgwin_wd, imgwin_ht,
                                  QtGui.QGraphicsScene.BackgroundLayer)
        else:
            self.imgwin.update()
            #self.imgwin.show()

    def set_cursor(self, cursor):
        if self.imgwin:
            self.imgwin.setCursor(cursor)
        
    def define_cursor(self, ctype, cursor):
        self.cursor[ctype] = cursor
        
    def switch_cursor(self, ctype):
        self.set_cursor(self.cursor[ctype])
        
    def _get_qimage(self, rgb):
	h, w, channels = rgb.shape

	# Qt expects 32bit BGRA data for color images:
	bgra = numpy.empty((h, w, 4), numpy.uint8, 'C')
	bgra[...,0] = rgb[...,2]
	bgra[...,1] = rgb[...,1]
	bgra[...,2] = rgb[...,0]
	if rgb.shape[2] == 3:
		bgra[...,3].fill(255)
		fmt = QtGui.QImage.Format_RGB32
	else:
		bgra[...,3] = rgb[...,3]
		fmt = QtGui.QImage.Format_ARGB32

	result = QtGui.QImage(bgra.data, w, h, fmt)
	result.ndarray = bgra
        return result

    def _get_color(self, r, g, b):
        n = 255.0
        clr = QtGui.QColor(int(r*n), int(g*n), int(b*n))
        return clr
        
    def set_bg(self, r, g, b, redraw=True):
        self.img_bg = self._get_color(r, g, b)
        if redraw:
            self.redraw(whence=3)
        
    def set_fg(self, r, g, b, redraw=True):
        self.img_fg = self._get_color(r, g, b)
        if redraw:
            self.redraw(whence=3)
        
    def onscreen_message(self, text, delay=None, redraw=True):
        try:
            self.msgtimer.stop()
        except:
            pass
        self.message = text
        if redraw:
            self.redraw(whence=3)
        if delay:
            ms = int(delay * 1000.0)
            self.msgtimer.start(ms)

    def onscreen_message_off(self, redraw=True):
        return self.onscreen_message(None, redraw=redraw)
    

class RenderMixin(object):

    def showEvent(self, event):
        self.fitsimage.map_event(self, event)
            
    def focusInEvent(self, event):
        self.fitsimage.focus_event(self, event, True)
            
    def focusOutEvent(self, event):
        self.fitsimage.focus_event(self, event, False)
            
    def enterEvent(self, event):
        self.fitsimage.enter_notify_event(self, event)
    
    def leaveEvent(self, event):
        self.fitsimage.leave_notify_event(self, event)
    
    def keyPressEvent(self, event):
        self.fitsimage.key_press_event(self, event)
        
    def keyReleaseEvent(self, event):
        self.fitsimage.key_release_event(self, event)
        
    def mousePressEvent(self, event):
        self.fitsimage.button_press_event(self, event)

    def mouseReleaseEvent(self, event):
        self.fitsimage.button_release_event(self, event)

    def mouseMoveEvent(self, event):
        self.fitsimage.motion_notify_event(self, event)

    def wheelEvent(self, event):
        self.fitsimage.scroll_event(self, event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('text/plain'):
            event.accept()
        else:
            event.ignore() 

    def dropEvent(self, event):
        self.fitsimage.drop_event(self, event)

    
class RenderWidgetZoom(RenderWidget, RenderMixin):
    pass

class RenderGraphicsViewZoom(RenderGraphicsView, RenderMixin):
    pass

class FitsImageEvent(FitsImageQt):

    def __init__(self, logger=None, render='widget'):
        #super(FitsImageEvent, self).__init__(logger=logger)
        FitsImageQt.__init__(self, logger=logger, render=render)

        # replace the widget our parent provided
        if hasattr(self, 'scene'):
            imgwin = RenderGraphicsViewZoom()
            imgwin.setScene(self.scene)
        else:
            imgwin = RenderWidgetZoom()
            
        imgwin.fitsimage = self
        self.imgwin = imgwin
        imgwin.setFocusPolicy(QtCore.Qt.TabFocus |
                              QtCore.Qt.ClickFocus |
                              QtCore.Qt.StrongFocus |
                              QtCore.Qt.WheelFocus)
        imgwin.setMouseTracking(True)
        imgwin.setAcceptDrops(True)
        
        # last known window mouse position
        self.last_win_x = 0
        self.last_win_y = 0
        # last known data mouse position
        self.last_data_x = 0
        self.last_data_y = 0
        # Does widget accept focus when mouse enters window
        self.follow_focus = True

        # User-defined keyboard mouse mask
        self.kbdmouse_mask = 0

        # Define cursors for pick and pan
        self.define_cursor('pan', QtGui.QCursor(QtCore.Qt.OpenHandCursor))
        co = thinCrossCursor('aquamarine')
        self.define_cursor('pick', co.cur)

        # @$%&^(_)*&^ qt!!
        self._keytbl = {
            '`': 'backquote',
            '"': 'doublequote',
            "'": 'singlequote',
            '\\': 'backslash',
            ' ': 'space',
            }
        self._fnkeycodes = [QtCore.Qt.Key_F1, QtCore.Qt.Key_F2,
                            QtCore.Qt.Key_F3, QtCore.Qt.Key_F4,
                            QtCore.Qt.Key_F5, QtCore.Qt.Key_F6,
                            QtCore.Qt.Key_F7, QtCore.Qt.Key_F8,
                            QtCore.Qt.Key_F9, QtCore.Qt.Key_F10,
                            QtCore.Qt.Key_F11, QtCore.Qt.Key_F12,
                            ]

        for name in ('motion', 'button-press', 'button-release',
                     'key-press', 'key-release', 'drag-drop', 
                     'scroll', 'map', 'focus', 'enter', 'leave',
                     ):
            self.enable_callback(name)


    def transkey(self, keycode, keyname):
        self.logger.debug("keycode=%d keyname='%s'" % (
            keycode, keyname))
        if keycode in [QtCore.Qt.Key_Control]:
            return 'control_l'
        if keycode in [QtCore.Qt.Key_Shift]:
            return 'shift_l'
        if keycode in [QtCore.Qt.Key_Escape]:
            return 'escape'
        if keycode in self._fnkeycodes:
            index = self._fnkeycodes.index(keycode)
            return 'f%d' % (index+1)

        try:
            return self._keytbl[keyname.lower()]

        except KeyError:
            return keyname
        
    def set_kbdmouse_mask(self, mask):
        self.kbdmouse_mask |= mask
        
    def reset_kbdmouse_mask(self, mask):
        self.kbdmouse_mask &= ~mask
        
    def get_kbdmouse_mask(self):
        return self.kbdmouse_mask
        
    def clear_kbdmouse_mask(self):
        self.kbdmouse_mask = 0
        
    def set_followfocus(self, tf):
        self.followfocus = tf
        
    def map_event(self, widget, event):
        rect = widget.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1
       
        self.configure(width, height)
        return self.make_callback('map')
            
    def focus_event(self, widget, event, hasFocus):
        return self.make_callback('focus', hasFocus)
            
    def enter_notify_event(self, widget, event):
        if self.follow_focus:
            widget.setFocus()
        return self.make_callback('enter')
    
    def leave_notify_event(self, widget, event):
        self.logger.debug("leaving widget...")
        return self.make_callback('leave')
    
    def key_press_event(self, widget, event):
        keyname = event.key()
        keyname2 = "%s" % (event.text())
        keyname = self.transkey(keyname, keyname2)
        self.logger.debug("key press event, key=%s" % (keyname))
        return self.make_callback('key-press', keyname)

    def key_release_event(self, widget, event):
        keyname = event.key()
        keyname2 = "%s" % (event.text())
        keyname = self.transkey(keyname, keyname2)
        self.logger.debug("key release event, key=%s" % (keyname))
        return self.make_callback('key-release', keyname)

    def button_press_event(self, widget, event):
        buttons = event.buttons()
        x, y = event.x(), event.y()

        button = self.kbdmouse_mask
        if buttons & QtCore.Qt.LeftButton:
            button |= 0x1
        if buttons & QtCore.Qt.MidButton:
            button |= 0x2
        if buttons & QtCore.Qt.RightButton:
            button |= 0x4
        self.logger.debug("button down event at %dx%d, button=%x" % (x, y, button))
                
        data_x, data_y = self.get_data_xy(x, y)
        return self.make_callback('button-press', button, data_x, data_y)

    def button_release_event(self, widget, event):
        # note: for mouseRelease this needs to be button(), not buttons()!
        buttons = event.button()
        x, y = event.x(), event.y()
        
        button = self.kbdmouse_mask
        if buttons & QtCore.Qt.LeftButton:
            button |= 0x1
        if buttons & QtCore.Qt.MidButton:
            button |= 0x2
        if buttons & QtCore.Qt.RightButton:
            button |= 0x4
            
        data_x, data_y = self.get_data_xy(x, y)
        return self.make_callback('button-release', button, data_x, data_y)

    def motion_notify_event(self, widget, event):
        buttons = event.buttons()
        x, y = event.x(), event.y()
        self.last_win_x, self.last_win_y = x, y
        
        button = self.kbdmouse_mask
        if buttons & QtCore.Qt.LeftButton:
            button |= 0x1
        if buttons & QtCore.Qt.MidButton:
            button |= 0x2
        if buttons & QtCore.Qt.RightButton:
            button |= 0x4

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_callback('motion', button, data_x, data_y)

    def scroll_event(self, widget, event):
        delta = event.delta()
        direction = None
        if delta > 0:
            direction = 'up'
        elif delta < 0:
            direction = 'down'
        self.logger.debug("scroll delta=%f direction=%s" % (
            delta, direction))

        return self.make_callback('scroll', direction)

    def drop_event(self, widget, event):
        data = str(event.mimeData().text())
        if '\r\n' in data:
            paths = data.split('\r\n')
        else:
            paths = data.split('\n')
        self.logger.debug("dropped filename(s): %s" % (str(paths)))
        return self.make_callback('drag-drop', paths)
        

class FitsImageZoom(FitsImageEvent, Mixins.FitsImageZoomMixin):

    def __init__(self, logger=None, render='widget'):
        #super(FitsImageZoom, self).__init__()
        FitsImageEvent.__init__(self, logger=logger, render=render)
        Mixins.FitsImageZoomMixin.__init__(self)
        
        
class thinCrossCursor(object):
    def __init__(self, color='red'):
        pm = QtGui.QPixmap(16,16)
        mask = QtGui.QBitmap(16,16)
        black = QtCore.Qt.color1
        white = QtCore.Qt.color0
        clr = QtGui.QColor(color)

        pm.fill(clr)
        mask.fill(black)
        p1 = QtGui.QPainter(mask)
        p1.setPen(white)
        
        p1.drawLine(0,6,5,6)
        p1.drawLine(0,8,5,8)
        
        p1.drawLine(10,6,15,6)
        p1.drawLine(10,8,15,8)
        
        p1.drawLine(6,0,6,5)
        p1.drawLine(8,0,8,5)
        
        p1.drawLine(6,10,6,15)
        p1.drawLine(8,10,8,15)
        
        #p1.drawLine(0,5,0,9)
        #p1.drawLine(15,5,15,9)
        #p1.drawLine(5,0,9,0)
        #p1.drawLine(5,15,9,15)
        #p1.drawArc(3,3,8,8,0,64*360)

        p1.end()
        pm.setAlphaChannel(mask)
        self.cur = QtGui.QCursor(pm, 8, 8)
        

#END