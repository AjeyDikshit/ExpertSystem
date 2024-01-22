# This Python file uses the following encoding: utf-8
import os
import time
from pathlib import Path
import sys
import time
import threading

from PyQt5 import QtWidgets, QtCore
from PyQt5 import uic
import pandas as pd
import numpy as np
import pyqtgraph as pg
import pickle
from comtrade import Comtrade, ComtradeError

import PPF as ppf
import segmentation_functions as segment_function

# TODO: The whole codebase can be refactored
# TODO: Refactor all the plotting methods to a single plotting method, that takes the column name as argument (.startswith("<This thing as argument>"))
# TODO: Break the compute values function into 2 functions? 1 for normal and 1 for multiple sets
# TODO: Try to refactor move_left/right and move_up/down to 1 function that takes +1/-1 as the argument.

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

        self.timer = None

        # Collapse widget
        self.hidden = False
        self.b = None
        self.label_option.setVisible(False)

        # Instantaneous tab
        self.PB_add_instantaneous_plots.clicked.connect(self.plot_instantaneous)
        self.PB_remove_instantaneous_plots.clicked.connect(self.remove_plot_instantaneous)
        self.count1 = 0
        self.scroll1 = QtWidgets.QScrollArea()
        self.verticalLayout_2.addWidget(self.scroll1)
        self.layout2 = QtWidgets.QVBoxLayout()
        self.plotted_plot = []

        # Segmentation
        self.q, self.z1, self.threshold = None, None, None
        self.CB_segment_voltage.stateChanged.connect(
            lambda: self._plot_segmentation("RMS_voltage", self.CB_segment_voltage))
        self.CB_segment_current.stateChanged.connect(
            lambda: self._plot_segmentation("RMS_current", self.CB_segment_current))
        self.CB_segment_frequency.stateChanged.connect(
            lambda: self._plot_segmentation("Frequency F_avg", self.CB_segment_frequency))

        # Tooltips:
        self.load_tooltips()

        # Signals -----------------------------------------------------
        # Tab-1 --> User input tab
        self.voltage_set_items = set()
        self.current_set_items = set()

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
        # TODO: add DFT RMS in self.plot_signal function
        self.CB_voltage_rms_dft.stateChanged.connect(self.plot_signal)
        self.CB_current_rms_dft.stateChanged.connect(self.plot_signal)

        self.CB_frequency.stateChanged.connect(self.plot_signal)
        self.CB_impedance.stateChanged.connect(self.plot_signal)

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

        self.PB_scale_signal.clicked.connect(self.scale_signal)

        self.list_of_files.activated.connect(self.load_signals)

        self.PB_hide_gb1.clicked.connect(self.hide_gb1)

        self.PB_save_state.clicked.connect(self.save_state)

        # self.CB_instantaneous_tab.activated.connect(self.plot_instantaneous)
        self.PB_manual_segmentation.clicked.connect(self.manual_segmentation)

        # Default settings
        self.LE_power_selection.setEnabled(False)
        self.PW_voltage_rms.showGrid(x=True, y=True, alpha=1)
        self.PW_current_rms.showGrid(x=True, y=True, alpha=1)
        self.PW_power.showGrid(x=True, y=True, alpha=1)
        self.PW_voltage_seq.showGrid(x=True, y=True, alpha=1)
        self.PW_current_seq.showGrid(x=True, y=True, alpha=1)
        self.PW_frequency.showGrid(x=True, y=True, alpha=1)
        self.PW_impedance.showGrid(x=True, y=True, alpha=1)
        self.PW_impedance.showGrid(x=True, y=True, alpha=1)
        self.PW_voltage_rms_dft.showGrid(x=True, y=True, alpha=1)
        self.PW_current_rms_dft.showGrid(x=True, y=True, alpha=1)
        self.plot_widget7.showGrid(x=True, y=True, alpha=1)
        self.plot_widget8.showGrid(x=True, y=True, alpha=1)
        self.groupBox.setEnabled(False)

    #################################################################################################
    #  Tab-1 -> User input area:
    #################################################################################################
    def get_file(self):
        dlg = QtWidgets.QFileDialog(self)
        self.file_path = dlg.getOpenFileName(self, 'Choose directory',
                                             r"C:\Users\dixit\OneDrive\Desktop\Ajey\Project\AFAS_dec2023\Mumbai Data\Oct12_2020_COMTRADE_Mumbai_Blackout\Unit 7 GRP",
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

            if self.LE_file_path.text().endswith("100125 hrs.cfg"):
                self.LW_voltage_set.addItems(["GTG GEN.Va.", "GTG GEN.Vb.", "GTG GEN.Vc.", "STG GEN.Va.", "STG GEN.Vb.", "STG GEN.Vc."])
                self.LW_current_set.addItems(["GTG GEN.Ia.", "GTG GEN.Ib.", "GTG GEN.Ic.", "STG GEN.Ia.", "STG GEN.Ib.", "STG GEN.Ic."])

        except ComtradeError as err:
            QtWidgets.QMessageBox.information(self,
                                              "Fail",
                                              "File browse failed, please check the filepath")

    def load_file(self):
        dlg = QtWidgets.QFileDialog(self)
        self.file_path = dlg.getOpenFileName(self, 'Choose directory',
                                             r"C:\Users\dixit\OneDrive\Desktop\Ajey\Project\AFAS_dec2023",
                                             filter="Pickle (*.pickle)")[0]

        self.LE_file_path.setText(self.file_path)
        filename = self.LE_file_path.text().split('/')[-1][:-7]

        self.LW_voltage_set.clear()
        self.LW_current_set.clear()
        self.LW_attribute_list.clear()

        try:
            with open(f"{self.file_path}", "rb") as infile:
                self.all_files1[filename] = pickle.load(infile)

            self.file_names = list(self.all_files1.keys())
            self.list_of_files.clear()
            self.list_of_files.addItems([""] + self.file_names)

            self.CB_instantaneous_tab.clear()
            self.CB_instantaneous_tab.addItems([""] + self.file_names)

            self.groupBox.setEnabled(True)

            self.number_of_files += 1
            self.label_list_of_files.setText(
                self.label_list_of_files.text() + f"\n\n{self.number_of_files}. {filename}")

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
        # TODO: Implement threading, such that QMessageBox will pop up
        ...
        # thread = threading.Thread(target=self._compute_values, daemon=True)
        # thread.start()
        self._compute_values()
        # p = QtCore.QThread()
        # p.start(self._compute_values())

    def _compute_values(self):
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
                df_dict[f'Va{count}'] = np.array(self.com.analog[
                    self.com.analog_channel_ids.index(self.LW_voltage_set.item(i).text())]) / 1000
            if i % 3 == 1:
                df_dict[f'Vb{count}'] = np.array(self.com.analog[
                    self.com.analog_channel_ids.index(self.LW_voltage_set.item(i).text())]) / 1000
            if i % 3 == 2:
                df_dict[f'Vc{count}'] = np.array(self.com.analog[
                    self.com.analog_channel_ids.index(self.LW_voltage_set.item(i).text())]) / 1000

        for i in range(count):
            df_dict[f'RMS_voltage {i + 1}'] = ppf.instaLL_RMSVoltage(df_dict['Time'], df_dict[f'Va{i + 1}'],
                                                                     df_dict[f'Vb{i + 1}'], df_dict[f'Vc{i + 1}'])

        count = 0
        for i in range(self.LW_current_set.count()):
            if i % 3 == 0:
                count += 1
                df_dict[f'Ia{count}'] = np.array(self.com.analog[
                    self.com.analog_channel_ids.index(self.LW_current_set.item(i).text())]) / 1000
            if i % 3 == 1:
                df_dict[f'Ib{count}'] = np.array(self.com.analog[
                    self.com.analog_channel_ids.index(self.LW_current_set.item(i).text())]) / 1000
            if i % 3 == 2:
                df_dict[f'Ic{count}'] = np.array(self.com.analog[
                    self.com.analog_channel_ids.index(self.LW_current_set.item(i).text())]) / 1000

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

                df["Z (Impedance)"] = ppf.impedance(va, vb, vc, ia, ib, ic)

                df["DFT Va"] = ppf.window_phasor(np.array(va), np.array(df['Time']), 1, 1)[0]
                df["DFT Vb"] = ppf.window_phasor(np.array(vb), np.array(df['Time']), 1, 1)[0]
                df["DFT Vc"] = ppf.window_phasor(np.array(vc), np.array(df['Time']), 1, 1)[0]
                df["DFT Ia"] = ppf.window_phasor(np.array(ia), np.array(df['Time']), 1, 1)[0]
                df["DFT Ib"] = ppf.window_phasor(np.array(ib), np.array(df['Time']), 1, 1)[0]
                df["DFT Ic"] = ppf.window_phasor(np.array(ic), np.array(df['Time']), 1, 1)[0]

                df["DFT voltage RMS"] = ppf.instaLL_RMSVoltage(np.array(df['Time']),
                                                               np.abs(df["DFT Va"]),
                                                               np.abs(df["DFT Vb"]),
                                                               np.abs(df["DFT Vc"]), )

                df["DFT current RMS"] = ppf.insta_RMSCurrent(np.array(df['Time']),
                                                             np.abs(df["DFT Ia"]),
                                                             np.abs(df["DFT Ib"]),
                                                             np.abs(df["DFT Ic"]), )

                df['Positive sequence V'], df['Negative sequence V'], df['Zero sequence V'] = ppf.sequencetransform(
                    df['Time'], df["DFT Va"], df["DFT Vb"], df["DFT Vc"])
                df['Positive sequence I'], df['Negative sequence I'], df['Zero sequence I'] = ppf.sequencetransform(
                    df['Time'], df["DFT Ia"], df["DFT Ib"], df["DFT Ic"])

                fa = ppf.freq4mdftPhasor(np.array(df["DFT Va"]), np.array(df['Time']), 1)[0]
                fb = ppf.freq4mdftPhasor(np.array(df["DFT Vb"]), np.array(df['Time']), 1)[0]
                fc = ppf.freq4mdftPhasor(np.array(df["DFT Vc"]), np.array(df['Time']), 1)[0]

                fa[:np.argwhere(np.isnan(fa))[-1][0] + 1] = fa[np.argwhere(np.isnan(fa))[-1][0] + 1]
                fb[:np.argwhere(np.isnan(fb))[-1][0] + 1] = fb[np.argwhere(np.isnan(fb))[-1][0] + 1]
                fc[:np.argwhere(np.isnan(fc))[-1][0] + 1] = fc[np.argwhere(np.isnan(fc))[-1][0] + 1]

                f = (fa + fb + fc) / 3

                df[f'Frequency F_avg'] = np.real(f)

            except KeyError as err:
                QtWidgets.QMessageBox.information(self,
                                                  "Error",
                                                  "Didn't obtain correct number of values, please check your input lists")
        elif type(power_input[0]) == list:
            for _ in range(len(power_input)):
                print(_)
                try:
                    self.timer = time.time()
                    va, vb, vc = df[f'Va{power_input[_][0]}'], df[f'Vb{power_input[_][0]}'], df[
                        f'Vc{power_input[_][0]}']
                    ia, ib, ic = df[f'Ia{power_input[_][1]}'], df[f'Ib{power_input[_][1]}'], df[
                        f'Ic{power_input[_][1]}']
                    print("V, I calculated")
                    df[f"Real power {_ + 1}"], df[f'Reactive power {_ + 1}'] = ppf.instant_power(va, vb, vc, ia, ib, ic)
                    print("Power calculated")
                    df[f"Z (Impedance) {_ + 1}"] = ppf.impedance(va, vb, vc, ia, ib, ic)
                    print("Impedance")
                    print(f"Time took: {time.time() - self.timer}")

                    self.timer = time.time()
                    df[f"DFT Ia {_ + 1}"] = ppf.window_phasor(np.array(ia), np.array(df['Time']), 1, 1)[0]
                    df[f"DFT Ib {_ + 1}"] = ppf.window_phasor(np.array(ib), np.array(df['Time']), 1, 1)[0]
                    df[f"DFT Ic {_ + 1}"] = ppf.window_phasor(np.array(ic), np.array(df['Time']), 1, 1)[0]
                    df[f"DFT Va {_ + 1}"] = ppf.window_phasor(np.array(va), np.array(df['Time']), 1, 1)[0]
                    df[f"DFT Vb {_ + 1}"] = ppf.window_phasor(np.array(vb), np.array(df['Time']), 1, 1)[0]
                    df[f"DFT Vc {_ + 1}"] = ppf.window_phasor(np.array(vc), np.array(df['Time']), 1, 1)[0]
                    print(f"DFT calculated took {time.time() - self.timer}s")

                    df[f"DFT voltage RMS {_ + 1}"] = ppf.instaLL_RMSVoltage(np.array(df['Time']),
                                                                            np.abs(df[f"DFT Va {_ + 1}"]),
                                                                            np.abs(df[f"DFT Vb {_ + 1}"]),
                                                                            np.abs(df[f"DFT Vc {_ + 1}"]), )
                    print("DFT RMS V")
                    df[f"DFT current RMS {_ + 1}"] = ppf.insta_RMSCurrent(np.array(df['Time']),
                                                                          np.abs(df[f"DFT Ia {_ + 1}"]),
                                                                          np.abs(df[f"DFT Ib {_ + 1}"]),
                                                                          np.abs(df[f"DFT Ic {_ + 1}"]), )
                    print("DFT RMS I")
                    df[f'Positive sequence V {_ + 1}'], \
                    df[f'Negative sequence V {_ + 1}'], \
                    df[f'Zero sequence V {_ + 1}'] = ppf.sequencetransform(df['Time'],
                                                                           df[f"DFT Va {_ + 1}"],
                                                                           df[f"DFT Vb {_ + 1}"],
                                                                           df[f"DFT Vc {_ + 1}"])
                    print("Sequence V")

                    df[f'Positive sequence I {_ + 1}'], \
                    df[f'Negative sequence I {_ + 1}'], \
                    df[f'Zero sequence I {_ + 1}'] = ppf.sequencetransform(df['Time'],
                                                                           df[f"DFT Ia {_ + 1}"],
                                                                           df[f"DFT Ib {_ + 1}"],
                                                                           df[f"DFT Ic {_ + 1}"])
                    print("Sequence I")

                    fa = ppf.freq4mdftPhasor(df[f"DFT Va {_ + 1}"], np.array(df['Time']), 1)[0]
                    fa[:np.argwhere(np.isnan(fa))[-1][0] + 1] = fa[np.argwhere(np.isnan(fa))[-1][0] + 1]  # Replaces the rise cycle and Nan values to first Non Nan value.
                    fb = ppf.freq4mdftPhasor(df[f"DFT Vb {_ + 1}"], np.array(df['Time']), 1)[0]
                    fb[:np.argwhere(np.isnan(fb))[-1][0] + 1] = fb[np.argwhere(np.isnan(fb))[-1][0] + 1]
                    fc = ppf.freq4mdftPhasor(df[f"DFT Vc {_ + 1}"], np.array(df['Time']), 1)[0]
                    fc[:np.argwhere(np.isnan(fc))[-1][0] + 1] = fc[np.argwhere(np.isnan(fc))[-1][0] + 1]

                    f = (fa + fb + fc) / 3

                    df[f'Frequency F_avg{_ + 1}'] = np.real(f)

                except KeyError as err:
                    QtWidgets.QMessageBox.information(self,
                                                      "Error",
                                                      "Didn't obtain correct number of values, please check your input lists")

        shifting_values = {item: 0 for item in df.columns[1:]}
        shifting_values['x'] = 0

        scaling_values = {item: 1 for item in df.columns[1:]}

        self.all_files1[filename] = dict(data=df,
                                         shift_values=shifting_values,
                                         scaling_values=scaling_values,
                                         color_dict=self.color_list[self.color_index])

        self.color_index += 1
        self.file_names = list(self.all_files1.keys())
        self.list_of_files.clear()
        self.list_of_files.addItems([""] + self.file_names)
        self.groupBox.setEnabled(True)

        self.CB_instantaneous_tab.clear()
        self.CB_instantaneous_tab.addItems([""] + self.file_names)

        print(self.all_files1[filename]['data'].keys())

        with open(f"{self.LE_file_path.text()[:-4]}.pickle", "wb") as outfile:
            pickle.dump(self.all_files1[filename], outfile)
            print("Pickle file generated to load later after this session")

        QtWidgets.QMessageBox.information(self,
                                          "Success",
                                          "File loaded successfully, you can add more files/proceed to plotting")

        self.number_of_files += 1
        self.label_list_of_files.setText(self.label_list_of_files.text() + f"\n\n{self.number_of_files}. {filename}")
        return 
    
    #################################################################################################
    #  Tab-2 -> Plotting area:
    #################################################################################################
    def plot_signal(self, ):
        # Calling function depending on the checkbox selected
        if self.CB_voltage_rms.isChecked():
            self.plot_rms_voltage()
        else:
            self.PW_voltage_rms.clear()

        if self.CB_current_rms.isChecked():
            self.plot_rms_current()
        else:
            self.PW_current_rms.clear()

        if self.CB_voltage_rms_dft.isChecked():
            self.plot_voltage_rms_dft()
        else:
            self.PW_voltage_rms_dft.clear()

        if self.CB_current_rms_dft.isChecked():
            self.plot_current_rms_dft()
        else:
            self.PW_current_rms_dft.clear()

        if self.CB_frequency.isChecked():
            self.plot_avg_frequency()
        else:
            self.PW_frequency.clear()

        if self.CB_impedance.isChecked():
            self.plot_impedance()
        else:
            self.PW_impedance.clear()

        if self.CB_real_power.isChecked() and self.CB_reactive_power.isChecked():
            self.PW_power.clear()
            self.plot_real_power()
            self.plot_reactive_power()
        elif self.CB_real_power.isChecked():
            self.PW_power.clear()
            self.plot_real_power()
        elif self.CB_reactive_power.isChecked():
            self.PW_power.clear()
            self.plot_reactive_power()
        else:
            self.PW_power.clear()

        if self.CB_voltage_positive.isChecked() and self.CB_voltage_negative.isChecked() and self.CB_voltage_zero.isChecked():
            self.PW_voltage_seq.clear()
            self.plot_positive_voltage()
            self.plot_negative_voltage()
            self.plot_zero_voltage()
        elif self.CB_voltage_positive.isChecked() and self.CB_voltage_negative.isChecked():
            self.PW_voltage_seq.clear()
            self.plot_positive_voltage()
            self.plot_negative_voltage()
        elif self.CB_voltage_zero.isChecked() and self.CB_voltage_negative.isChecked():
            self.PW_voltage_seq.clear()
            self.plot_zero_voltage()
            self.plot_negative_voltage()
        elif self.CB_voltage_positive.isChecked() and self.CB_voltage_zero.isChecked():
            self.PW_voltage_seq.clear()
            self.plot_positive_voltage()
            self.plot_zero_voltage()
        elif self.CB_voltage_positive.isChecked():
            self.PW_voltage_seq.clear()
            self.plot_positive_voltage()
        elif self.CB_voltage_negative.isChecked():
            self.PW_voltage_seq.clear()
            self.plot_negative_voltage()
        elif self.CB_voltage_zero.isChecked():
            self.PW_voltage_seq.clear()
            self.plot_zero_voltage()
        else:
            self.PW_voltage_seq.clear()

        if self.CB_current_positive.isChecked() and self.CB_current_negative.isChecked() and self.CB_current_zero.isChecked():
            self.PW_current_seq.clear()
            self.plot_positive_current()
            self.plot_negative_current()
            self.plot_zero_current()
        elif self.CB_current_positive.isChecked() and self.CB_current_negative.isChecked():
            self.PW_current_seq.clear()
            self.plot_positive_current()
            self.plot_negative_current()
        elif self.CB_current_zero.isChecked() and self.CB_current_negative.isChecked():
            self.PW_current_seq.clear()
            self.plot_zero_current()
            self.plot_negative_current()
        elif self.CB_current_positive.isChecked() and self.CB_current_zero.isChecked():
            self.PW_current_seq.clear()
            self.plot_positive_current()
            self.plot_zero_current()
        elif self.CB_current_positive.isChecked():
            self.PW_current_seq.clear()
            self.plot_positive_current()
        elif self.CB_current_negative.isChecked():
            self.PW_current_seq.clear()
            self.plot_negative_current()
        elif self.CB_current_zero.isChecked():
            self.PW_current_seq.clear()
            self.plot_zero_current()
        else:
            self.PW_current_seq.clear()

    # Plotting functions:
    def plot_rms_voltage(self):
        self.PW_voltage_rms.clear()
        self.PW_voltage_rms.addLegend(offset=(350, 8))

        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith("RMS_voltage")]:
                self.PW_voltage_rms.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    (self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column]) * self.all_files1[file]['scaling_values'][column],
                    pen=pen, name=file + f"_{column}")

    def plot_rms_current(self):
        self.PW_current_rms.clear()
        self.PW_current_rms.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith("RMS_current")]:
                self.PW_current_rms.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    (self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column]) * self.all_files1[file]['scaling_values'][column],
                    pen=pen, name=file + f"_{column}")

    def plot_voltage_rms_dft(self):
        self.PW_voltage_rms_dft.clear()
        self.PW_voltage_rms_dft.addLegend(offset=(350, 8))

        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith("DFT voltage RMS")]:
                self.PW_voltage_rms_dft.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column],
                    pen=pen, name=file + f"_{column}")

    def plot_current_rms_dft(self):
        self.PW_current_rms_dft.clear()
        self.PW_current_rms_dft.addLegend(offset=(350, 8))

        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith("DFT current RMS")]:
                self.PW_current_rms_dft.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column],
                    pen=pen, name=file + f"_{column}")

    def plot_avg_frequency(self):
        self.PW_frequency.clear()
        self.PW_frequency.addLegend(offset=(350, 8))

        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith("Frequency F_avg")]:
                self.PW_frequency.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column],
                    pen=pen, name=file + f"_{column}")

    def plot_impedance(self):
        self.PW_impedance.clear()
        self.PW_impedance.addLegend(offset=(350, 8))

        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith("Z (Impedance)")]:
                self.PW_impedance.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column],
                    pen=pen, name=file + f"_{column}")

    def plot_real_power(self):
        self.PW_power.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith("Real power")]:
                self.PW_power.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column],
                    pen=pen, name=file + f"_{column}")

    def plot_reactive_power(self):
        self.PW_power.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith("Reactive power")]:
                self.PW_power.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column],
                    pen=pen, name=file + f"_{column}")

    def plot_positive_voltage(self):
        self.PW_voltage_seq.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if
                           item.startswith("Positive sequence V")]:
                self.PW_voltage_seq.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    np.abs(self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column]),
                    pen=pen, name=file + f"_{column}")

    def plot_negative_voltage(self):
        self.PW_voltage_seq.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if
                           item.startswith("Negative sequence V")]:
                self.PW_voltage_seq.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    np.abs(self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column]),
                    pen=pen, name=file + f"_{column}")

    def plot_zero_voltage(self):
        self.PW_voltage_seq.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith("Zero sequence V")]:
                self.PW_voltage_seq.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    np.abs(self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column]),
                    pen=pen, name=file + f"_{column}")

    def plot_positive_current(self):
        self.PW_current_seq.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if
                           item.startswith("Positive sequence I")]:
                self.PW_current_seq.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    np.abs(self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column]),
                    pen=pen, name=file + f"_{column}")

    def plot_negative_current(self):
        self.PW_current_seq.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if
                           item.startswith("Negative sequence I")]:
                self.PW_current_seq.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    np.abs(self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column]),
                    pen=pen, name=file + f"_{column}")

    def plot_zero_current(self):
        self.PW_current_seq.addLegend(offset=(350, 8))
        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith("Zero sequence I")]:
                self.PW_current_seq.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    np.abs(self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column]),
                    pen=pen, name=file + f"_{column}")

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

    def scale_signal(self):
        try:
            self.current_scale.setText(str(float(self.current_scale.text()) * float(self.LE_scaling_factor.text())))
            value = float(self.current_scale.text())

            self.all_files1[self.list_of_files.currentText()]['scaling_values'][
                self.CB_signals_list.currentText()] = value

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
        if not self.hidden:
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

    def plot_instantaneous(self):
        self.count1 += 1

        # for i in range(self.count1):
        file = self.CB_instantaneous_tab.currentText()

        if file == "":
            QtWidgets.QMessageBox.information(self,
                                              "Error",
                                              "Please select a file to shift.")
            return

        if file not in self.plotted_plot:
            self.plotted_plot.append(file)

            self.plot1 = pg.PlotWidget()
            self.plot1.addLegend(offset=(280, 8))
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
            self.plot2.addLegend(offset=(280, 8))
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

        else:
            QtWidgets.QMessageBox.information(self,
                                              "Error",
                                              "Plot already plotted!")

    def remove_plot_instantaneous(self):
        h_layouts = self.scroll1.findChildren(QtWidgets.QHBoxLayout)
        plot_layout = self.scroll1.findChildren(pg.PlotWidget)

        file = self.CB_instantaneous_tab.currentText()

        if file in self.plotted_plot:
            h_layout = h_layouts[self.plotted_plot.index(file)]
            self.layout2.removeItem(h_layout)
            plot_layout[0 + 2 * (self.plotted_plot.index(file))].deleteLater()
            plot_layout[1 + 2 * (self.plotted_plot.index(file))].deleteLater()
            self.plotted_plot.remove(file)

        else:
            QtWidgets.QMessageBox.information(self,
                                              "Error",
                                              "Plot doesn't exist!")

    def _plot_segmentation(self, signal, button):
        if button.isChecked():  # Unchecking all checkboxes, and checking the checked checkbox
            self.set_checkboxes_unchecked()
            button.setChecked(True)

        self.plot_widget7.clear()
        self.plot_widget8.clear()
        self.LE_threshold_value.setText("")

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
                    (self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column]) * self.all_files1[file]['scaling_values'][column],
                    pen=pen, name=file + f"_{column}")

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
                                           np.linspace(min(self.all_files1[file]['data'][column] +
                                                           self.all_files1[file]['shift_values'][column]),
                                                       max(self.all_files1[file]['data'][column] +
                                                           self.all_files1[file]['shift_values'][column]), 3),
                                           pen=segment_pen)

                    self.plot_widget7.plot([self.all_files1[file]['data']["Time"][self.q[i][-1] + 1] +
                                            self.all_files1[file]['shift_values']['x']] * 3,
                                           np.linspace(min(self.all_files1[file]['data'][column] +
                                                           self.all_files1[file]['shift_values'][column]),
                                                       max(self.all_files1[file]['data'][column] +
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

    def _plot_manual_segmentation(self, signal):
        self.plot_widget7.clear()
        self.plot_widget8.clear()

        threshold = float(self.LE_threshold_value.text())
        threshold_pen = pg.mkPen(color=(0, 94, 255), width=1.5)
        segment_pen = pg.mkPen(color=(255, 255, 0), width=1.5)

        for file in self.file_names:
            pen = pg.mkPen(color=self.all_files1[file]['color_dict'], width=1.5)
            for column in [item for item in self.all_files1[file]['data'].keys() if item.startswith(signal)]:
                self.q, self.z1 = segment_function.manual_segmentation_trendfilter(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column],
                    threshold
                )

                self.plot_widget7.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    (self.all_files1[file]['data'][column] + self.all_files1[file]['shift_values'][column]) * self.all_files1[file]['scaling_values'][column],
                    pen=pen, name=file + f"_{column}")

                self.plot_widget8.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    self.z1,
                    pen=pen)
                self.plot_widget8.plot(
                    self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x'],
                    [threshold] * len(
                        self.all_files1[file]['data']["Time"] + self.all_files1[file]['shift_values']['x']),
                    pen=threshold_pen)

                for i in range(len(self.q)):
                    self.plot_widget7.plot([self.all_files1[file]['data']["Time"][self.q[i][0] - 1] +
                                            self.all_files1[file]['shift_values']['x']] * 3,
                                           np.linspace(min(self.all_files1[file]['data'][column] +
                                                           self.all_files1[file]['shift_values'][column]),
                                                       max(self.all_files1[file]['data'][column] +
                                                           self.all_files1[file]['shift_values'][column]), 3),
                                           pen=segment_pen)

                    self.plot_widget7.plot([self.all_files1[file]['data']["Time"][self.q[i][-1] + 1] +
                                            self.all_files1[file]['shift_values']['x']] * 3,
                                           np.linspace(min(self.all_files1[file]['data'][column] +
                                                           self.all_files1[file]['shift_values'][column]),
                                                       max(self.all_files1[file]['data'][column] +
                                                           self.all_files1[file]['shift_values'][column]), 3),
                                           pen=segment_pen)

                    self.plot_widget8.plot([self.all_files1[file]['data']["Time"][self.q[i][0] - 1] +
                                            self.all_files1[file]['shift_values']['x']] * 3,
                                           np.linspace(0, max(self.z1), 3), pen=segment_pen)
                    self.plot_widget8.plot([self.all_files1[file]['data']["Time"][self.q[i][-1] + 1] +
                                            self.all_files1[file]['shift_values']['x']] * 3,
                                           np.linspace(0, max(self.z1), 3), pen=segment_pen)

    def manual_segmentation(self):
        if self.CB_segment_voltage.isChecked():
            self._plot_manual_segmentation("RMS_voltage")

        elif self.CB_segment_current.isChecked():
            self._plot_manual_segmentation("RMS_current")

        elif self.CB_segment_frequency.isChecked():
            self._plot_manual_segmentation("Frequency F_avg")

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
