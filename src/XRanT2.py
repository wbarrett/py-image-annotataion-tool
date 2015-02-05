#!/usr/bin/env python

# author: Muhammet Bastan, mubastan@gmail.com
# date: August 2011

import sys
import os
import functools
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from Annotation2 import *

### GLOBAL VARIABLES ###

# min size for the image display panels
WMIN = 650
HMIN = 700

# initial brush radius & color (painting)
BRUSH_RADIUS = 20
BRUSH_COLOR = QColor(255, 0, 0, 255)

# brush types
DRAWL = 0       # draw/paint line
DRAWELL = 1     # draw/paint filled ellipse--circle
DRAWRECT = 2    # paint filled rectangle
DRAWRECTR = 3   # paint filled rounded rectangle
DRAWPOLY = 4    # paint filled rounded rectangle
BRUSH_TYPES_STR = ["Line", "Circle", "Rectangle", "Rounded rect.", "Polygon"]
BRUSH_TYPES_INT = [DRAWL, DRAWELL, DRAWRECT, DRAWRECTR, DRAWPOLY]


###  FUNCTIONS AND CLASSES ###

class ObjectItem(QGraphicsItem):
    def __init__(self, qimage, x, y, scene, id, opacity, drawMBR, view = V0):
        super(ObjectItem, self).__init__(None, scene)
        self.image = qimage
        self.setPos(QPointF(x,y))
        self.ID = id
        self.rect = QRectF(0,0, qimage.width(), qimage.height())        
        self.opacity = opacity
        self.drawMBR = drawMBR
        self.setMBR_color(view)
        self.setFlags(QGraphicsItem.ItemIsSelectable|QGraphicsItem.ItemIsFocusable)
        self.setSelected(True)
        self.setFocus()        
    
    def boundingRect(self):
        return self.rect.adjusted(-2, -2, 2, 2)
    
    def paint(self, painter, option, widget=None):
        painter.setOpacity(self.opacity)
        if self.image:
            painter.drawImage(0,0, self.image)
        if not self.drawMBR: return
        painter.setOpacity(1.0)
        pen = self.rcolor
        pen.setStyle(Qt.DotLine)
        pen.setWidth(2)        
        if option.state & QStyle.State_Selected: 
            pen.setStyle(Qt.SolidLine)
            pen.setWidth(3)       
        painter.setPen(pen)
        painter.drawRect(self.rect)        
        
    def contextMenuEvent(self, event):        
        menu = QMenu()
        for text, viewLabel in (
                ("view 1: clear, visible (green mbr)", V1),
                ("view 2: at some angle (blue mbr)", V2),
                ("view 3: side, not clearly visible (red mbr)", V3),
                ("skip 0: no view label (magenta mbr)", V0),):
            wrapper = functools.partial(self.setViewLabel, viewLabel, text)            
            menu.addAction(text, wrapper)        
        menu.exec_(event.screenPos())        
    
    def setViewLabel(self, viewLabel, text):
        self.scene().setObjectViewLabel(self.ID, viewLabel)
        print 'View label for object ', self.ID, ':', text
        
        self.setMBR_color(viewLabel)
        #self.update()
    
    def setMBR_color(self, viewLabel):
        if viewLabel == V0: self.rcolor = QPen(Qt.magenta)
        elif viewLabel == V1: self.rcolor = QPen(Qt.green)
        elif viewLabel == V2: self.rcolor = QPen(Qt.blue)
        elif viewLabel == V3: self.rcolor = QPen(Qt.red)
        self.update()
    
    def delete(self):
        self.scene().deleteObject(self)       
    def increaseOpacity(self):
        self.changeOpacity(0.1)
    def decreaseOpacity(self):
        self.changeOpacity(-0.1)
    def changeOpacity(self, incr):
        self.opacity += incr
        if self.opacity > 1.0: self.opacity = 1.0
        elif self.opacity < 0.1: self.opacity = 0.1
        self.update()
    
class ImageDrawScene(QGraphicsScene):
    def __init__(self, main):
        super(ImageDrawScene, self).__init__()
        self.main = main
        self.backgroundImage = None
        self.foregroundImage = None
        self.setSceneRect(0, 0, WMIN, HMIN)        
        self.w, self.h = 1,1
        
        # painting related
        self.showBrush = False
        self.opacity = 0.7
        self.x0, self.y0 = -1, -1
        self.painting = False
        self.erasing = False
        self.dradius = BRUSH_RADIUS       # drawing/painting radius
        self.dtype = DRAWL                # brush type: line, circle, rectangle, polygon
        self.dcolor = BRUSH_COLOR
        self.dbrush = QBrush(self.dcolor)
        self.pen = QPen(Qt.SolidLine)
        self.pen.setColor(self.dcolor)
        self.pen.setWidth(2*self.dradius)
        self.pen.setCapStyle(Qt.RoundCap)
        
        self.polypen = QPen(Qt.SolidLine)
        self.polypen.setColor(self.dcolor)
        self.polypen.setWidth(3)
        self.polypen.setCapStyle(Qt.RoundCap)
        
        self.polygon = QPolygonF()
        self.polyDrawing = False
        self.polyLast = None        
        self.setBrushType(BRUSH_TYPES_INT[0])
        
    def setRadius(self, radius):
        self.dradius = radius
        self.pen.setWidth(2*self.dradius)
        self.update()
    
    def setBrushType(self, dtype):
        if dtype in BRUSH_TYPES_INT:
            self.dtype = dtype
            if(self.dtype == DRAWPOLY):
                self.startPolygon()
        self.update()
        
    def setBrushColor(self, dcolor):
        self.dcolor = dcolor
        self.dbrush.setColor(self.dcolor)
        self.pen.setColor(self.dcolor)
        self.polypen.setColor(self.dcolor)
        self.update()
    
    def setImage(self, image):
        if image:            
            self.w, self.h = image.width(), image.height()
            self.setBackground(image)
            self.setForeground(self.w, self.h)
            self.setSceneRect(0, 0, self.w, self.h)            
        else:
            self.setSceneRect(0, 0, WMIN, HMIN)
        self.update()
    
    def setForeground(self, w, h):        
        #self.foregroundImage = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        self.foregroundImage = QImage(w, h, QImage.Format_ARGB32)
        self.foregroundImage.fill(QColor(0, 0, 0, 0).rgba())        
    # reset painting
    def resetForeground(self):
        if self.w > 1 and self.h > 1:
            self.setForeground(self.w, self.h)
        if self.dtype == DRAWPOLY:
            self.startPolygon()
        self.update()
    def addObject(self):
        self.main.addObject()
        if self.dtype == DRAWPOLY:
            self.startPolygon()            
        self.update()
    # return the selected object as a single channel image
    def getObjectMask(self):
        if self.foregroundImage:
            return self.foregroundImage.alphaChannel()
        else: return None
    
    def setBackground(self, image):
        if image:
            self.backgroundImage = image.copy()            
            self.update()
    
    # overridden
    def drawForeground (self, painter, rect):
        if self.dtype == DRAWPOLY and self.polyDrawing:
            self.drawPolygon(painter)
        if self.foregroundImage:
            painter.setOpacity(self.opacity)
            painter.drawImage(0, 0, self.foregroundImage)
        if self.showBrush: self.drawCursor(painter)
    
    def drawPolygon(self, painter):
        n = self.polygon.size()        
        painter.setPen(self.polypen)
        if n == 0:
            if self.polyLast: painter.drawEllipse(self.polyLast, 3, 3)
            return
        if self.polyLast:
            self.polygon.append(self.polyLast)
        n = self.polygon.size()
        painter.drawPolygon(self.polygon)  
        for i in range(n):
            painter.drawEllipse(self.polygon.at(i), 3, 3)
        if self.polyLast:
            self.polygon.remove(n-1)
            self.polyLast = None
    # overridden
    def drawBackground (self, painter, rect):
        if self.backgroundImage:
            painter.drawPixmap(0, 0, self.backgroundImage)
    
    def contextMenuEvent(self, event):
        return
        
        cmenu = QMenu()
        if self.dtype == DRAWPOLY and self.polyDrawing:
            cmenu.addAction("End polygon", self.endPolygon)
            cmenu.addSeparator()
        cmenu.addAction("Add object", self.addObject)
        cmenu.addAction("Reset/clear", self.resetForeground)
        cmenu.addSeparator()
        if self.erasing:
            cmenu.addAction("Change mode to: paint", self.togglePaintErase)
        else:
            cmenu.addAction("Change mode to: erase", self.togglePaintErase)
        cmenu.addSeparator()
        if self.dtype != DRAWPOLY:
            if self.showBrush: cmenu.addAction("Hide brush", self.toggleBrushFlag)
            else: cmenu.addAction("Show brush", self.toggleBrushFlag)        
        cmenu.addAction("Increase opacity", self.increaseOpacity)            
        cmenu.addAction("Decrease opacity", self.decreaseOpacity)            
        cmenu.exec_(event.screenPos())
        super(ImageDrawScene, self).contextMenuEvent(event)
    def toggleBrushFlag(self):
        self.showBrush = not self.showBrush
        self.update()
    def togglePaintErase(self):
        self.erasing = not self.erasing
        if self.erasing:
            self.dbrush.setColor(QColor(0, 0, 0, 0))
            self.pen.setColor(QColor(0, 0, 0, 0))            
        else:
            self.dbrush.setColor(self.dcolor)
            self.pen.setColor(self.dcolor)            
        self.update()
    def startPolygon(self):
        self.polygon.clear()
        self.polyDrawing = True
        self.update()
    def endPolygon(self):
        self.polyDrawing = False
        self.drawPolygonOnImage()
        self.update()
    def increaseOpacity(self):
        self.changeOpacity(0.1)
    def decreaseOpacity(self):
        self.changeOpacity(-0.1)
    def changeOpacity(self, incr):
        self.opacity += incr
        if self.opacity > 1.0: self.opacity = 1.0
        elif self.opacity < 0.1: self.opacity = 0.1
        self.update()
    
    def mousePressEvent(self, event):
        return
        if event.button() == Qt.LeftButton:
            if self.dtype == DRAWPOLY and self.polyDrawing:
                self.polygon.append(event.scenePos())
                self.polyLast = None
            else:
                self.painting = True
                self.drawOnImage(event, self.dtype)                       
            self.update()
        
    def mouseReleaseEvent(self, event):
        return
        if self.dtype == DRAWPOLY: return
        if event.button() == Qt.LeftButton:
            self.painting = False
            self.x0, self.y0 = -1,-1
            self.update()
        
    def mouseMoveEvent (self, event):
        return
        if self.dtype == DRAWPOLY:
            if self.polyDrawing:
                self.polyLast = event.scenePos()
                self.update()
            return
        self.mpos = event.scenePos()
        if self.painting:
            self.drawOnImage(event, self.dtype)
        self.update()        
    def drawOnImage(self, event, dtype = DRAWELL):
        if not (self.foregroundImage and self.backgroundImage): return
        pos = event.scenePos()
        x, y = pos.x(), pos.y()            
        painter = QPainter(self.foregroundImage)
        if self.erasing: 
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
        if dtype == DRAWL: painter.setPen(self.pen)
        else:
            painter.setPen(Qt.NoPen)        
            painter.setBrush(self.dbrush)            
        if dtype == DRAWELL:
            painter.drawEllipse(pos, self.dradius, self.dradius)       
        elif dtype == DRAWRECT:            
            painter.drawRect(x-self.dradius, y-self.dradius, 2*self.dradius, 2*self.dradius)
        elif dtype == DRAWRECTR:
            painter.drawRoundedRect(x-self.dradius, y-self.dradius, 2*self.dradius, 2*self.dradius, 25.0, 25.0, mode=Qt.RelativeSize)
        elif dtype == DRAWL and self.x0 >= 0 and self.y0 >= 0:            
            painter.drawLine(self.x0, self.y0, x, y)
        self.x0, self.y0 = x, y
            
        painter.end()
    
    def drawPolygonOnImage(self):
        if self.polygon.size() < 3 or not (self.foregroundImage and self.backgroundImage): return
        painter = QPainter(self.foregroundImage)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.dbrush)
        painter.drawPolygon(self.polygon)
        painter.end()
    # draw the current brush    
    def drawCursor(self, painter):
        painter.setPen(Qt.black)
        if self.erasing: painter.setBrush(Qt.white)
        else: painter.setBrush(self.dbrush)
        if self.dtype == DRAWELL or self.dtype == DRAWL:
            painter.drawEllipse(self.mpos, self.dradius, self.dradius)
        elif self.dtype == DRAWRECT:            
            painter.drawRect(self.mpos.x()-self.dradius, self.mpos.y()-self.dradius, 2*self.dradius, 2*self.dradius)
        elif self.dtype == DRAWRECTR:
            painter.drawRoundedRect(self.mpos.x()-self.dradius, self.mpos.y()-self.dradius, 2*self.dradius, 2*self.dradius, 25.0, 25.0, mode=Qt.RelativeSize)    
            
        
        
# scene to store the list of selected objects, to be shown on the left
class ObjectListScene(QGraphicsScene):
    def __init__(self, main):
        super(ObjectListScene, self).__init__()
        self.main = main                            # main window
        self.backgroundImage = None
        self.setSceneRect(0, 0, WMIN, HMIN)
        self.objID = -1
        self.opacity = 0.6
        self.drawMBR = True
    
    def addObjectImage(self, qimg, x, y):
        self.clearSelection()
        self.objID += 1
        item = ObjectItem(qimg, x, y, self, self.objID, self.opacity, self.drawMBR)     # create and add the object, no need to use addItem        
        self.update()
        
    # add and display the existing objects
    def addObjects(self, ximage):
        for obj in ximage.objects:
            if self.objID < obj.id: self.objID = obj.id
            item = ObjectItem(obj.region, obj.x1, obj.y1, self, obj.id, self.opacity, self.drawMBR, obj.view)
            #item.setMBR_color(obj.view)
        self.update()    
    
    def deleteObject(self, objectItem):
        if objectItem:
            id = objectItem.ID
            self.removeItem(objectItem)
            self.main.ann.deleteObjects([id])
            self.main.imageListTable.updateTableRow(self.main.ann, self.main.ann.index)
            self.update()
    
    def setObjectViewLabel(self, id, viewLabel):
        if viewLabel in (V0, V1, V2, V3):
            self.main.ann.setObjectViewLabel(id, viewLabel)            
    
    def deleteAllObjects(self):
        self.clear()
        self.main.ann.deleteAllObjects()
        self.main.imageListTable.updateTableRow(self.main.ann, self.main.ann.index)
        self.update()
    
    def deleteSelectedObjects(self):
        items = self.selectedItems()
        for item in items:
            self.deleteObject(item)
    
    # set the (background) image of the scene
    def setImage(self, image):
        if image:
            self.backgroundImage = image.copy()
            w,h = image.width(), image.height()
            self.setSceneRect(0, 0, w, h)
            self.update()
        else:
            self.setSceneRect(0, 0, WMIN, HMIN)
    
    # overridden
    def drawBackground (self, painter, rect):
        if self.backgroundImage:
            painter.drawPixmap(0, 0, self.backgroundImage)
    
    def contextMenuEvent(self, event):
        item = self.itemAt(event.scenePos())
        if item is None and self.main.ann:
            menu = QMenu()
            for text, level in (
                    ("level 1: simple -- one object in the bin", 1),
                    ("level 2: simple -- mult. objects in the bin", 2),
                    ("level 3: medium -- baggage un-cluttered", 3),
                    ("level 4: difficult -- baggage cluttered", 4),
                    ("level 5: too difficult -- hard to see", 5),
                    ("skip  0: not labeled", 0)):
                wrapper = functools.partial(self.setLevel, level, text)            
                menu.addAction(text, wrapper)            
            menu.exec_(event.screenPos())

        super(ObjectListScene, self).contextMenuEvent(event)
        
    # difficulty level of the image
    def setLevel(self, level, text):        
        if level in (0,1,2,3,4,5):            
            self.main.ann.setLevel(level)            
            index = self.main.ann.index        
            print 'Image', index, 'level:', text
            self.main.imageListTable.updateTableRow(self.main.ann, index)
    
    def toggleShowMBR(self):
        self.drawMBR = not self.drawMBR
        for item in self.items():
            item.drawMBR = self.drawMBR
        self.update()
        
    def increaseOpacity(self):
        self.changeOpacity(0.1)
    def decreaseOpacity(self):
        self.changeOpacity(-0.1)
    def changeOpacity(self, incr):
        self.opacity += incr
        if self.opacity > 1.0: self.opacity = 1.0
        elif self.opacity < 0.1: self.opacity = 0.1
        # update all items/objects in the scene
        for item in self.items():
            item.opacity = self.opacity
        self.update()
    
class ImageTable(QTableWidget):
    def __init__(self, rows, columns, main):
        super(ImageTable, self).__init__(rows, columns, main)
        self.main = main
        self.ann = None
        self.setHorizontalHeaderLabels(["image filename", "objects", "label", "level"])
        self.resizeColumnsToContents()
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAlternatingRowColors(True)
        
    def select(self, row, column):
        self.clearSelection()
        self.setCurrentCell(row, column)        
    
    def setBGColor(self, row, column, color):
        item = self.item(row, column)
        item.setBackgroundColor(color) 
    
    def selectionChanged(self, selected, deselected):        
        items = self.selectedItems()
        rows = []
        for item in items:
            r,c = item.row(), item.column()            
            if c == 0 and r not in rows: rows.append(r)
        if len(rows) == 1:      # only one row is selected, go to that image
            self.main.toImage(rows[0])
    
    def contextMenuEvent(self, event):
        if not self.main.ann: return
        menu = QMenu()
        menu.addMenu("SET ALL IMAGES TO :")
        menu.addSeparator()
        for text, level in (
                ("level 1: simple -- one object in the bin", 1),
                ("level 2: simple -- mult. objects in the bin", 2),
                ("level 3: medium -- baggage un-cluttered", 3),
                ("level 4: difficult -- baggage cluttered", 4),
                ("level 5: too difficult -- hard to see", 5),
                ("skip  0: not labeled", 0)):
            wrapper = functools.partial(self.setLevel, level, text)            
            menu.addAction(text, wrapper)        
        menu.exec_(event.globalPos())
    
    def setLevel(self, level, text):        
        if level in (0,1,2,3,4,5):            
            self.main.ann.setLevelAll(level)
            print 'SET ALL IMAGES TO: ', text
            #self.updateTableRow(self.ann, index)
            self.updateTableView(self.main.ann)
            
    
    # populate the table with the images
    def updateTableView(self, annotation):
        if annotation is None: return
        if annotation.numImages() > 0:
            self.clearContents()
            self.setRowCount (annotation.numImages())
        for i in range(annotation.numImages()):
            self.updateTableRow(annotation, i)
        self.ann = annotation
        self.resizeColumnsToContents()
    
    def updateTableRow(self, annotation, index):
        if annotation is None: return
        nameItem = QTableWidgetItem(annotation.imageName(index))
        numItem = QTableWidgetItem(str(annotation.numObjects(index)))
        labelItem = QTableWidgetItem(str(annotation.image(index).label))
        levelItem = QTableWidgetItem(str(annotation.image(index).level))
        self.setItem(index, 0, nameItem)
        self.setItem(index, 1, numItem)
        self.setItem(index, 2, labelItem)
        self.setItem(index, 3, levelItem)

class GraphicsView(QGraphicsView):

    def __init__(self, parent, dragMode=QGraphicsView.NoDrag):
        super(GraphicsView, self).__init__(parent)        
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode (dragMode) 
        self.scene = parent
        self.fitImageView()       
        self.fitmode = True
        
    # Ctrl + wheel to zoom in/out
    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            factor = 1.41 ** (event.delta() / 240.0)            
            self.scale(factor, factor)
            
    
    def mouseDoubleClickEvent(self, event):
        self.fitOrResetView()
        super(GraphicsView, self).mouseDoubleClickEvent(event)
    
    def fitOrResetView(self):
        self.fitmode = not self.fitmode
        if self.fitmode: 
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
            print 'Fit the image in view'
        else:
            self.resetTransform()
            print 'Actual image size'
    
    def fitImageView(self):
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio) 

# main window containing all the widgets
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        
        self.createMenus()
        
        # annotations, image list, etc.
        self.ann = None
        self.imageDir = None
        # current image shown
        piximage = None
        self.startUp = True
        
        ## drawing scene and view on the right
        self.sceneDraw = ImageDrawScene(self)
        self.sceneDraw.setBackground(piximage)        
        self.viewDraw = GraphicsView(self.sceneDraw, QGraphicsView.NoDrag)
        self.viewDraw.installEventFilter(self)
        self.viewDraw.setStatusTip('Painting area')
        
        ## list of objects scene and view on the left
        self.sceneList = ObjectListScene(self)
        self.sceneList.setImage(piximage)        
        self.viewList = GraphicsView(self.sceneList, QGraphicsView.RubberBandDrag)
        self.viewList.setRubberBandSelectionMode(Qt.ContainsItemShape)
        self.viewList.installEventFilter(self)
        self.viewList.setStatusTip('List of already selected objects')
        
        ## list of images
        self.imageListTable = ImageTable(10, 4, self)
        
        # text fields for class/subclass name
        classLabel = QLabel("Class:")
        subclassLabel = QLabel("Subclass:")
        self.classText = QLineEdit("")
        self.classText.setReadOnly(True)
        self.subclassText = QLineEdit("")
        self.subclassText.setReadOnly(True)
        #self.connect(self.classText, SIGNAL('editingFinished()'), self.updateClassNames)
        #self.connect(self.subclassText, SIGNAL('editingFinished()'), self.updateClassNames)
        
        
        
        ## buttons - todo: setShortcut (self, QKeySequence key)
        buttonPrev = QPushButton("Previous", self)
        buttonPrev.setIcon(QIcon('./icons/prev.png'))
        buttonPrev.setStatusTip('Go to the previous image  [ shortcut: Ctrl + Space ]')
        buttonPrev.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_Space))
        self.connect(buttonPrev,  SIGNAL('clicked()'), self.onButtonPrev)
        
        buttonNext = QPushButton("Next", self)
        buttonNext.setIcon(QIcon('./icons/next.png'))
        buttonNext.setStatusTip('Go to the next image  [ shortcut: Space ]')
        buttonNext.setShortcut(QKeySequence(Qt.Key_Space))
        self.connect(buttonNext,  SIGNAL('clicked()'), self.onButtonNext)
        
        buttonAddObject = QPushButton("Add", self)
        buttonAddObject.setIcon(QIcon('./icons/add.png'))
        buttonAddObject.setEnabled(False)
        #buttonAddObject.setStatusTip('Add the selected object  [ shortcut: Ctrl + A ]')
        #buttonAddObject.setShortcut(QKeySequence("Ctrl+a"))     
        #self.connect(buttonAddObject,  SIGNAL('clicked()'), self.onButtonAddObject)
        
        buttonDeleteObject = QPushButton("Delete", self)
        buttonDeleteObject.setIcon(QIcon('./icons/delete.png'))
        buttonDeleteObject.setEnabled(False)
        #buttonDeleteObject.setStatusTip('Delete the selected object(s)     [ shortcut: Del ]')
        #buttonDeleteObject.setShortcut(QKeySequence(QKeySequence.Delete))               # Delete key
        #self.connect(buttonDeleteObject,  SIGNAL('clicked()'), self.onButtonDeleteObject)
        
        buttonResetPaint = QPushButton("Reset", self)
        buttonResetPaint.setIcon(QIcon('./icons/refresh.png'))
        buttonResetPaint.setEnabled(False)
        #buttonResetPaint.setStatusTip('Clear/reset the painting on the right image')
        #self.connect(buttonResetPaint,  SIGNAL('clicked()'), self.onButtonResetPaint)
        
        buttonSave = QPushButton("Save", self)
        buttonSave.setIcon(QIcon('./icons/save.png'))
        buttonSave.setStatusTip('Save annotation list     [ shortcut: Ctrl + S ]')
        buttonSave.setShortcut(QKeySequence(QKeySequence.Save))                 # Ctrl + S
        self.connect(buttonSave,  SIGNAL('clicked()'), self.onButtonSave)
        
        buttonExit = QPushButton("Exit", self)
        buttonExit.setIcon(QIcon('./icons/exit.png'))
        buttonExit.setStatusTip('Exit the application    [ shortcut: Ctrl + Q ]')
        self.connect(buttonExit,  SIGNAL('clicked()'), self.close)
        
        # drawing/painting/brush type combo box
        dtypeComboBox = QComboBox()
        # BRUSH_TYPES_STR = [ "Line", "Ellipse", "Rectangle", "Rounded rectangle"] --- global variable
        dtypeComboBox.addItems(BRUSH_TYPES_STR)        
        #dtypeComboBox.setStatusTip('Brush type for painting on the image')
        #self.connect(dtypeComboBox,  SIGNAL('activated(int)'), self.changeBrushType)
        dtypeComboBox.setEnabled(False)
        typeLabel = QLabel("&Brush type:")
        typeLabel.setBuddy(dtypeComboBox)
                
        self.buttonBrushColor = QPushButton("Brush color", self)
        self.buttonBrushColor.setIcon(QIcon(self.getColorRectImage(BRUSH_COLOR)))
        self.brushColor = BRUSH_COLOR
        #self.buttonBrushColor.setStatusTip('Select brush color')
        #self.connect(self.buttonBrushColor,  SIGNAL('clicked()'), self.changeBrushColor)
        self.buttonBrushColor.setEnabled(False)
        
        ## slider for brush size 
        brushSizeSlider = QSlider(Qt.Horizontal, self)
        brushSizeSlider.setMinimum(1)
        brushSizeSlider.setMaximum(100)
        brushSizeSlider.setTickPosition(QSlider.TicksAbove)
        brushSizeSlider.setTickInterval(10)
        brushSizeSlider.setSingleStep(1)
        brushSizeSlider.setValue(BRUSH_RADIUS)
        self.changeBrushRadius(BRUSH_RADIUS)
        #brushSizeSlider.setStatusTip('Brush radius, for painting on the image')        
        #self.connect(brushSizeSlider,  SIGNAL('valueChanged(int)'), self.changeBrushRadius)
        brushSizeSlider.setEnabled(False)
        
        ## status bar
        self.statusBar = QStatusBar(self)
        self.setStatusBar(self.statusBar)
        
        ### Layouts ### 
        # images & image list in the center
        layoutC = QHBoxLayout()        
        layoutC.addWidget(self.viewDraw)        
        layoutC.addSpacing(20)
        layoutC.addWidget(self.viewList)
        layoutC.addSpacing(20)
        
        layoutR0 = QHBoxLayout()
        layoutR0.addWidget(classLabel)
        layoutR0.addStretch(0)
        layoutR0.addWidget(self.classText)
        layoutR0.addSpacing(5)
        layoutR0.addWidget(subclassLabel)
        layoutR0.addStretch(0)
        layoutR0.addWidget(self.subclassText)
                
        layoutR1 = QHBoxLayout()
        layoutR1.addWidget(typeLabel)
        layoutR1.addStretch(0)
        layoutR1.addWidget(dtypeComboBox)
        layoutR1.addSpacing(10)
        layoutR1.addWidget(self.buttonBrushColor)
        
        layoutR = QVBoxLayout()
        layoutR.addItem(layoutR0)
        layoutR.addSpacing(10)
        layoutR.addWidget(self.imageListTable)
        layoutR.addSpacing(10)        
        layoutR.addItem(layoutR1)
        layoutR.addSpacing(5)
        layoutR.addWidget(brushSizeSlider)
                
        layoutC.addItem(layoutR)
        
        # layout for controls at the bottom
        layoutB = QHBoxLayout()
        layoutB.addWidget(buttonDeleteObject)
        layoutB.addSpacing(5)
        layoutB.addWidget(buttonAddObject)
        layoutB.addSpacing(5)        
        layoutB.addWidget(buttonResetPaint)
        layoutB.addSpacing(20)
        layoutB.addWidget(buttonPrev)
        layoutB.addSpacing(50)
        layoutB.addWidget(buttonNext)
        layoutB.addSpacing(120)
        layoutB.addWidget(buttonSave)
        layoutB.addSpacing(80)
        layoutB.addWidget(buttonExit)
        layoutB.addSpacing(40)
                
        layout = QVBoxLayout()
        layout.addItem(layoutC)
        layout.addSpacing(10)
        layout.addItem(layoutB)
        
        self.widget = QWidget()
        self.widget.setLayout(layout)        
        self.setCentralWidget(self.widget)
        
        self.setWindowTitle("XRanT2 : X-Ray Annotation Tool (difficulty level & view annotation)")
        self.setWindowIcon(QIcon('./icons/x-icon.png'))
        #self.setWindowIcon(QIcon('./icons/xray-icon.png'))
        
        self.statusMessage("XRanT2 ready. Browse an image directory to get started [File/Ctrl-O]")
            
    def createMenus(self):
        menuBar = self.menuBar()
        
        ## File menu
        self.fileMenu = menuBar.addMenu("&File")
        
        #self.fileOpenImageDir = QAction("&Open image directory..", self, shortcut="Ctrl+O", triggered=self.loadImageDir)
        #self.fileOpenImageDir.setStatusTip("Select the directory containing the images to annotate")
        #self.fileMenu.addAction(self.fileOpenImageDir)
        
        #self.changeAnnDir = QAction("Change output directory..", self, triggered=self.changeAnnotationDir)
        #self.changeAnnDir.setStatusTip("Change the current output directory to any directory")
        #self.fileMenu.addAction(self.changeAnnDir)
        
        #self.fileMenu.addSeparator()
        
        
        
        self.loadAnn = QAction("Load annotation list..", self, triggered=self.loadAnnotation)
        self.loadAnn.setStatusTip("Load existing annotation list from file")
        self.fileMenu.addAction(self.loadAnn)
        
        self.fileMenu.addSeparator()
        
        self.saveAll = QAction("Save", self, triggered=self.onButtonSave)
        self.saveAll.setStatusTip("Save annotation list (over-write)")
        self.fileMenu.addAction(self.saveAll)
        
        self.saveAnnAs = QAction("Save annotation list as..", self, triggered=self.saveAnnotationAs)
        self.saveAnnAs.setStatusTip("Save a copy of annotation list to a specified file")
        self.fileMenu.addAction(self.saveAnnAs)
        
        self.fileMenu.addSeparator()
                
        
        self.fileExitAct = QAction("E&xit", self, shortcut="Ctrl+Q", triggered=self.close)
        self.fileExitAct.setStatusTip("Exit the application!")
        self.fileMenu.addAction(self.fileExitAct)
        
        self.helpMenu = menuBar.addMenu("&Help")
        self.helpAbout = QAction("&About", self, triggered=self.helpAbout)
        self.helpMenu.addAction(self.helpAbout)   
    
    ### ### ### Event handling    ### ### ###
    
    # handle previous/next image button events
    def onButtonPrev(self):
        ind = self.ann.prev()
        if ind != self.ann.index:
            self.imageListTable.select(ind, 0)
    def onButtonNext(self):        
        ind = self.ann.next()
        if ind != self.ann.index:
            self.imageListTable.select(ind, 0)
            
    def onButtonAddObject(self):        
        self.addObject()
    def onButtonDeleteObject(self):
        self.sceneList.deleteSelectedObjects()
    def onButtonResetPaint(self):
        self.sceneDraw.resetForeground()
    # TODO: ask overwrite
    def onButtonSave(self):
        if self.ann is not None:
            #self.ann.saveCurrentObjectMasks()
            self.ann.saveAnnotationList()            
        else: print 'Nothing to save!'
    def closeEvent(self, event):
        if self.ann:
            ret = QMessageBox.question(self, "Exit application", "Save annotation list before exit?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if ret == QMessageBox.Yes: self.onButtonSave()
            elif ret == QMessageBox.Cancel: event.ignore(); print 'Cancel'; return
        event.accept()
        
    ### FUNCTIONS ###
    # TODO: ask overwrite
    def saveAnnotationAs(self):
        if not self.ann: return
        fileName = QFileDialog.getSaveFileName(self, "Save a copy of annotation list as", self.ann.annotationDir + self.ann.getAnnotationListFile(), "All Files (*);;Text Files (*.txt)")
        if fileName:
            self.ann.saveAnnotationListAs(fileName)
    
    def loadAnnotation(self):
        if self.ann:
            ret = QMessageBox.question(self, "Load annotation", "Save current annotations before loading?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if ret == QMessageBox.Yes: self.onButtonSave()
            elif ret == QMessageBox.Cancel: return       
        dir = "/home/bastan/research/sicura/data/"
        if self.ann: dir = self.ann.annotationDir
        fileName = QFileDialog.getOpenFileName(self, "Load annotation list from file", dir, "All Files (*);;Text Files (*.txt)")
        if fileName:
            print fileName
            self.ann = Annotation(fileName)
            self.startUp = True
            self.updateClassNamesView()
            self.imageListTable.updateTableView(self.ann)
            self.imageListTable.select(0,0)
    
    def changeAnnotationDir(self):
        if not self.ann: print 'No annotation yet!'; return
        options = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly
        directory = QFileDialog.getExistingDirectory(self, "Select output annotation directory", self.ann.annotationDir, options)
        if directory:
            self.ann.setAnnotationDir(directory)
    
    def loadImageDir(self):
        if self.ann:
            ret = QMessageBox.question(self, "Load annotation", "Save current annotations before loading?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if ret == QMessageBox.Yes: self.onButtonSave()
            elif ret == QMessageBox.Cancel: return
        if self.imageDir is None: self.imageDir = "/home/bastan/research/sicura/data"
        fd = QFileDialog(None, "Select image folder", self.imageDir, "*.png")
        #fd = QFileDialog(None, "Select image folder", ".", "*.png")
        fd.setFileMode(QFileDialog.Directory)        
        fd.setNameFilter("*.png;;*.jpg;;*.jpeg;;*.pgm;;*.*")
        if fd.exec_() == QDialog.Rejected: return        
        fileExt = fd.selectedNameFilter()
        # load the image file names from the selected directory
        self.ann = Annotation()
        self.ann.loadDir(fd.directory().absolutePath(), fd.directory().dirName(), fd.selectedNameFilter())
        self.startUp = True
        self.updateClassNames()
        self.imageListTable.updateTableView(self.ann)
        self.imageListTable.select(0,0)     # select and goto the first image       
               
    def toImage(self, index):
        if self.ann is not None:
            #if not self.startUp:
            #    self.ann.saveCurrentObjectMasks()
            #    self.ann.deleteObjectMasks()
            index = self.ann.goto(index)
            self.ann.loadObjectImages(index, self.brushColor, False)
            self.imageListTable.updateTableRow(self.ann, self.ann.index)
            self.sceneList.clear()
            self.showCurrentImage()
            self.startUp = False
            print 'Image', index+1
            
    # load the current image from disk and display it
    def showCurrentImage(self):
        if self.ann is not None and self.ann.numImages() > 0:            
            imageFile = self.ann.curImagePath()
            if os.path.exists(imageFile):
                piximage = QPixmap(imageFile)
                self.showImage(piximage)                
    
    def showImage(self, piximage):        
        self.sceneList.setImage(piximage)
        self.sceneList.addObjects(self.ann.image(self.ann.index))
        self.viewList.fitImageView()
        self.sceneList.update()
        self.sceneDraw.setImage(piximage)
        self.viewDraw.fitImageView()
        self.sceneDraw.update()        
    
    # add the selected object to the scene and to the list of annotations
    def addObject(self):
        mask = self.sceneDraw.getObjectMask()       
        x1,y1,w,h = getMBR_numpy(mask)
        if x1 < 0: return
        objImg = self.sceneDraw.foregroundImage.copy(x1, y1, w, h)
        self.sceneList.addObjectImage(objImg, x1, y1)
        self.sceneDraw.resetForeground()
        self.ann.addObject(mask, objImg, x1, y1, self.sceneList.objID)        
        self.imageListTable.updateTableRow(self.ann, self.ann.index)        
    
    def updateClassNames(self):
        className = self.classText.text()
        subclassName = self.subclassText.text()        
        if len(className) < 1 : className = 'none'
        if len(subclassName) < 1 : subclassName = 'none'        
        if self.ann is not None:
            self.ann.setClassName(className, subclassName)
        print 'Updated class names and directories'
    
    def updateClassNamesView(self):
        className = self.ann.className
        subclassName = self.ann.subclassName
        if len(className) < 1 or  className == 'none': self.classText.setText("")            
        else: self.classText.setText(className)
        if len(subclassName) < 1 or  subclassName == 'none': self.subclassText.setText("")            
        else: self.subclassText.setText(subclassName)        
    
    def changeBrushRadius(self, value):
        self.sceneDraw.setRadius(value)
    def changeBrushType(self, value):
        self.sceneDraw.setBrushType(BRUSH_TYPES_INT[value])
    
    def getColorRectImage(self, color, w=80, h=60):
        qimage = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        qimage.fill(color.rgba())
        return QPixmap.fromImage(qimage)
        
    def changeBrushColor(self):
        cd = QColorDialog(self.sceneDraw.dcolor)
        cd.setOption(QColorDialog.ShowAlphaChannel, True)
        cd.exec_()
        color = cd.selectedColor()
        self.sceneDraw.setBrushColor(color)
        self.buttonBrushColor.setIcon(QIcon(self.getColorRectImage(color)))
        self.brushColor = color
        
    def statusMessage(self, message):
        self.statusBar.showMessage(message)
    def helpAbout(self):        
        QMessageBox.about(self, "About XRanT2",
                "<b>XRanT2: X-Ray Annotation Tool (image difficulty level and object view)</b><br>"
                "Author: Muhammet Bastan<br>IUPR @TU-KL<br>mubastan@iupr.com<br>July-December 2011")
    
if __name__ == "__main__":    
    app = QApplication(sys.argv)
    mainWindow = MainWindow()    
    #mainWindow.show()
    mainWindow.showMaximized()
    sys.exit(app.exec_())