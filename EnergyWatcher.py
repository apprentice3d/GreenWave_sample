import MaxPlus
import pymxs
from PySide.QtGui import *
import os
import pyqtgraph as pg
import numpy as np
import thread

rt = pymxs.runtime
attime = pymxs.attime
treeView = None
beacon_list_view = None  # used
beacon_references = dict()
total_watts = 0
efficacy = 0.1
plot = None
tool_layout = None
interval = None
progress_bar = None


class Beacon:
    def __init__(self, item):
        self.name = item.name
        self.position = item.position
        self.movement_history = np.zeros((1, 101))
        self.energy_value_history = list()
        self.reference = item

    def totalEnergy(self):
        return sum(self.energy_value_history) * efficacy

    def updateMovementHistory(self):
        frame = int(rt.sliderTime)
        previous_value = self.movement_history[0][frame - 1] if frame > 1 else 0
        current_value = self.reference.position.z
        self.movement_history[0][frame] = current_value
        self.energy_value_history.append(abs(previous_value - current_value))


class MainWindow(QWidget):
    def __init__(self, ui_class, parent=None):
        QWidget.__init__(self, parent)
        self.ui = ui_class()
        self.ui.setupUi(self)


def loadUI():
    ui_path = os.path.join(os.path.dirname(__file__), "energyWatcher.ui")
    ui_class, base_class = MaxPlus.LoadUiType(ui_path)
    return ui_class


def updateBeaconPosition():
    global total_watts
    global beacon_list_view
    for item, beacon in beacon_references.iteritems():
        if int(rt.sliderTime) < 1:
            # beacon.movement_history = np.zeros((1, 101))
            beacon.energy_value_history = list()
            total_watts = 0
        else:
            beacon.updateMovementHistory()
        total_watts = total_watts + beacon.totalEnergy()
        item.setText(1, '{:.2f} W'.format(beacon.totalEnergy() * 1.0))
    beacon_list_view.setText(1, '{:.2f} MW'.format(total_watts / 1000.0))
    updateGUIuponSelection()
    progress_bar.setValue(int(rt.sliderTime))


def createWindow(ui_class):
    global treeView
    global tool_layout
    global plot
    global beacon_list_view
    global interval
    global progress_bar
    interval = np.arange(1, 100)
    beacons = []
    gui = MainWindow(ui_descriptor)
    treeView = gui.findChild(QTreeWidget, "treeWidget")
    treeView.setColumnCount(2)
    treeView.setHeaderLabels(['Beacon', 'Energy'])

    tool_layout = gui.findChild(QSplitter, "splitter")
    progress_bar = gui.findChild(QProgressBar, "progressBar")

    root_node = rt.rootNode
    for child in root_node.children:
        if "Beacon" in child.name:
            beacons.append(Beacon(child))

    beacon_list_view = QTreeWidgetItem(treeView, ["BeaconGrid", str(total_watts)])
    for beacon in beacons:
        item = QTreeWidgetItem(beacon_list_view, [beacon.name, '{:.2f} W'.format(beacon.totalEnergy() * 1.0)])
        beacon_references[item] = beacon

    bakeKeys()

    plot = pg.PlotWidget(title="No beacon selected")
    # plot.setMaximumHeight(480)
    # plot.setMaximumWidth(480)
    # plot.setMinimumWidth(320)
    # plot.getPlotItem().setMaximumWidth(470)
    # plot.getPlotItem().setMinimumWidth(310)
    # plot.getPlotItem().setPreferredSize(320,240)
    # plot.setBaseSize(320,240)
    # plot.getPlotItem().resize(320,240)
    tool_layout.insertWidget(0, plot)

    treeView.currentItemChanged.connect(updateGUIuponSelection)

    return gui


def updateGUIuponSelection():
    item = treeView.currentItem()
    frame = int(rt.sliderTime)
    if item.childCount() == 0:
        beacon = beacon_references[item]
        # bakeKeysFor(beacon)
        plot.clear()
        plot.setTitle(title=beacon.name)
        plot.plot(interval, beacon.movement_history[0][1:100], pen=(1, 3))
        plot.plot(np.full(99, frame, dtype=np.int8),
                  np.full(99, beacon.movement_history[0][frame], dtype=np.float16),
                  pen=None, symbol='o')


def bakeKeys():
    # TODO: parallelize this
    for frame in range(0, 101):
        with attime(frame):
            for index, beacon in beacon_references.iteritems():
                value_at_frame = beacon.reference.position.z
                beacon.movement_history[0][frame] = value_at_frame


if __name__ == "__main__":
    ui_descriptor = loadUI()
    eng_window = createWindow(ui_descriptor)
    eng_window.setParent(MaxPlus.GetQMaxWindow())
    MaxPlus.MakeQWidgetDockable(eng_window, 4)
    eng_window.show()
    rt.registerTimeCallback(updateBeaconPosition)
    # instance.close()
