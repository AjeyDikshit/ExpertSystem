# This Python file uses the following encoding: utf-8
import os
from pathlib import Path
import sys
from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import uic
from PyQt5 import QtGui
import pandas as pd
import numpy as np
import pyqtgraph as pg
import random
import time
# import csv
from comtrade import Comtrade
import PPF as ppf

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('Trial_UI_V2.ui', self)

        # Variables -----------------------------------------------------
        self.file_path = None
        self.all_files = {}
        self.shift_values = {}
        self.file_names = []
        self.description = {}  # TODO: Add on activate function to show a short description
        self.color_index = 0
        self.color_list = [(222, 60, 0), (222, 60, 163), (200, 60, 222), (125, 114, 223), (71, 165, 247),
                           (20, 190, 209), (24, 255, 109), (168, 230, 76), (247, 255, 0), (255, 162, 0)] * 2
        self.color_dict = {}
        self.com = Comtrade()

        # Tooltips:
        self.load_tooltips()

        # Signals -----------------------------------------------------
        # Tab-1 --> User input tab
        self.browse_file_location.clicked.connect(self.get_file)
        self.PB_move_to_voltage.clicked.connect(self.move_to_voltage)
        self.PB_move_to_current.clicked.connect(self.move_to_current)
        self.voltage_set_items = set([])
        self.current_set_items = set([])
        self.PB_remove_entry.clicked.connect(self.removeSel)
        self.LW_voltage_set.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.LW_current_set.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

        self.PB_load_file.clicked.connect(self.load_file)

        self.list_of_files.activated.connect(self.show_description)
        # Here lambda function is used as I wanted to send argument to the functions (arguments being, the clicked/checked widget themselves)
        # Plotting signals:
        self.CB_voltage_rms.stateChanged.connect(lambda: self.plot_signal(self.CB_voltage_rms))
        self.CB_current_rms.stateChanged.connect(lambda: self.plot_signal(self.CB_current_rms))

        self.CB_real_power.stateChanged.connect(lambda: self.plot_signal(self.CB_real_power))
        self.CB_reactive_power.stateChanged.connect(lambda: self.plot_signal(self.CB_reactive_power))

        self.CB_voltage_positive.stateChanged.connect(lambda: self.plot_signal(self.CB_voltage_positive))
        self.CB_voltage_negative.stateChanged.connect(lambda: self.plot_signal(self.CB_voltage_negative))
        self.CB_voltage_zero.stateChanged.connect(lambda: self.plot_signal(self.CB_voltage_zero))

        self.CB_current_positive.stateChanged.connect(lambda: self.plot_signal(self.CB_current_positive))
        self.CB_current_negative.stateChanged.connect(lambda: self.plot_signal(self.CB_current_negative))
        self.CB_current_zero.stateChanged.connect(lambda: self.plot_signal(self.CB_current_zero))

        # Default settings
        # self.LE_power_selection.setEnabled(False)

        self.plot_widget1.showGrid(x=True, y=True, alpha=1)
        self.plot_widget2.showGrid(x=True, y=True, alpha=1)
        self.groupBox.setEnabled(False)

    #################################################################################################
    #  Tab-1 -> User input area:
    #################################################################################################
    def get_file(self):
        dlg = QtWidgets.QFileDialog(self)
        # self.file_path = dlg.getOpenFileName(self, 'Choose directory', r'C:\Users\dixit\OneDrive\Desktop\Folder_forGUI\Comtrade Data')[0]
        self.file_path = dlg.getOpenFileName(self, 'Choose directory', r"C:\Users\dixit\OneDrive\Desktop\Folder_forGUI\Comtrade data\A1Q07DP1202311084f.cfg")[0]
        self.LE_file_path.setText(self.file_path)

        self.com.load(self.file_path)
        self.LW_attribute_list.clear()
        self.LW_attribute_list.addItems(self.com.analog_channel_ids)
        self.LW_voltage_set.clear()
        self.LW_current_set.clear()

    def move_to_voltage(self):
        item = self.LW_attribute_list.currentItem().text()
        if item not in self.voltage_set_items:
            self.LW_voltage_set.addItem(item)
            self.voltage_set_items.add(item)
            self.LW_attribute_list.clearSelection()
        # if self.LW_voltage_set.count() > 3:
        #     self.LE_power_selection.setEnabled(True)

    def move_to_current(self):
        item = self.LW_attribute_list.currentItem().text()
        if item not in self.current_set_items:
            self.LW_current_set.addItem(item)
            self.current_set_items.add(item)
            self.LW_attribute_list.clearSelection()
        # if self.LW_current_set.count() > 3:
        #     self.LE_power_selection.setEnabled(True)

    def removeSel(self):
        listItems1 = self.LW_voltage_set.selectedItems()
        listItems2 = self.LW_current_set.selectedItems()
        if not listItems1 and not listItems2:
            return
        if listItems1:
            for item in listItems1:
                self.LW_voltage_set.takeItem(self.LW_voltage_set.row(item))
                self.voltage_set_items.discard(item.text())
                self.LW_voltage_set.clearSelection()
        if listItems2:
            for item in listItems2:
                self.LW_current_set.takeItem(self.LW_current_set.row(item))
                self.current_set_items.discard(item.text())
                self.LW_current_set.clearSelection()

        # if self.LW_current_set.count() <= 3 and self.LW_voltage_set.count() <= 3:
        #     self.LE_power_selection.setEnabled(False)

    def load_file(self):
        df_dict = {}
        number_of_voltage_sets = self.LW_voltage_set.count() // 3
        number_of_current_sets = self.LW_current_set.count() // 3

        filename = self.LE_file_path.text().split('/')[-1]
        print(filename)

        self.description[filename] = self.com.cfg_summary()
        df_dict['Time'] = self.com.time

        count = 0
        for i in range(self.LW_voltage_set.count()):
            if i % 3 == 0:
                count += 1
                df_dict[f'Va{count}'] = self.com.analog[self.com.analog_channel_ids.index(self.LW_voltage_set.item(i).text())]
            if i % 3 == 1:
                df_dict[f'Vb{count}'] = self.com.analog[self.com.analog_channel_ids.index(self.LW_voltage_set.item(i).text())]
            if i % 3 == 2:
                df_dict[f'Vc{count}'] = self.com.analog[self.com.analog_channel_ids.index(self.LW_voltage_set.item(i).text())]

        count = 0
        for i in range(self.LW_current_set.count()):
            if i % 3 == 0:
                count += 1
                df_dict[f'Ia{count}'] = self.com.analog[self.com.analog_channel_ids.index(self.LW_current_set.item(i).text())]
            if i % 3 == 1:
                df_dict[f'Ib{count}'] = self.com.analog[self.com.analog_channel_ids.index(self.LW_current_set.item(i).text())]
            if i % 3 == 2:
                df_dict[f'Ic{count}'] = self.com.analog[self.com.analog_channel_ids.index(self.LW_current_set.item(i).text())]

        df = pd.DataFrame(df_dict)

        # For power calculations:
        power_input = list(eval(self.LE_power_selection.text()))
        try:
            if int(power_input[0]):
                if power_input[0] > number_of_voltage_sets or power_input[1] > number_of_current_sets:
                    QtWidgets.QMessageBox.information(self, "Error", "Please input proper values for power calculation")
                try:
                    va, vb, vc = df[f'Va{power_input[0]}'], df[f'Vb{power_input[0]}'], df[f'Vc{power_input[0]}']
                    ia, ib, ic = df[f'Ia{power_input[1]}'], df[f'Ib{power_input[1]}'], df[f'Ic{power_input[1]}']

                    df['RMS_voltage'] = ppf.instaLL_RMSVoltage(df['Time'], va, vb, vc)  # TODO: Move this line 147, and calculate for all sets of voltages
                    df['RMS_current'] = ppf.insta_RMSCurrent(df['Time'], ia, ib, ic)  # TODO: Move this line 147, and calculate for all sets of currents
                    df["Real power"], df['Reactive power'] = ppf.instant_power(va, vb, vc, ia, ib, ic)

                    va_dft = ppf.window_phasor(np.array(va), np.array(df['Time']), 1, 1)[0]
                    vb_dft = ppf.window_phasor(np.array(vb), np.array(df['Time']), 1, 1)[0]
                    vc_dft = ppf.window_phasor(np.array(vc), np.array(df['Time']), 1, 1)[0]
                    ia_dft = ppf.window_phasor(np.array(ia), np.array(df['Time']), 1, 1)[0]
                    ib_dft = ppf.window_phasor(np.array(ib), np.array(df['Time']), 1, 1)[0]
                    ic_dft = ppf.window_phasor(np.array(ic), np.array(df['Time']), 1, 1)[0]

                    df['Positive sequence V'], df['Negative sequence V'], df['Zero sequence V'] = ppf.sequencetransform(
                        df['Time'], va_dft, vb_dft, vc_dft)
                    df['Positive sequence I'], df['Negative sequence I'], df['Zero sequence I'] = ppf.sequencetransform(
                        df['Time'], ia_dft, ib_dft, ic_dft)

                    self.all_files[filename] = df
                    self.list_of_files.clear()
                    self.list_of_files.addItems([""] + list(self.all_files.keys()))
                    self.shift_values[filename] = [0, 0]
                    self.color_dict[filename] = self.color_list[self.color_index]
                    self.color_index += 1
                    self.file_names = list(self.all_files.keys())

                    self.groupBox.setEnabled(True)

                    QtWidgets.QMessageBox.information(self,
                                                      "Success",
                                                      "File loaded successfully, you can add more files/proceed to plotting")
                except KeyError as err:
                    QtWidgets.QMessageBox.information(self,
                                                      "Error", "Didn't obtain correct number of values, please check your input lists")
        except TypeError as e:
            for _ in range(len(power_input)):
                # if power_input[0] > number_of_voltage_sets or power_input[1] > number_of_current_sets:
                #     QtWidgets.QMessageBox.information(self, "Error", "Please input proper values for power calculation")
                try:
                    va, vb, vc = df[f'Va{power_input[_][0]}'], df[f'Vb{power_input[_][0]}'], df[f'Vc{power_input[_][0]}']
                    ia, ib, ic = df[f'Ia{power_input[_][1]}'], df[f'Ib{power_input[_][1]}'], df[f'Ic{power_input[_][1]}']

                    df['RMS_voltage'] = ppf.instaLL_RMSVoltage(df['Time'], va, vb, vc)
                    df[f'RMS_current {_+1}'] = ppf.insta_RMSCurrent(df['Time'], ia, ib, ic)
                    df[f"Real power {_+1}"], df[f'Reactive power {_+1}'] = ppf.instant_power(va, vb, vc, ia, ib, ic)

                    va_dft = ppf.window_phasor(np.array(va), np.array(df['Time']), 1, 1)[0]
                    vb_dft = ppf.window_phasor(np.array(vb), np.array(df['Time']), 1, 1)[0]
                    vc_dft = ppf.window_phasor(np.array(vc), np.array(df['Time']), 1, 1)[0]
                    ia_dft = ppf.window_phasor(np.array(ia), np.array(df['Time']), 1, 1)[0]
                    ib_dft = ppf.window_phasor(np.array(ib), np.array(df['Time']), 1, 1)[0]
                    ic_dft = ppf.window_phasor(np.array(ic), np.array(df['Time']), 1, 1)[0]

                    df[f'Positive sequence V {_+1}'], df[f'Negative sequence V {_+1}'], df[f'Zero sequence V {_+1}'] = ppf.sequencetransform(
                        df['Time'], va_dft, vb_dft, vc_dft)
                    df[f'Positive sequence I {_+1}'], df[f'Negative sequence I {_+1}'], df[f'Zero sequence I {_+1}'] = ppf.sequencetransform(
                        df['Time'], ia_dft, ib_dft, ic_dft)

                except KeyError as err:
                    QtWidgets.QMessageBox.information(self,
                                                      "Error",
                                                      "Didn't obtain correct number of values, please check your input lists")

            self.all_files[filename] = df
            self.list_of_files.clear()
            self.list_of_files.addItems([""] + list(self.all_files.keys()))
            self.shift_values[filename] = [0, 0]
            self.color_dict[filename] = self.color_list[self.color_index]
            self.color_index += 1
            self.file_names = list(self.all_files.keys())

            self.groupBox.setEnabled(True)

            QtWidgets.QMessageBox.information(self,
                                              "Success",
                                              "File loaded successfully, you can add more files/proceed to plotting")
        print(df.columns)

    # def load_all_files(self):
    #     for file in self.file_names:
    #         self.all_files[file] = self.load_dataframe(file)
    #         self.shift_values[file] = [0, 0]
    #
    #     print(self.all_files.keys())
    #     self.groupBox.setEnabled(True)
    #
    # def load_dataframe(self, file: str) -> pd.DataFrame:
    #     com = Comtrade()
    #     com.load(file)
    #
    #     self.description[file[:-4]] = com.cfg_summary()
    #
    #     df = pd.DataFrame(com.analog, index=com.analog_channel_ids).transpose()
    #     df.insert(0, 'Time', com.time)
    #
    #     if com.channels_count == 123:
    #         va, vb, vc = df.iloc[:, 5], df.iloc[:, 6], df.iloc[:, 7]
    #         ia, ib, ic = df.iloc[:, 1], df.iloc[:, 2], df.iloc[:, 3]
    #
    #     if com.channels_count == 95:
    #         va, vb, vc = df['LINE PT R-Ph'], df['LINE PT Y-Ph'], df['LINE PT B-Ph']
    #         ia, ib, ic = df['LINE CT R-Ph'], df['LINE CT Y-Ph'], df['LINE CT B-Ph']
    #
    #     if com.channels_count == 80 or com.channels_count == 40:
    #         va, vb, vc = df['VA'], df["VB"], df["VC"]
    #         ia, ib, ic = df['IA'], df["IB"], df["IC"]
    #
    #     df['RMS_voltage'] = ppf.instaLL_RMSVoltage(df['Time'], va, vb, vc)
    #     df['RMS_current'] = ppf.insta_RMSCurrent(df['Time'], ia, ib, ic)
    #     df["Real power"], df['Reactive power'] = ppf.instant_power(va, vb, vc, ia, ib, ic)
    #
    #     va_dft = ppf.window_phasor(np.array(va), np.array(df['Time']), 1, 1)[0]
    #     vb_dft = ppf.window_phasor(np.array(vb), np.array(df['Time']), 1, 1)[0]
    #     vc_dft = ppf.window_phasor(np.array(vc), np.array(df['Time']), 1, 1)[0]
    #     ia_dft = ppf.window_phasor(np.array(ia), np.array(df['Time']), 1, 1)[0]
    #     ib_dft = ppf.window_phasor(np.array(ib), np.array(df['Time']), 1, 1)[0]
    #     ic_dft = ppf.window_phasor(np.array(ic), np.array(df['Time']), 1, 1)[0]
    #
    #     df['Positive sequence V'], df['Negative sequence V'], df['Zero sequence V'] = ppf.sequencetransform(
    #         df['Time'], va_dft, vb_dft, vc_dft)
    #     df['Positive sequence I'], df['Negative sequence I'], df['Zero sequence I'] = ppf.sequencetransform(
    #         df['Time'], ia_dft, ib_dft, ic_dft)
    #
    #     print("done")
    #     return df

#################################################################################################
    #  Tab-2 -> Plotting area?:
#################################################################################################
    
    def show_description(self):
        self.short_description.setText(self.description[self.list_of_files.currentText()])

    def plot_signal(self, button):
        if button.isChecked():  # Unchecking all checkboxes, and checking the checked checkbox
            self.set_checkboxes_unchecked()
            button.setChecked(True)

        # Calling functino depending on the checkbox selected
        if self.CB_voltage_rms.isChecked():
            self.plot_rms_voltage()
        elif self.CB_current_rms.isChecked():
            self.plot_rms_current()
        elif self.CB_real_power.isChecked():
            self.plot_real_power()
        elif self.CB_reactive_power.isChecked():
            self.plot_reactive_power()
        elif self.CB_voltage_positive.isChecked():
            self.plot_positive_voltage()
        elif self.CB_voltage_negative.isChecked():
            self.plot_negative_voltage()
        elif self.CB_voltage_zero.isChecked():
            self.plot_zero_voltage()
        elif self.CB_current_positive.isChecked():
            self.plot_positive_current()
        elif self.CB_current_negative.isChecked():
            self.plot_negative_current()
        elif self.CB_current_zero.isChecked():
            self.plot_zero_current()

    def set_checkboxes_unchecked(self):
        for edit in self.groupBox.parentWidget().findChildren(QtWidgets.QCheckBox):
            edit.setChecked(False)

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

    def plot_positive_voltage(self):
        self.plot_widget1.clear()
        self.plot_widget1.addLegend()
        for file in self.file_names:
            name = file[:-4]
            pen = pg.mkPen(color=self.color_dict[file], width=1.5)
            self.plot_widget1.plot(self.all_files[file]["Time"], np.abs(self.all_files[file]['Positive sequence V']), pen=pen, name=name)

    def plot_negative_voltage(self):
        self.plot_widget1.clear()
        self.plot_widget1.addLegend()
        for file in self.file_names:
            name = file[:-4]
            pen = pg.mkPen(color=self.color_dict[file], width=1.5)
            self.plot_widget1.plot(self.all_files[file]["Time"], np.abs(self.all_files[file]['Negative sequence V']), pen=pen, name=name)

    def plot_zero_voltage(self):
        self.plot_widget1.clear()
        self.plot_widget1.addLegend()
        for file in self.file_names:
            name = file[:-4]
            pen = pg.mkPen(color=self.color_dict[file], width=1.5)
            self.plot_widget1.plot(self.all_files[file]["Time"], np.abs(self.all_files[file]['Zero sequence V']), pen=pen, name=name)

    def plot_positive_current(self):
        self.plot_widget1.clear()
        self.plot_widget1.addLegend()
        for file in self.file_names:
            name = file[:-4]
            pen = pg.mkPen(color=self.color_dict[file], width=1.5)
            self.plot_widget1.plot(self.all_files[file]["Time"], np.abs(self.all_files[file]['Positive sequence I']), pen=pen, name=name)

    def plot_negative_current(self):
        self.plot_widget1.clear()
        self.plot_widget1.addLegend()
        for file in self.file_names:
            name = file[:-4]
            pen = pg.mkPen(color=self.color_dict[file], width=1.5)
            self.plot_widget1.plot(self.all_files[file]["Time"], np.abs(self.all_files[file]['Negative sequence I']), pen=pen, name=name)

    def plot_zero_current(self):
        self.plot_widget1.clear()
        self.plot_widget1.addLegend()
        for file in self.file_names:
            name = file[:-4]
            pen = pg.mkPen(color=self.color_dict[file], width=1.5)
            self.plot_widget1.plot(self.all_files[file]["Time"], np.abs(self.all_files[file]['Zero sequence I']), pen=pen, name=name)

    def load_tooltips(self):
        self.TT_remove_selection.setToolTip('To de-select item from list, click on list on a blank area')
        self.label_2.setToolTip('The voltages will be grouped in groups of 3, so enter variables appropriately')
        self.TT_voltage_set.setToolTip(
            'The voltages will be grouped in groups of 3, so enter variables appropriately\nThe order will be:\nA-phase,\nB-phase,\nC-phase')
        self.label_3.setToolTip('The currents will be grouped in groups of 3, so enter variables appropriately')
        self.TT_current_set.setToolTip(
            'The currents will be grouped in groups of 3, so enter variables appropriately\nThe order will be:\nA-phase,\nB-phase,\nC-phase')
        self.TT_set_selection.setToolTip('By default, the 1st set for each will be chosen')


class DeselectableTreeView(QtWidgets.QListWidget):
    def __init__(self, parent):
        super().__init__(parent)

    def mousePressEvent(self, event):
        super(DeselectableTreeView, self).mousePressEvent(event)
        if not self.indexAt(event.pos()).isValid():
            self.clearSelection()

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
