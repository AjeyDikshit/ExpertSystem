# This Python file uses the following encoding: utf-8
import os
import time
from pathlib import Path
import sys

from PyQt5 import QtWidgets
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
        uic.loadUi('Trial_UI_V2.ui', self)

        self.set_checkboxes_unchecked()
        # Variables -----------------------------------------------------
        self.file_path = None  # File path of file user is going to load

        self.all_files1 = {}  # TODO: rename to better variable

        self.file_names = []
        self.color_index = 0
        self.color_list = [(222, 60, 0), (222, 60, 163), (200, 60, 222), (125, 114, 223), (71, 165, 247),
                           (20, 190, 209), (24, 255, 109), (168, 230, 76), (247, 255, 0), (255, 162, 0)] * 2

        self.number_of_files = 0
        self.com = Comtrade()  # Initializing at start so that it can be reused for all files.

        # Collapse widget
        self.hidden = False
        self.b = None
        self.label_option.setVisible(False)

        # Segmentation
        self.q, self.z1, self.threshold = None, None, None
        self.CB_segment_voltage.stateChanged.connect(lambda: self._plot_segmentation("RMS_voltage", self.CB_segment_voltage))
        self.CB_segment_current.stateChanged.connect(lambda: self._plot_segmentation("RMS_current", self.CB_segment_current))
        self.CB_segment_frequency.stateChanged.connect(lambda: self._plot_segmentation("Frequency F_avg", self.CB_segment_frequency))

        # Tooltips:
        self.load_tooltips()

        # Signals -----------------------------------------------------
        # Tab-1 --> User input tab
        self.voltage_set_items = set([])
        self.current_set_items = set([])

        self.browse_file_location.clicked.connect(self.get_file)
        self.PB_load_file.clicked.connect(self.load_file)
        self.PB_move_to_voltage.clicked.connect(self.move_to_voltage)
        self.PB_move_to_current.clicked.connect(self.move_to_current)
        self.PB_remove_entry.clicked.connect(self.removeSel)
        self.PB_compute_values.clicked.connect(self.compute_values)

        self.LW_voltage_set.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.LW_current_set.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

        # Plotting signals:
        self.CB_voltage_rms.stateChanged.connect(self.plot_signal)
        self.CB_current_rms.stateChanged.connect(self.plot_signal)
        self.CB_frequency.stateChanged.connect(self.plot_signal)

        self.CB_real_power.stateChanged.connect(self.plot_signal)
        self.CB_reactive_power.stateChanged.connect(self.plot_signal)

        self.CB_voltage_positive.stateChanged.connect(self.plot_signal)
        self.CB_voltage_negative.stateChanged.connect(self.plot_signal)
        self.CB_voltage_zero.stateChanged.connect(self.plot_signal)

        self.CB_current_positive.stateChanged.connect(self.plot_signal)
        self.CB_current_negative.stateChanged.connect(self.plot_signal)
        self.CB_current_zero.stateChanged.connect(self.plot_signal)

        self.PB_move_left.clicked.connect(self.move_left)
        self.PB_move_right.clicked.connect(self.move_right)
        self.PB_move_up.clicked.connect(self.move_up)
        self.PB_move_down.clicked.connect(self.move_down)

        self.list_of_files.activated.connect(self.load_signals)

        self.PB_hide_gb1.clicked.connect(self.hide_gb1)

        self.PB_save_state.clicked.connect(self.save_state)

        # Default settings
        self.LE_power_selection.setEnabled(False)
        self.plot_widget1.showGrid(x=True, y=True, alpha=1)
        self.plot_widget2.showGrid(x=True, y=True, alpha=1)
        self.plot_widget3.showGrid(x=True, y=True, alpha=1)
        self.plot_widget4.showGrid(x=True, y=True, alpha=1)
        self.plot_widget5.showGrid(x=True, y=True, alpha=1)
        self.plot_widget6.showGrid(x=True, y=True, alpha=1)
        self.plot_widget7.showGrid(x=True, y=True, alpha=1)
        self.plot_widget8.showGrid(x=True, y=True, alpha=1)
        self.groupBox.setEnabled(False)

    #################################################################################################
    #  Tab-1 -> User input area:
    #################################################################################################
    def get_file(self):
        dlg = QtWidgets.QFileDialog(self)
        self.file_path = dlg.getOpenFileName(self, 'Choose directory',
                                             r"C:\Users\dixit\OneDrive\Desktop\Folder_forGUI\Comtrade data\A1Q07DP1202311084f.cfg",
                                             filter="Config files (*.cfg *.CFG)")[0]
        self.LE_file_path.setText(self.file_path)

        filename = self.LE_file_path.text().split('/')[-1][:-4]
        self.voltage_set_items = set([])
        self.current_set_items = set([])

        try:
            self.com.load(self.file_path)
            self.LW_attribute_list.clear()
            self.LW_attribute_list.addItems(self.com.analog_channel_ids)
            self.LW_voltage_set.clear()
            self.LW_current_set.clear()
        except ComtradeError as err:
            QtWidgets.QMessageBox.information(self,
                                              "Fail",
                                              "File browse failed, please check the filepath")

    def load_file(self):
        dlg = QtWidgets.QFileDialog(self)
        self.file_path = dlg.getOpenFileName(self, 'Choose directory',
                                             r"C:\Users\dixit\OneDrive\Desktop\Folder_forGUI\Comtrade data",
                                             filter="Pickle (*.pickle)")[0]

        self.LE_file_path.setText(self.file_path)
        filename = self.LE_file_path.text().split('/')[-1]

        self.LW_voltage_set.clear()
        self.LW_current_set.clear()
        self.LW_attribute_list.clear()

        try:
            with open(f"{self.file_path}", "rb") as infile:
                self.all_files1[filename] = pickle.load(infile)

            self.file_names = list(self.all_files1.keys())
            self.list_of_files.clear()
            self.list_of_files.addItems([""] + self.file_names)
            self.groupBox.setEnabled(True)

            self.number_of_files += 1
            self.label_list_of_files.setText(
                self.label_list_of_files.text() + f"\n\n{self.number_of_files}. {filename[:-7]}")

            self.all_files1[filename]['color_dict'] = self.color_list[self.color_index]
            self.color_index += 1

            QtWidgets.QMessageBox.information(self,
                                              "Success",
                                              "File loaded successfully, you can add more files/proceed to plotting")
        except FileNotFoundError as err:
            QtWidgets.QMessageBox.information(self,
                                              "Fail",
                                              "The file doesn't exist, please compute the values before trying to load a file")

    def move_to_voltage(self):
        item = self.LW_attribute_list.currentItem().text()
        if item not in self.voltage_set_items:
            self.LW_voltage_set.addItem(item)
            self.voltage_set_items.add(item)
            self.LW_attribute_list.clearSelection()
        if self.LW_voltage_set.count() > 3:
            self.LE_power_selection.setEnabled(True)

    def move_to_current(self):
        item = self.LW_attribute_list.currentItem().text()
        if item not in self.current_set_items:
            self.LW_current_set.addItem(item)
            self.current_set_items.add(item)
            self.LW_attribute_list.clearSelection()
        if self.LW_current_set.count() > 3:
            self.LE_power_selection.setEnabled(True)

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

        if self.LW_current_set.count() <= 3 and self.LW_voltage_set.count() <= 3:
            self.LE_power_selection.setEnabled(False)

    def compute_values(self):
        df_dict = {}
        number_of_voltage_sets = self.LW_voltage_set.count() // 3
        number_of_current_sets = self.LW_current_set.count() // 3

        filename = self.LE_file_path.text().split('/')[-1][:-4]
        print(filename)

        df_dict['Time'] = self.com.time

        count = 0
        for i in range(self.LW_voltage_set.count()):
            if i % 3 == 0:
                count += 1
                df_dict[f'Va{count}'] = self.com.analog[
                    self.com.analog_channel_ids.index(self.LW_voltage_set.item(i).text())]
            if i % 3 == 1:
                df_dict[f'Vb{count}'] = self.com.analog[
                    self.com.analog_channel_ids.index(self.LW_voltage_set.item(i).text())]
            if i % 3 == 2:
                df_dict[f'Vc{count}'] = self.com.analog[
                    self.com.analog_channel_ids.index(self.LW_voltage_set.item(i).text())]

        for i in range(count):
            df_dict[f'RMS_voltage {i + 1}'] = ppf.instaLL_RMSVoltage(df_dict['Time'], df_dict[f'Va{i + 1}'],
                                                                     df_dict[f'Vb{i + 1}'], df_dict[f'Vc{i + 1}'])

        count = 0
        for i in range(self.LW_current_set.count()):
            if i % 3 == 0:
                count += 1
                df_dict[f'Ia{count}'] = self.com.analog[
                    self.com.analog_channel_ids.index(self.LW_current_set.item(i).text())]
            if i % 3 == 1:
                df_dict[f'Ib{count}'] = self.com.analog[
                    self.com.analog_channel_ids.index(self.LW_current_set.item(i).text())]
            if i % 3 == 2:
                df_dict[f'Ic{count}'] = self.com.analog[
                    self.com.analog_channel_ids.index(self.LW_current_set.item(i).text())]

        for i in range(count):
            df_dict[f'RMS_current {i + 1}'] = ppf.instaLL_RMSVoltage(df_dict['Time'], df_dict[f'Ia{i + 1}'],
                                                                     df_dict[f'Ib{i + 1}'], df_dict[f'Ic{i + 1}'])

        df = pd.DataFrame(df_dict)

        # For derived quantities calculations:
        power_input = list(eval(self.LE_power_selection.text()))
        if type(power_input[0]) == int:
            if power_input[0] > number_of_voltage_sets or power_input[1] > number_of_current_sets:
                QtWidgets.QMessageBox.information(self, "Error", "Please input proper values for power calculation")
            try:
                va, vb, vc = df[f'Va{power_input[0]}'], df[f'Vb{power_input[0]}'], df[f'Vc{power_input[0]}']
                ia, ib, ic = df[f'Ia{power_input[1]}'], df[f'Ib{power_input[1]}'], df[f'Ic{power_input[1]}']

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

                # TODO: change "freq4mdftPhasor" function and change the nan values of
                fa = ppf.freq4mdftPhasor(va_dft, np.array(df['Time']), 1)[0]
                fb = ppf.freq4mdftPhasor(vb_dft, np.array(df['Time']), 1)[0]
                fc = ppf.freq4mdftPhasor(vc_dft, np.array(df['Time']), 1)[0]

                fa[:np.argwhere(np.isnan(fa))[-1][0] + 1] = fa[np.argwhere(np.isnan(fa))[-1][0] + 1]
                fb[:np.argwhere(np.isnan(fb))[-1][0] + 1] = fb[np.argwhere(np.isnan(fb))[-1][0] + 1]
                fc[:np.argwhere(np.isnan(fc))[-1][0] + 1] = fc[np.argwhere(np.isnan(fc))[-1][0] + 1]

                f = (fa + fb + fc) / 3

                df[f'Frequency Fa'] = np.real(fa)
                df[f'Frequency Fb'] = np.real(fb)
                df[f'Frequency Fc'] = np.real(fc)
                df[f'Frequency F_avg'] = np.real(f)

            except KeyError as err:
                QtWidgets.QMessageBox.information(self,
                                                  "Error",
                                                  "Didn't obtain correct number of values, please check your input lists")
        elif type(power_input[0]) == list:
            for _ in range(len(power_input)):
                try:
                    va, vb, vc = df[f'Va{power_input[_][0]}'], df[f'Vb{power_input[_][0]}'], df[
                        f'Vc{power_input[_][0]}']
                    ia, ib, ic = df[f'Ia{power_input[_][1]}'], df[f'Ib{power_input[_][1]}'], df[
                        f'Ic{power_input[_][1]}']

                    df[f"Real power {_ + 1}"], df[f'Reactive power {_ + 1}'] = ppf.instant_power(va, vb, vc, ia, ib, ic)

                    va_dft = ppf.window_phasor(np.array(va), np.array(df['Time']), 1, 1)[0]
                    vb_dft = ppf.window_phasor(np.array(vb), np.array(df['Time']), 1, 1)[0]
                    vc_dft = ppf.window_phasor(np.array(vc), np.array(df['Time']), 1, 1)[0]
                    ia_dft = ppf.window_phasor(np.array(ia), np.array(df['Time']), 1, 1)[0]
                    ib_dft = ppf.window_phasor(np.array(ib), np.array(df['Time']), 1, 1)[0]
                    ic_dft = ppf.window_phasor(np.array(ic), np.array(df['Time']), 1, 1)[0]

                    df[f'Positive sequence V {_ + 1}'], df[f'Negative sequence V {_ + 1}'], df[
                        f'Zero sequence V {_ + 1}'] = ppf.sequencetransform(
                        df['Time'], va_dft, vb_dft, vc_dft)
                    df[f'Positive sequence I {_ + 1}'], df[f'Negative sequence I {_ + 1}'], df[
                        f'Zero sequence I {_ + 1}'] = ppf.sequencetransform(
                        df['Time'], ia_dft, ib_dft, ic_dft)

                    fa = ppf.freq4mdftPhasor(va_dft, np.array(df['time']), 1)
                    fa[:np.argwhere(np.isnan(fa))[-1][0] + 1] = fa[np.argwhere(np.isnan(fa))[-1][0] + 1]  # Replaces the rise cycle and Nan values to first Non Nan value.

                    fb = ppf.freq4mdftPhasor(vb_dft, np.array(df['time']), 1)
                    fb[:np.argwhere(np.isnan(fb))[-1][0] + 1] = fb[np.argwhere(np.isnan(fb))[-1][0] + 1]

                    fc = ppf.freq4mdftPhasor(vc_dft, np.array(df['time']), 1)
                    fc[:np.argwhere(np.isnan(fc))[-1][0] + 1] = fc[np.argwhere(np.isnan(fc))[-1][0] + 1]

                    f = (fa + fb + fc) / 3

                    df[f'Frequency Fa{_ + 1}'] = fa
                    df[f'Frequency Fb{_ + 1}'] = fb
                    df[f'Frequency Fc{_ + 1}'] = fc
                    df[f'Frequency F_avg{_ + 1}'] = f

                except KeyError as err:
                    QtWidgets.QMessageBox.information(self,
                                                      "Error",
                                                      "Didn't obtain correct number of values, please check your input lists")

        shifting_values = {item: 0 for item in df.columns[1:]}
        shifting_values['x'] = 0

        self.all_files1[filename] = dict(data=df,
                                         shift_values=shifting_values,
                                         color_dict=self.color_list[self.color_index])

        self.color_index += 1
        self.file_names = list(self.all_files1.keys())
        self.list_of_files.clear()
        self.list_of_files.addItems([""] + self.file_names)
        self.groupBox.setEnabled(True)

        with open(f"{self.LE_file_path.text()[:-4]}.pickle", "wb") as outfile:
            pickle.dump(self.all_files1[filename], outfile)
            print("Pickle file generated to load later after this session")

        QtWidgets.QMessageBox.information(self,
                                          "Success",
                                          "File loaded successfully, you can add more files/proceed to plotting")

        self.number_of_files += 1
        self.label_list_of_files.setText(self.label_list_of_files.text() + f"\n\n{self.number_of_files}. {filename}")

    #################################################################################################
    #  Tab-2 -> Plotting area:
    #################################################################################################
    def plot_signal(self, ):
        # Calling function depending on the checkbox selected
        if self.CB_voltage_rms.isChecked():
            self.plot_rms_voltage()
        else:
            self.plot_widget1.clear()

        if self.CB_current_rms.isChecked():
            self.plot_rms_current()
        else:
            self.plot_widget2.clear()

        if self.CB_frequency.isChecked():
            self.plot_avg_frequency()
        else:
            self.plot_widget6.clear()

        if self.CB_real_power.isChecked() and self.CB_reactive_power.isChecked():
            self.plot_widget3.clear()
            self.plot_real_power()
            self.plot_reactive_power()
        elif self.CB_real_power.isChecked():
            self.plot_widget3.clear()
            self.plot_real_power()
        elif self.CB_reactive_power.isChecked():
            self.plot_widget3.clear()
            self.plot_reactive_power()
        else:
            self.plot_widget3.clear()

        if self.CB_voltage_positive.isChecked() and self.CB_voltage_negative.isChecked() and self.CB_voltage_zero.isChecked():
            self.plot_widget4.clear()
            self.plot_positive_voltage()
            self.plot_negative_voltage()
            self.plot_zero_voltage()
        elif self.CB_voltage_positive.isChecked() and self.CB_voltage_negative.isChecked():
            self.plot_widget4.clear()
            self.plot_positive_voltage()
            self.plot_negative_voltage()
        elif self.CB_voltage_zero.isChecked() and self.CB_voltage_negative.isChecked():
            self.plot_widget4.clear()
            self.plot_zero_voltage()
            self.plot_negative_voltage()
        elif self.CB_voltage_positive.isChecked() and self.CB_voltage_zero.isChecked():
            self.plot_widget4.clear()
            self.plot_positive_voltage()
            self.plot_zero_voltage()
        elif self.CB_voltage_positive.isChecked():
            self.plot_widget4.clear()
            self.plot_positive_voltage()
        elif self.CB_voltage_negative.isChecked():
            self.plot_widget4.clear()
            self.plot_negative_voltage()
        elif self.CB_voltage_zero.isChecked():
            self.plot_widget4.clear()
            self.plot_zero_voltage()
        else:
            self.plot_widget4.clear()

        if self.CB_current_positive.isChecked() and self.CB_current_negative.isChecked() and self.CB_current_zero.isChecked():
            self.plot_widget5.clear()
            self.plot_positive_current()
            self.plot_negative_current()
            self.plot_zero_current()
        elif self.CB_current_positive.isChecked() and self.CB_current_negative.isChecked():
            self.plot_widget5.clear()
            self.plot_positive_current()
            self.plot_negative_current()
        elif self.CB_current_zero.isChecked() and self.CB_current_negative.isChecked():
            self.plot_widget5.clear()
            self.plot_zero_current()
            self.plot_negative_current()
        elif self.CB_current_positive.isChecked() and self.CB_current_zero.isChecked():
            self.plot_widget5.clear()
            self.plot_positive_current()
            self.plot_zero_current()
        elif self.CB_current_positive.isChecked():
            self.plot_widget5.clear()
            self.plot_positive_current()
        elif self.CB_current_negative.isChecked():
            self.plot_widget5.clear()
            self.plot_negative_current()
        elif self.CB_current_zero.isChecked():
            self.plot_widget5.clear()
            self.plot_zero_current()
        else:
            self.plot_widget5.clear()

    # Plotting functions:
    def plot_rms_voltage(self):
        self.plot_widget1.clear()
        self.plot_widget1.addLegend(offset=(350, 8))

        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith("RMS_voltage")]:
                self.plot_widget1.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column],
                    pen=pen, name=file[:-4] + f"_{column}")

    def plot_rms_current(self):
        self.plot_widget2.clear()
        self.plot_widget2.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith("RMS_current")]:
                self.plot_widget2.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column],
                    pen=pen, name=file[:-4] + f"_{column}")

    def plot_avg_frequency(self):
        self.plot_widget6.clear()
        self.plot_widget6.addLegend(offset=(350, 8))

        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith("Frequency F_avg")]:
                self.plot_widget6.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column],
                    pen=pen, name=file[:-4] + f"_{column}")

    def plot_real_power(self):
        self.plot_widget3.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith("Real power")]:
                self.plot_widget3.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column],
                    pen=pen, name=file[:-4] + f"_{column}")

    def plot_reactive_power(self):
        self.plot_widget3.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith("Reactive power")]:
                self.plot_widget3.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column],
                    pen=pen, name=file[:-4] + f"_{column}")

    def plot_positive_voltage(self):
        self.plot_widget4.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if
                           item.startswith("Positive sequence V")]:
                self.plot_widget4.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    np.abs(self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column]),
                    pen=pen, name=file[:-4] + f"_{column}")

    def plot_negative_voltage(self):
        self.plot_widget4.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if
                           item.startswith("Negative sequence V")]:
                self.plot_widget4.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    np.abs(self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column]),
                    pen=pen, name=file[:-4] + f"_{column}")

    def plot_zero_voltage(self):
        self.plot_widget4.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith("Zero sequence V")]:
                self.plot_widget4.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    np.abs(self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column]),
                    pen=pen, name=file[:-4] + f"_{column}")

    def plot_positive_current(self):
        self.plot_widget5.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if
                           item.startswith("Positive sequence I")]:
                self.plot_widget5.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    np.abs(self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column]),
                    pen=pen, name=file[:-4] + f"_{column}")

    def plot_negative_current(self):
        self.plot_widget5.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if
                           item.startswith("Negative sequence I")]:
                self.plot_widget5.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    np.abs(self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column]),
                    pen=pen, name=file[:-4] + f"_{column}")

    def plot_zero_current(self):
        self.plot_widget5.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith("Zero sequence I")]:
                self.plot_widget5.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    np.abs(self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column]),
                    pen=pen, name=file[:-4] + f"_{column}")

    def move_left(self):
        try:
            shift = (-1) * float(self.LE_shift_value.text())
            new_val = round(float(self.x_shift_value.text()) + shift, 3)
            self.x_shift_value.setText(str(new_val))
            self.all_files1[self.list_of_files.currentText()]['shift_values']['x'] = float(self.x_shift_value.text())
            self.plot_signal()

        except KeyError as err:
            QtWidgets.QMessageBox.information(self,
                                              "Error",
                                              "Please select a file to shift.")

    def move_right(self):
        try:
            shift = float(self.LE_shift_value.text())
            new_val = round(float(self.x_shift_value.text()) + shift, 3)
            self.x_shift_value.setText(str(new_val))
            self.all_files1[self.list_of_files.currentText()]['shift_values']['x'] = float(self.x_shift_value.text())
            self.plot_signal()

        except KeyError as err:
            QtWidgets.QMessageBox.information(self,
                                              "Error",
                                              "Please select a file to shift.")

    def move_up(self):
        try:
            shift = float(self.LE_shift_value.text())
            new_val = float(self.y_shift_value.text()) + shift

            self.y_shift_value.setText(str(new_val))
            self.all_files1[self.list_of_files.currentText()]['shift_values'][
                self.CB_signals_list.currentText()] = float(self.y_shift_value.text())
            self.plot_signal()

        except KeyError as err:
            QtWidgets.QMessageBox.information(self,
                                              "Error",
                                              "Please select a file to shift.")

    def move_down(self):
        try:
            shift = -float(self.LE_shift_value.text())
            new_val = float(self.y_shift_value.text()) + shift

            self.y_shift_value.setText(str(new_val))
            self.all_files1[self.list_of_files.currentText()]['shift_values'][
                self.CB_signals_list.currentText()] = float(self.y_shift_value.text())
            self.plot_signal()

        except KeyError as err:
            QtWidgets.QMessageBox.information(self,
                                              "Error",
                                              "Please select a file to shift.")

    def load_signals(self):
        filename = self.list_of_files.currentText()
        self.x_shift_value.setText('0')
        self.CB_signals_list.clear()
        if filename != "":
            self.CB_signals_list.addItems([""] + list(self.all_files1[filename]['shift_values'].keys())[:-1])

    def hide_gb1(self):
        if self.hidden == False:
            self.groupBox.hide()
            self.PB_hide_gb1.setText('▽')
            self.label_option.setVisible(True)
            self.hidden = True
            self.b = self.groupBox_2.pos()
            self.groupBox_2.move(self.groupBox.pos())
        else:
            self.groupBox.show()
            self.PB_hide_gb1.setText('△')
            self.label_option.setVisible(False)
            self.hidden = False
            self.groupBox_2.move(self.b)

    def save_state(self):
        for filename in self.file_names:
            with open(fr"C:\Users\dixit\OneDrive\Desktop\Folder_forGUI\pickle files\{filename}.pickle",
                      "wb") as outfile:
                pickle.dump(self.all_files1[filename], outfile)
                print("Pickle file generated to load later after this session")

        QtWidgets.QMessageBox.information(self,
                                          "Success",
                                          "File loaded successfully, you can add more files/proceed to plotting")

    def _plot_segmentation(self, signal, button):
        if button.isChecked():  # Unchecking all checkboxes, and checking the checked checkbox
            self.set_checkboxes_unchecked()
            button.setChecked(True)

        self.plot_widget7.clear()
        self.plot_widget8.clear()

        threshold_pen = pg.mkPen(color=(0, 94, 255), width=1.5)
        segment_pen = pg.mkPen(color=(255, 255, 0), width=1.5)

        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith(signal)]:
                self.q, self.z1, self.threshold = segment_function.segmentation_trendfilter(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column])

                self.plot_widget7.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    np.abs(self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column]),
                    pen=pen, name=file[:-4] + f"_{column}")

                self.plot_widget8.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    self.z1,
                    pen=pen)
                self.plot_widget8.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    [self.threshold] * len(
                        self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x']),
                    pen=threshold_pen)

                for i in range(len(self.q)):
                    self.plot_widget7.plot([self.all_files1[file]['data']["Time"][self.q[i][0] - 1] +
                                            self.all_files1[file]['shift_values']['x']] * 3,
                                           np.linspace(0, max(self.all_files1[file]['data'][column] +
                                                              self.all_files1[file]['shift_values'][column]), 3),
                                           pen=segment_pen)

                    self.plot_widget7.plot([self.all_files1[file]['data']["Time"][self.q[i][-1] + 1] +
                                            self.all_files1[file]['shift_values']['x']] * 3,
                                           np.linspace(0, max(self.all_files1[file]['data'][column] +
                                                              self.all_files1[file]['shift_values'][column]), 3),
                                           pen=segment_pen)

                    self.plot_widget8.plot([self.all_files1[file]['data']["Time"][self.q[i][0] - 1] +
                                            self.all_files1[file]['shift_values']['x']] * 3,
                                           np.linspace(0, max(self.z1), 3), pen=segment_pen)
                    self.plot_widget8.plot([self.all_files1[file]['data']["Time"][self.q[i][-1] + 1] +
                                            self.all_files1[file]['shift_values']['x']] * 3,
                                           np.linspace(0, max(self.z1), 3), pen=segment_pen)

        if not any([button.isChecked() for button in self.tab_3.findChildren(QtWidgets.QCheckBox)]):
            self.plot_widget7.clear()
            self.plot_widget8.clear()

    def set_checkboxes_unchecked(self):
        for edit in self.tab_3.findChildren(QtWidgets.QCheckBox):
            edit.setChecked(False)

    def load_tooltips(self):
        self.TT_remove_selection.setToolTip('To de-select item from list, click on list on a blank area')
        self.label_2.setToolTip('The voltages will be grouped in groups of 3, so enter variables appropriately')
        self.TT_voltage_set.setToolTip(
            'The voltages will be grouped in groups of 3, so enter variables appropriately\nThe order will be:\nA-phase,\nB-phase,\nC-phase')
        self.label_3.setToolTip('The currents will be grouped in groups of 3, so enter variables appropriately')
        self.TT_current_set.setToolTip(
            'The currents will be grouped in groups of 3, so enter variables appropriately\nThe order will be:\nA-phase,\nB-phase,\nC-phase')
        self.TT_set_selection.setToolTip('By default, the 1st set for each will be chosen')

        self.TT_plotting_voltage_rms.setToolTip(f'Calculations done using: √(Va² + Vb² + Vc²)')
        self.TT_plotting_current_rms.setToolTip("Calculations done using: (1/√3) × √(Ia² + Ib² + Ic²)")
        self.TT_plotting_power.setToolTip("Calculations done using:\n"
                                          "P = Va×Ia + Vb×Ib + Vc×Ic\n"
                                          "Q = (1/√3) × ((Va-Vb)×Ic + (Vb-Vc)×Ia + (Vc-Va)×Ic)")

        self.TT_plotting_sequence.setToolTip("Calculations done using:\n"
                                             "⍺ = 1∠120°\n\n"
                                             "Sₜ = ⌜ 1 1 1  ⌝\n"
                                             "       | ⍺² ⍺ 1  |\n"
                                             "       ⌞ ⍺ ⍺² 1⌟\n\n"
                                             "⌜ Vp ⌝          ⌜ Va ⌝\n"
                                             "|  Vn  | = Sₜ⁻¹ | Vb   |\n"
                                             "⌞ V0 ⌟          ⌞ Vc ⌟\n")


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
