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
from comtrade import Comtrade
import PPF as ppf

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('form_scribble.ui', self)

        # Variables -----------------------------------------------------
        self.dir_path = None
        self.all_files = {}
        self.shift_values = {}
        self.file_names = []
        self.description = {}  # TODO: Add on activate function to show a short description
        self.color_list = [(222, 60, 0), (222, 60, 163), (200, 60, 222), (125, 114, 223), (71, 165, 247),
                           (20, 190, 209), (24, 255, 109), (168, 230, 76), (247, 255, 0), (255, 162, 0)] * 2
        self.color_dict = {}

        # Signals -----------------------------------------------------
        self.browse_folder_location.clicked.connect(self.get_folder)
        self.list_of_files.activated.connect(self.show_description)
        self.plot_button.clicked.connect(self.plot_signal)

        self.plotting_general_options.clicked.connect(lambda: self.toggle_options(self.plotting_general_options))
        self.plotting_power_options.clicked.connect(lambda: self.toggle_options(self.plotting_power_options))
        self.plotting_pn0_options.clicked.connect(lambda: self.toggle_options(self.plotting_pn0_options))

        # Default setting
        self.plot_widget1.showGrid(x=True, y=True, alpha=1)
        self.plot_widget2.showGrid(x=True, y=True, alpha=1)
        self.groupBox.setEnabled(False)

    def get_folder(self):
        dlg = QtWidgets.QFileDialog(self)
        self.dir_path = dlg.getExistingDirectory(self, 'Choose directory', r'C:\Users\dixit\OneDrive\Desktop\Folder_forGUI\Comtrade Data')
        self.folder_location.setText(self.dir_path)
        os.chdir(self.dir_path)

        files = os.listdir(self.dir_path)
        count = 0
        for index, file in enumerate(files):
            if len(file.split('.')) > 1:
                if file.upper().endswith('.CFG'):
                    self.file_names.append(file)
                    self.color_dict[file] = self.color_list[count]
                    count += 1

        print(self.file_names)
        print(self.color_dict)
        self.list_of_files.addItems([''] + [x[:-4] for x in self.file_names])
        self.load_all_files()
        # self.plot_derivatives()

    def load_all_files(self):
        for file in self.file_names:
            self.all_files[file] = self.load_dataframe(file)
            self.shift_values[file] = [0, 0]

        self.plot_widget1.addLegend()
        for file in self.file_names:
            name = file[:-4]
            pen = pg.mkPen(color=self.color_dict[file], width=1.5)
            self.plot1_signals(self.all_files[file])

        self.groupBox.setEnabled(True)

    def plot_derivatives(self):
        self.plot_widget2.addLegend()
        for file in self.file_names:
            name = file[:-4]
            pen = pg.mkPen(color=self.color_dict[file], width=1.5)
            derivative = ppf.derivative(np.array(self.all_files[file]['Time']), np.array(self.all_files[file]['calculated_voltage']))
            self.plot_widget2.plot(self.all_files[file]['Time'], abs(derivative/max(derivative)), pen=pen, name=name)

    def load_dataframe(self, file: str) -> pd.DataFrame:
        com = Comtrade()
        com.load(file)

        self.description[file[:-4]] = com.cfg_summary()

        df = pd.DataFrame(com.analog, index=com.analog_channel_ids).transpose()
        df.insert(0, 'Time', com.time)
        if com.channels_count == 123:
            print("L-90 relay")
            df['RMS_voltage'] = ppf.instaLL_RMSVoltage(df['Time'], df.iloc[:, 5], df.iloc[:, 6], df.iloc[:, 7])
            df['RMS_current'] = ppf.insta_RMSCurrent(df['Time'], df.iloc[:, 1], df.iloc[:, 2], df.iloc[:, 3])
            df["Real power"], df['Reactive power'] = ppf.instant_power(df.iloc[:, 5], df.iloc[:, 6], df.iloc[:, 7],
                                                                       df.iloc[:, 1], df.iloc[:, 2], df.iloc[:, 3])

        if com.channels_count == 95:
            print("ABB relay")
            df['RMS_voltage'] = ppf.instaLL_RMSVoltage(df['Time'], df['LINE PT R-Ph'], df['LINE PT Y-Ph'], df['LINE PT B-Ph'])
            df['RMS_current'] = ppf.insta_RMSCurrent(df["Time"], df['LINE CT R-Ph'], df['LINE CT Y-Ph'], df['LINE CT B-Ph'])
            df['Real power'], df['Reactive power'] = ppf.instant_power(df['LINE PT R-Ph'], df['LINE PT Y-Ph'], df['LINE PT B-Ph'],
                                                                       df['LINE CT R-Ph'], df['LINE CT Y-Ph'], df['LINE CT B-Ph'])

        if com.channels_count == 80:
            print("Micom relay")
            df['RMS_voltage'] = ppf.instaLL_RMSVoltage(df['Time'], df['VA'], df['VB'], df['VC'])
            df['RMS_current'] = ppf.insta_RMSCurrent(df["Time"], df['IA'], df['IB'], df['IC'])
            df['Real power'], df['Reactive power'] = ppf.instant_power(df['VA'], df['VB'], df['VC'],
                                                                       df['IA'], df['IB'], df['IC'])

        if com.channels_count == 40:
            print("Unknown relay")
            df['RMS_voltage'] = ppf.instaLL_RMSVoltage(df['Time'], df['VA'], df['VB'], df['VC'])
            df['RMS_current'] = ppf.insta_RMSCurrent(df["Time"], df['IA'], df['IB'], df['IC'])
            df['Real power'], df['Reactive power'] = ppf.instant_power(df['VA'], df['VB'], df['VC'],
                                                                       df['IA'], df['IB'], df['IC'])

        print("done")
        return df

    def plot1_signals(self, df):
        self.plot_widget1.addLegend()

        if len(df.columns) == 42:
            self.plot_widget1.plot(df['Time'], df.iloc[:, 5], label='Va')
            self.plot_widget1.plot(df['Time'], df.iloc[:, 6], label='Vb')
            self.plot_widget1.plot(df['Time'], df.iloc[:, 7], label='Vc')
            self.plot_widget1.plot(df['Time'], df['RMS'], label='RMS')

        if len(df.columns) == 19:
            self.plot_widget1.plot(df['Time'], df['LINE PT R-Ph'], label='Va')
            self.plot_widget1.plot(df['Time'], df['LINE PT Y-Ph'], label='Vb')
            self.plot_widget1.plot(df['Time'], df['LINE PT B-Ph'], label='Vc')
            self.plot_widget1.plot(df['Time'], df['RMS'], label="RMS")

        if len(df.columns) == 18:
            self.plot_widget1.plot(df['Time'], df['VA'], label='Va')
            self.plot_widget1.plot(df['Time'], df['VB'], label='Vb')
            self.plot_widget1.plot(df['Time'], df['VC'], label='Vc')
            self.plot_widget1.plot(df['Time'], df['RMS'], label="RMS")

        if len(df.columns) == 10:
            self.plot_widget1.plot(df['Time'], df['VA'], label='Va')
            self.plot_widget1.plot(df['Time'], df['VB'], label='Vb')
            self.plot_widget1.plot(df['Time'], df['VC'], label='Vc')
            self.plot_widget1.plot(df['Time'], df['RMS'], label="RMS")

    def show_description(self):
        self.short_description.setText(self.description[self.list_of_files.currentText()])

    def plot_signal(self):
        if self.plotting_general_options.isChecked():
            if self.CB_voltage_rms.isChecked():
                self.plot_rms_voltage()
            elif self.CB_current_rms.isChecked():
                self.plot_rms_current()

        if self.plotting_power_options.isChecked():
            if self.CB_real_power.isChecked():
                self.plot_real_power()
            elif self.CB_reactive_power.isChecked():
                self.plot_reactive_power()

        if self.plotting_pn0_options.isChecked():
            if self.CB_voltage_positive.isChecked():
                self.short_description.setText("Positive voltage")
            elif self.CB_voltage_negative.isChecked():
                self.short_description.setText("Negative voltage")
            elif self.CB_voltage_zero.isChecked():
                self.short_description.setText("Zero voltage")
            elif self.CB_current_positive.isChecked():
                self.short_description.setText("Positive current")
            elif self.CB_current_negative.isChecked():
                self.short_description.setText("Negative current")
            elif self.CB_current_zero.isChecked():
                self.short_description.setText("Zero current")

    def set_checkboxes_unchecked(self):
        for edit in self.groupBox.parentWidget().findChildren(QtWidgets.QCheckBox):
            edit.setChecked(False)

    def toggle_options(self, group_box):
        if group_box.title() == 'General:':
            if self.plotting_general_options.isChecked():
                self.set_checkboxes_unchecked()
                self.plotting_power_options.setEnabled(False)
                self.plotting_pn0_options.setEnabled(False)
            else:
                self.plotting_power_options.setEnabled(True)
                self.plotting_pn0_options.setEnabled(True)

        elif group_box.title() == 'Power:':
            if self.plotting_power_options.isChecked():
                self.set_checkboxes_unchecked()
                self.plotting_general_options.setEnabled(False)
                self.plotting_pn0_options.setEnabled(False)
            else:
                self.plotting_general_options.setEnabled(True)
                self.plotting_pn0_options.setEnabled(True)

        elif group_box.title() == 'Positive, Negative, Zero sequence:':
            if self.plotting_pn0_options.isChecked():
                self.set_checkboxes_unchecked()
                self.plotting_power_options.setEnabled(False)
                self.plotting_general_options.setEnabled(False)
            else:
                self.plotting_power_options.setEnabled(True)
                self.plotting_general_options.setEnabled(True)

    # Plotting functions:
    def plot_real_power(self):
        self.plot_widget1.clear()
        self.plot_widget1.addLegend()
        for file in self.file_names:
            name = file[:-4]
            pen = pg.mkPen(color=self.color_dict[file], width=1.5)
            self.plot_widget1.plot(self.all_files[file]["Time"], self.all_files[file]['Real power'], pen=pen, name=name)

    def plot_reactive_power(self):
        self.plot_widget1.clear()
        self.plot_widget1.addLegend()
        for file in self.file_names:
            name = file[:-4]
            pen = pg.mkPen(color=self.color_dict[file], width=1.5)
            self.plot_widget1.plot(self.all_files[file]["Time"], self.all_files[file]['Reactive power'], pen=pen, name=name)

    def plot_rms_voltage(self):
        self.plot_widget1.clear()
        self.plot_widget1.addLegend()
        for file in self.file_names:
            name = file[:-4]
            pen = pg.mkPen(color=self.color_dict[file], width=1.5)
            self.plot_widget1.plot(self.all_files[file]["Time"], self.all_files[file]['RMS_voltage'], pen=pen, name=name)

    def plot_rms_current(self):
        self.plot_widget1.clear()
        self.plot_widget1.addLegend()
        for file in self.file_names:
            name = file[:-4]
            pen = pg.mkPen(color=self.color_dict[file], width=1.5)
            self.plot_widget1.plot(self.all_files[file]["Time"], self.all_files[file]['RMS_current'], pen=pen, name=name)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec_())
