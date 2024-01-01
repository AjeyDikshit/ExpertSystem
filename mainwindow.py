# This Python file uses the following encoding: utf-8
import os
from pathlib import Path
import sys
from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import uic
import pandas as pd
import numpy as np
import pyqtgraph as pg
import random
import time
import csv
import PPF as ppf

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('form.ui', self)

        # Variables -----------------------------------------------------
        self.dir_path = None
        self.all_files = {}
        self.shift_values = {}
        self.file_names = []
        self.color_list = [(222, 60, 0), (222, 60, 163), (200, 60, 222), (125, 114, 223), (71, 165, 247),
                           (20, 190, 209), (24, 255, 109), (168, 230, 76), (247, 255, 0), (255, 162, 0)] * 2
        self.color_dict = {}

        # Signals -----------------------------------------------------
        self.browse_folder_location.clicked.connect(self.get_folder)

        # Default setting
        self.plot_widget1.showGrid(x=True, y=True, alpha=1)
        self.plot_widget2.showGrid(x=True, y=True, alpha=1)

    def get_folder(self):
        dlg = QtWidgets.QFileDialog(self)
        self.dir_path = dlg.getExistingDirectory(self, 'Choose directory', r'C:\Users\dixit\OneDrive\Desktop\Folder_forGUI\Mumbai Data\Output')
        self.folder_location.setText(self.dir_path)
        os.chdir(self.dir_path)

        files = os.listdir(self.dir_path)
        count = 0
        for index, file in enumerate(files):
            if len(file.split('.')) > 1:
                if file.upper().endswith('_CALCULATED.CSV'):
                    self.file_names.append(file)
                    self.color_dict[file] = self.color_list[count]
                    count += 1

        # print(self.file_names)
        # print(self.color_dict)
        self.list_of_files.addItems([''] + [x[:-15] for x in self.file_names])
        self.plot_all_files()
        self.plot_derivatives()

    def plot_all_files(self):
        for file in self.file_names:
            self.all_files[file] = pd.read_csv(file)
            self.shift_values[file] = [0, 0]

        self.plot_widget1.addLegend()
        for file in self.file_names:
            name = file[:-15]
            pen = pg.mkPen(color=self.color_dict[file], width=1.5)
            self.plot_widget1.plot(self.all_files[file]['Time'], self.all_files[file]['calculated_voltage'], pen=pen, name=name)

    def plot_derivatives(self):
        self.plot_widget2.addLegend()
        for file in self.file_names:
            name = file[:-15]
            pen = pg.mkPen(color=self.color_dict[file], width=1.5)
            derivative = ppf.derivative(np.array(self.all_files[file]['Time']), np.array(self.all_files[file]['calculated_voltage']))
            self.plot_widget2.plot(self.all_files[file]['Time'], abs(derivative/max(derivative)), pen=pen, name=name)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec_())
