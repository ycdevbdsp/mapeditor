from math import floor
import sys
import os
import re
from mapeditor import *
import json
import placedataheader
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QMessageBox
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
from PyQt5.QtCore import Qt
import clicklabel

class MouseTracker(QtCore.QObject):
    positionChanged = QtCore.pyqtSignal(QtCore.QPoint)
    clicked = QtCore.pyqtSignal(QtCore.QPoint)

    def __init__(self, widget):
        super().__init__(widget)
        self._widget = widget
        self.widget.setMouseTracking(True)
        self.widget.installEventFilter(self)

    @property
    def widget(self):
        return self._widget

    def eventFilter(self, o, e):
        if o is self.widget and e.type() == QtCore.QEvent.MouseMove:
            self.positionChanged.emit(e.pos())

        return super().eventFilter(o, e)

class MapEditor(QMainWindow):

    MapSquareSize = 16
    OriginX = 0
    OriginY = 0
    LastX = 0
    LastY = 0
    LastMouseX = 0
    LastMouseY = 0
    MapData = None
    MapPlaceData = None
    InitializeLocalPlaceData = False
    LocalPlaceData = {}
    SelectedSquare = None
    ThisZoneID = 0
    NewPlaceData = None
    OutputPlaceData = ""


    def loadFiles(self):
        fileList = os.listdir('F:\Games\Pokemon\json')
        for f in fileList:
            with open('F:\Games\Pokemon\json\{0}'.format(f)) as infile:
                mapData = json.load(infile)
                self.OriginX = mapData['originX']
                self.OriginY = mapData['originY']
                lastX = 0
                lastY = 0

                #Need to determine the "bottom right" of this map, which we will do by taking the X/Y
                #of all elements in the map data and adding the width/height, getting a "bottom right"
                #coordinate of each map object until we find the greatest one

                for el in mapData['mapData']:
                    brX = el['x'] + el['width']
                    brY = el['y'] + el['height']

                    if brX > lastX:
                        lastX = brX
                    if brY > lastY:
                        lastY = brY

                self.LastX = lastX
                self.LastY = lastY
            
            mapList = os.listdir('F:\Games\Pokemon\MonoBehaviour')
            for m in mapList:
                coords = re.findall(r'([0-9][0-9])', m)
                #coords contains the two numbers from file name, e.g. map01_08
                #multiple the coords by 32, then see if it exists in the bounds of
                #the map we just got the bounds of. This could be more optimized, but
                #I'm literally only doing this to get info. It's not a regular thing.

                #if we have a match, just log it and we'll move on to the next map data
                if int(coords[0]) * 32 >= int(self.OriginX) and int(coords[0]) * 32 <= int(self.LastX) and int(coords[1]) * 32 >= int(self.OriginY) and int(coords[1]) * 32 <= int(self.LastY):
                    print ("{0}, {1}".format(m, mapData['area']))
                    break

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.lineType = "SolidLine"
        tracker = MouseTracker(self.ui.frame)
        tracker.positionChanged.connect(self.mouseMoveEvent)
        self.ui.frame.clicked.connect(self.mousePressed)
        self.ui.actionLoad_Map.triggered.connect(self.loadMap)
        self.ui.actionLoad_Map_Data.triggered.connect(self.loadMapPlaceData)
        self.ui.actionSave.triggered.connect(self.saveChanges)

        self.ui.objectPositionX.valueChanged.connect(self.positionXChanged)
        self.ui.objectPositionY.valueChanged.connect(self.positionYChanged)
        self.ui.objectDirection.currentIndexChanged.connect(self.directionChanged)
        self.ui.objectID.textChanged.connect(self.idChanged)

        #PlaceData information setup. Default to hiding the information specific for trainers.

        self.ui.trainerInfoFrame.setEnabled(False)
        
        self.LocalPlaceData = {}

    def repaintMap(self):
        self.paintMap()
        self.ui.frame.repaint()

    def paintMap(self):
        if self.MapData is None:
            return
        
        self.ui.frame.pixmap().fill(QtGui.QColor("white"))
        qp = QPainter(self.ui.frame.pixmap())
        for el in self.MapData['mapData']:
            if el['x'] < self.OriginX or el['y'] < self.OriginY:
                continue
            if "Grass" in el['name'] or "plant" in (el['name']).lower():
                qp.setBrush(QBrush(Qt.green, Qt.SolidPattern))
            elif "Tree" in el['name']:
                qp.setBrush(QBrush(QColor(34,139,34), Qt.DiagCrossPattern))
            # elif "Ground" in el['name']:
            #     continue
            elif "Mart" in el['name'] or "Shop" in el['name']:
                qp.setBrush(QBrush(Qt.blue, Qt.SolidPattern))
                #qp.setBrush(QBrush(QColor(165, 42, 42), Qt.SolidPattern))
            elif "PokeCen" in el['name']:
                qp.setBrush(QBrush(Qt.red, Qt.SolidPattern))
            elif "PokeCompany" in el['name']:
                qp.setBrush(QBrush(QColor(138,43,226), Qt.SolidPattern))
            elif "Water" in el['name']:
                qp.setBrush(QBrush(QColor(173,216,230), Qt.SolidPattern))
            elif "House_01 (" in el['name']:
                qp.setBrush(QBrush(QColor(0, 153, 76), Qt.SolidPattern))
            else:
                qp.setBrush(QBrush(QColor(211, 211, 211), Qt.SolidPattern))

            if el['x'] == 159 and el['y'] == 769:
                print("white square")
            qp.drawRect(
                ((el['x'] - self.OriginX) * self.MapSquareSize),
                ((el['y'] - self.OriginY - el['height']) * self.MapSquareSize),
                self.MapSquareSize * el['width'], self.MapSquareSize * el['height'])

            # for mesh in el['meshes']:
            #     qp.drawRect(
            #         floor(((el['x'] + (el['width'] * mesh['x'])) - self.OriginX) * self.MapSquareSize),
            #         floor(((el['y'] + (el['height'] * mesh['y'])) - self.OriginY - el['height']) * self.MapSquareSize),
            #         self.MapSquareSize, self.MapSquareSize)
    
        if self.MapPlaceData is not None:
            #Drop the relevant PlaceData onto the map.  
            placeData = self.MapPlaceData
            qp.setBrush(QBrush(QColor(255,165,0), Qt.SolidPattern))
            index = 0
            for pd in placeData['Data']:
                #It's relevant if its position is within the bounds of our area.
                pos = { "x": pd['Position']['x'], "y": pd['Position']['y']}
                if pos['x'] > self.OriginX and pos['x'] < self.LastX and pos['y'] > self.OriginY and pos['y'] < self.LastY:                    
                    qp.drawRect(
                        floor((pos['x'] - self.OriginX) * self.MapSquareSize),
                        floor((pos['y'] - self.OriginY) * self.MapSquareSize),
                        self.MapSquareSize, self.MapSquareSize)

                    #This is a very simple way to note a trainer. Ultimately I'd like to show a sprite or something
                    if pd['TrainerID'] != 0:
                        qp.drawText( 
                            floor((pos['x'] - self.OriginX) * self.MapSquareSize + (self.MapSquareSize/2)),
                            floor((pos['y'] - self.OriginY) * self.MapSquareSize + (self.MapSquareSize)),
                            'T')
                    if self.InitializeLocalPlaceData is True:
                        self.LocalPlaceData[str(pos['x']) + str(pos['y'])] = {"index": index, "data": pd}
                index += 1
            self.InitializeLocalPlaceData = False
        
        #draw the selected square if there is one

        if self.SelectedSquare != None:
            qp.setBrush(QBrush(QColor(255,255,153, 200), Qt.SolidPattern))
            qp.drawRect(
                floor(self.SelectedSquare['x'] * self.MapSquareSize),
                floor(self.SelectedSquare['y'] * self.MapSquareSize),
                self.MapSquareSize, self.MapSquareSize
            )

        #width/height of frame
        frameHeight = (self.LastY - self.OriginY) * self.MapSquareSize
        frameWidth = (self.LastX - self.OriginX) * self.MapSquareSize

        mapSquareSize = self.MapSquareSize  #pixels
        for i in range(floor(frameWidth/mapSquareSize)+1):
            qp.drawLine(i*mapSquareSize, 0, i*mapSquareSize, frameHeight*mapSquareSize)

        for j in range(floor(frameHeight/mapSquareSize)+1):
            qp.drawLine(0, j*mapSquareSize, frameWidth*mapSquareSize, j*mapSquareSize)

        qp.end()
        
    def loadMap(self):

        file = QFileDialog.getOpenFileName(self, 'Open map file', './maps')

        if file[0]:
            # First clear the map and placedata. This will force the user to have to reload PlaceData,
            # which could be annoying. But.

            self.MapData = None
            self.MapPlaceData = None

            with open(file[0]) as infile:
                self.MapData = json.load(infile)
                self.OriginX = self.MapData['originX']
                self.OriginY = self.MapData['originY']
                lastX = 0
                lastY = 0

                #Need to determine the "bottom right" of this map, which we will do by taking the X/Y
                #of all elements in the map data and adding the width/height, getting a "bottom right"
                #coordinate of each map object until we find the greatest one

                for el in self.MapData['mapData']:
                    brX = el['x'] + el['width']
                    brY = el['y'] + el['height']

                    if brX > lastX:
                        lastX = brX
                    if brY > lastY:
                        lastY = brY

                self.LastX = lastX
                self.LastY = lastY
            
            
            #print("lastX:{0}, originX:{1}, lastY:{2}, originY:{3}".format(lastX, self.OriginX, lastY, self.OriginY))
            canvas = QtGui.QPixmap(self.MapSquareSize * (lastX - self.OriginX), self.MapSquareSize * (lastY - self.OriginY))
            self.ui.frame.setPixmap(canvas)
            self.paintMap()
            self.show()
        return

    def loadMapPlaceData(self):
        file = QFileDialog.getOpenFileName(self, 'Open map data file', './mapdata')

        self.InitializeLocalPlaceData = True

        if file[0]:
            with open(file[0]) as infile:
                self.OutputPlaceData = os.path.basename(file[0])
                self.MapPlaceData = json.load(infile)
                self.ThisZoneID = self.MapPlaceData['Data'][0]['zoneID']
                self.paintMap()
                
    def saveChanges(self):
        #Run through our local place data and update any changes made to the original placedata.
        #New changes are automatically added to the original placedata

        try:
            if self.OutputPlaceData == "":
                print("No place data loaded!")
                return
            for pd in self.LocalPlaceData:
                index = self.LocalPlaceData[pd]['index']
                self.MapPlaceData['Data'][index] = self.LocalPlaceData[pd]['data']

            if os.path.exists("output") == False:
                os.makedirs("output")

            with open("output\\new_" + self.OutputPlaceData, 'w+', encoding="utf-8") as outfile:
                json.dump(self.MapPlaceData, outfile)
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("An error occurred trying to save your changes:\n" + str(e))
            msg.show()
        return

    def mouseMoveEvent(self, event):
        self.paintMap()
        x = floor(event.x() / self.MapSquareSize)
        y = floor(event.y() / self.MapSquareSize)
        if x == self.LastMouseX and y == self.LastMouseY:
            return
        
        self.LastMouseX = x
        self.LastMouseY = y

        text = "x: {0}, y: {1}".format(x + self.OriginX, y + self.OriginY)
        self.ui.labelMapCoord.setText(text)
        
        if self.ui.frame is None:
            return
        if self.ui.frame.pixmap() is None:
            return
            
        qp = QPainter(self.ui.frame.pixmap())
        qp.setBrush(QBrush(QColor(255,255,153, 200), Qt.SolidPattern))
        
        qp.eraseRect(
            floor(x * self.MapSquareSize),
            floor(y * self.MapSquareSize),
            floor(self.MapSquareSize), floor(self.MapSquareSize))
        qp.drawRect(
            floor(x * self.MapSquareSize),
            floor(y * self.MapSquareSize),
            floor(self.MapSquareSize), floor(self.MapSquareSize))
        qp.end()
        self.ui.frame.repaint()
        
    def mousePressed(self, event):
        self.SelectedSquare = None

        x = floor(event.x() / self.MapSquareSize)
        y = floor(event.y() / self.MapSquareSize)
        
        print(x)
        print(self.OriginX)
        print(y)
        print(self.OriginY)
        self.LastMouseX = x
        self.LastMouseY = y
        
        self.NewPlaceData = None
        
        pdIndex = str(x + self.OriginX) + str(y + self.OriginY)
        #Update the object info with the object we clicked, or clear it if there's nothing there.

        if pdIndex in self.LocalPlaceData:
            self.ui.objectPositionX.setValue(x + self.OriginX)
            self.ui.objectPositionY.setValue(y + self.OriginY)
            self.ui.objectID.setText(self.LocalPlaceData[pdIndex]['data']['ID'])

            rotation = self.LocalPlaceData[pdIndex]['data']['Rotation']

            if rotation == 0:
                self.ui.objectDirection.setCurrentText("Down")
            elif rotation == 90:
                self.ui.objectDirection.setCurrentText("Left")
            elif rotation == 180:
                self.ui.objectDirection.setCurrentText("Up")
            else:
                self.ui.objectDirection.setCurrentText("Right")

            #If this is a trainer, set and enable the Trainer ID

            if self.LocalPlaceData[pdIndex]['data']['TrainerID'] != 0:
                self.ui.trainerInfoFrame.setEnabled(True)
                self.ui.trainerID.setValue(self.LocalPlaceData[pdIndex]['data']['TrainerID'])
            else:
                self.ui.trainerInfoFrame.setEnabled(False)
                self.ui.trainerID.setValue(0)
        else:
            self.ui.objectPositionX.setValue(x + self.OriginX)
            self.ui.objectPositionY.setValue(y + self.OriginY)
            self.ui.objectID.setText("")
            self.ui.objectDirection.setCurrentText("Down")
            self.ui.trainerInfoFrame.setEnabled(False)
            self.ui.trainerID.setValue(0)

        # #allow deselecting the square
        # if self.SelectedSquare != None and x == self.SelectedSquare['x'] and y == self.SelectedSquare['y']:
        #     self.SelectedSquare = None
        # else:
        self.SelectedSquare = {'x': x, 'y': y}

        self.repaintMap()

    def positionXChanged(self):
        #If we haven't selected a square, just return.
        
        if self.SelectedSquare is None:
            return
        newX = self.ui.objectPositionX.value()

        pdIndex = str(self.SelectedSquare['x'] + self.OriginX) + str(self.SelectedSquare['y'] + self.OriginY)
        
        # if this pdIndex already exists in our local placedata, grab the true index from it and update
        # the corresponding entry in the true PlaceData. Otherwise, create a new entry for the true
        # PlaceData

        if pdIndex in self.LocalPlaceData:
            trueIndex = self.LocalPlaceData[pdIndex]['index']
            self.MapPlaceData['Data'][trueIndex]['Position']['x'] = newX
        else:
            if self.NewPlaceData is None:
                self.NewPlaceData = placedataheader.placedataBlank
            self.NewPlaceData['Position']['x'] = newX

        #Now update the LocalPlaceData since the location has changed. We can use whatever the current
        #value of the Y spinbox is. Then delete the old entry.

        self.LocalPlaceData[str(newX) + str(self.ui.objectPositionY.value())] = self.LocalPlaceData[pdIndex]
        del self.LocalPlaceData[pdIndex]
        self.SelectedSquare['x'] = newX - self.OriginX
        self.repaintMap()
        

    
    def positionYChanged(self):
        #If we haven't selected a square, just return

        if self.SelectedSquare is None:
            return
        
        newY = self.ui.objectPositionY.value()

        pdIndex = str(self.SelectedSquare['x'] + self.OriginX) + str(self.SelectedSquare['y'] + self.OriginY)

        # if this pdIndex already exists in our local placedata, grab the true index from it and update
        # the corresponding entry in the true PlaceData. Otherwise, create a new entry for the true
        # PlaceData

        if pdIndex in self.LocalPlaceData:
            trueIndex = self.LocalPlaceData[pdIndex]['index']
            self.MapPlaceData['Data'][trueIndex]['Position']['y'] = self.ui.objectPositionY.value()
        else:
            if self.NewPlaceData is None:
                self.NewPlaceData = placedataheader.placedataBlank
            self.NewPlaceData['Position']['y'] = self.ui.objectPositionY.value()

        #Now update the LocalPlaceData since the location has changed. We can use whatever the current
        #value of the X spinbox is. Then delete the old entry.

        self.LocalPlaceData[str(self.ui.objectPositionX.value()) + str(newY)] = self.LocalPlaceData[pdIndex]
        del self.LocalPlaceData[pdIndex]
        self.SelectedSquare['y'] = newY - self.OriginY
        self.repaintMap()

    def directionChanged(self, i):
        if self.SelectedSquare is None:
            return

        direction = self.ui.objectDirection.currentText()
        rotation = 0

        if direction == "Down":
            rotation = 0
        elif direction == "Left":
            rotation = 90
        elif direction == "Up":
            rotation = 180
        else:
            rotation = 270

        pdIndex = str(self.SelectedSquare['x'] + self.OriginX) + str(self.SelectedSquare['y'] + self.OriginY)

        if pdIndex in self.LocalPlaceData:
            trueIndex = self.LocalPlaceData[pdIndex]['index']
            self.MapPlaceData['Data'][trueIndex]['Rotation'] = rotation
        else:
            if self.NewPlaceData is None:
                self.NewPlaceData = placedataheader.placedataBlank
            self.NewPlaceData['Rotation'] = rotation
        
    def idChanged(self):
        if self.SelectedSquare is None:
            return

        id = self.ui.objectID.text()
        pdIndex = str(self.SelectedSquare['x'] + self.OriginX) + str(self.SelectedSquare['y'] + self.OriginY)

        if pdIndex in self.LocalPlaceData:
            trueIndex = self.LocalPlaceData[pdIndex]['index']
            self.MapPlaceData['Data'][trueIndex]['ID'] = id
        else:
            if self.NewPlaceData is None:
                self.NewPlaceData = placedataheader.placedataBlank
            self.NewPlaceData['ID'] = id
        
if __name__=="__main__":
    app = QApplication(sys.argv)
    w = MapEditor()
    w.show()
    sys.exit(app.exec_())