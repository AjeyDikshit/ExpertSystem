# This Python file uses the following encoding: utf-8
import os
import time
from pathlib import Path
import sys

from PyQt5 import QtWidgets, QtCore
from PyQt5 import uic
import pandas as pd
import numpy as np
import pyqtgraph as pg
import pickle
from comtrade import Comtrade, ComtradeError

import PPF as ppf
import segmentation_functions as segment_function


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('Dynamic_plotting.ui', self)

        # Variables -----------------------------------------------------
        self.file_path = None  # File path of file user is going to load

        self.all_files1 = {}  # TODO: rename to better variable

        self.file_names = []
        self.color_index = 0
        self.color_list = [(222, 60, 0), (222, 60, 163), (200, 60, 222), (125, 114, 223), (71, 165, 247),
                           (20, 190, 209), (24, 255, 109), (168, 230, 76), (247, 255, 0), (255, 162, 0)] * 2

        self.count = 1


        self.scrollArea.setVisible(False)

        self.number_of_files = 0

        self.current_set_items = set([])

        self.PB_load_file.clicked.connect(self.load_file)

        self.CB_instantaneous_tab.activated.connect(self.plot_instantaneous)

        self.PB_add_plots.clicked.connect(self.changeSize)

        self.PB_click.clicked.connect(self.dosomething)

    def load_file(self):
        dlg = QtWidgets.QFileDialog(self)
        self.file_path = dlg.getOpenFileName(self, 'Choose directory',
                                             r"C:\Users\dixit\OneDrive\Desktop\Folder_forGUI\Comtrade data",
                                             filter="Pickle (*.pickle)")[0]

        self.LE_file_path.setText(self.file_path)
        filename = self.LE_file_path.text().split('/')[-1][:-7]

        try:
            with open(f"{self.file_path}", "rb") as infile:
                self.all_files1[filename] = pickle.load(infile)

            self.file_names = list(self.all_files1.keys())

            self.CB_instantaneous_tab.clear()
            self.CB_instantaneous_tab.addItems([""] + self.file_names)

            self.number_of_files += 1

            self.all_files1[filename]['color_dict'] = self.color_list[self.color_index]
            self.color_index += 1

            QtWidgets.QMessageBox.information(self,
                                              "Success",
                                              "File loaded successfully, you can add more files/proceed to plotting")
        except FileNotFoundError as err:
            QtWidgets.QMessageBox.information(self,
                                              "Fail",
                                              "The file doesn't exist, please compute the values before trying to load a file")

    """
    1. Make scroll area, keep it hidden initially
    2. When "add" button clicked, show the scroll area with first 2 plots corresponding to selected file.
    3. Store the added files in a set to avoid duplicate entries, and somehow store the plots that are connected to that file.
    3.5. Create a new class which defines the min and max size of the plot widgets, so that they don't have to set everytime.
    4. Create plot widgets, and add stack them horizontally, and then vertical together with the scroll area.
    5. 
    """
    def dosomething(self):
        self.count1 += 1

        # for i in range(self.count1):
        file = self.CB_instantaneous_tab.currentText()

        self.plot1 = pg.PlotWidget()
        self.plot1.addLegend(offset=(350, 8))
        self.plot1.setMinimumSize(480, 250)
        self.plot1.setMaximumSize(550, 280)

        colors = ['r', 'y', 'b'] * 3
        color_count = 0

        for column in [item for item in self.all_files1[file]['data'].keys() if
                       item.startswith("V")]:
            pen = pg.mkPen(color=colors[color_count], width=1.5)
            self.plot1.plot(
                self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column],
                pen=pen, name=file + f"_{column}")
            color_count += 1

        self.plot2 = pg.PlotWidget()
        self.plot2.addLegend(offset=(350, 8))
        self.plot2.setMinimumSize(480, 250)
        self.plot2.setMaximumSize(550, 280)


        color_count = 0
        for column in [item for item in self.all_files1[file]['data'].keys() if
                       item.startswith("I")]:
            pen = pg.mkPen(color=colors[color_count], width=1.5)
            self.plot2.plot(
                self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column],
                pen=pen, name=file + f"_{column}")
            color_count += 1

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.plot1)
        layout.addWidget(self.plot2)

        self.layout2.addLayout(layout)

        self.widget = QtWidgets.QWidget()
        self.widget.setLayout(self.layout2)

        self.scroll1.setWidget(self.widget)



    def changeSize(self):
        print("Plot added", self.count)
        self.scrollArea.setVisible(True)
        plots = self.scrollArea.findChildren(pg.PlotWidget)
        self.scrollArea.setGeometry(50, 110, 1179, 500 * self.count)
        for index, plot in enumerate(plots):
            print(index, plot.plotItem)
        self.count += 1

    def plot_instantaneous(self):
        self.PW_instant_voltage.clear()
        self.PW_instant_current.clear()


        if file == "":
            self.PW_instant_voltage.clear()
            self.PW_instant_current.clear()
            return

        self.PW_instant_voltage.addLegend(offset=(350, 8))
        self.PW_instant_current.addLegend(offset=(350, 8))

        colors = ['r', 'y', 'b'] * 3
        color_count = 0

        for column in [item for item in self.all_files1[file]['data'].keys() if
                       item.startswith("V")]:
            pen = pg.mkPen(color=colors[color_count], width=1.5)
            self.PW_instant_voltage.plot(
                self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column],
                pen=pen, name=file + f"_{column}")
            color_count += 1

        color_count = 0
        for column in [item for item in self.all_files1[file]['data'].keys() if
                       item.startswith("I")]:
            pen = pg.mkPen(color=colors[color_count], width=1.5)
            self.PW_instant_current.plot(
                self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column],
                pen=pen, name=file + f"_{column}")
            color_count += 1

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
