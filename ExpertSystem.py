# This Python file uses the following encoding: utf-8
import os
import time
from pathlib import Path
import sys

import numpy
from PyQt5 import QtWidgets, QtCore
from PyQt5 import uic
import pandas as pd
import numpy as np
import pyqtgraph as pg
import pickle
from comtrade import Comtrade, ComtradeError

import PPF as ppf
import segmentation_functions as segment_function

# TODO: Remove the 0s in DFT (The "cycles" part)
# TODO: Option to remove files if required

"""
The following code has been written in order of the tabs in the UI, to look for a specific tab just search "Tab-{Tab number}"
The first half of the code (the code inside __init__ method is responsible for calling all the function when a certain action is performed.

There are some "rules" I have followed when naming the UI attributes, they are as follows:
- LW: List Widget (Ex: LW_voltage_set => List widget which stores the voltages)
- LE: Line Edit Widget (Ex: LE_power_selection => Line edit which takes the combination of voltages and current on which we should calculate Power, and some other derived quantities)
- PB: Push button (Ex: PB_load_file)
- TT: Tooltips
- CB: Checkboxes (Ex: CB_voltage_rms => For plotting voltage rms)
- ComB: Combo boxes (Ex: ComB_ComB_list_of_files => When the files are loaded, this will be populated with the same)
- PW: Plot widgets (Ex: PW_voltage_rms => Plot widget corresponding to voltage rms plots)
- labels have just been given appropriate names when required, and don't follow any rule
"""


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('ExpertSystem.ui', self)

        #################################################################################################
        #  General:
        #################################################################################################
        self.load_tooltips()  # Loading all the tooltips

        self.com = Comtrade()  # Initializing at start so that it can be reused for all files.
        self.files_data_dict = {}

        """
        This is how the self.files_data_dict looks like internally =>
        For each file we have a dictionary that stores the data, shift/scale values, plot color.
        self.files_data_dict = {
            "filename": {
                "data": A pandas Dataframe, which stores all the signal values (from the comtrade file and the derived quantities),
                "shift_values": A Python dictionary, which stores value of the x-y shift, by default they are 0 (No shift),
                "scaling_values": Similar to shift values, but for the scaling of the signals, by default the value is 1,
                "plot_color": Stores the color, which the file will use for all the plots
            },
            
            "filename": {
                "data": A pandas Dataframe, which stores all the signal values (from the comtrade file and the derived quantities),
                "shift_values": A Python dictionary, which stores value of the x-y shift, by default they are 0 (No shift),
                "scaling_values": Similar to shift values, but for the scaling of the signals, by default the value is 1,
                "plot_color": Stores the color, which the file will use for all the plots
            }
        }
        """

        self.groupBox.setEnabled(False)

        #################################################################################################
        #  Tab-1 -> User input area:
        #################################################################################################
        self.file_path = None  # File path of file, user is going to load
        self.file_names = []  # Store the names of files that are loaded/computed

        # List consisting of different RGB values, duplicated 2 times, so total we have 20 colors
        self.color_list = [(222, 60, 0), (222, 60, 163), (200, 60, 222), (125, 114, 223), (71, 165, 247),
                           (20, 190, 209), (24, 255, 109), (168, 230, 76), (247, 255, 0), (255, 162, 0)] * 2
        self.color_index = 0

        self.number_of_files = 0

        # Creating a set for the voltages, currents to avoid duplicate entries in the list widget.
        self.voltage_set_items = set()
        self.current_set_items = set()
        self.LE_power_selection.setEnabled(False)

        # Calling methods depending on what is clicked
        self.PB_browse_file_location.clicked.connect(self.get_file)
        self.PB_load_file.clicked.connect(self.load_file)
        self.PB_load_save_state.clicked.connect(self.load_save_state)
        self.PB_move_to_voltage.clicked.connect(self.move_to_voltage)
        self.PB_move_to_current.clicked.connect(self.move_to_current)
        self.PB_remove_entry.clicked.connect(self.removeSel)
        self.PB_compute_values.clicked.connect(self.compute_values)

        self.LW_voltage_set.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.LW_current_set.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        #################################################################################################
        #  Tab-2 -> Signal plotting tab:
        #################################################################################################
        # Stores all the plots in the scroll area of tab-2 in sequential order
        self.tab2_plots = self.scrollArea.findChildren(pg.PlotWidget)
        for plot in self.tab2_plots:
            plot.showGrid(x=True, y=True, alpha=1)

        # Collapse widget
        self.hidden = False
        self.b = None
        self.label_option.setVisible(False)

        # Calling methods depending on what is clicked
        self.CB_voltage_rms.stateChanged.connect(self.plot_signal)
        self.CB_current_rms.stateChanged.connect(self.plot_signal)
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

        # lambda functions are required here as I want to pass some arguments to the function, this is true for all the places' lambda function is called
        self.PB_move_left.clicked.connect(lambda: self.move_horizontal(-1))
        self.PB_move_right.clicked.connect(lambda: self.move_horizontal(1))

        self.PB_move_up.clicked.connect(lambda: self.move_vertical(1))
        self.PB_move_down.clicked.connect(lambda: self.move_vertical(-1))

        self.PB_scale_signal.clicked.connect(self.scale_signal)

        self.ComB_list_of_files.activated.connect(self.load_signals)

        self.PB_hide_gb1.clicked.connect(self.hide_gb1)

        self.PB_save_state.clicked.connect(self.save_state)

        #################################################################################################
        #  Tab-3 -> Instantaneous plots tab:
        #################################################################################################
        self.PB_add_instantaneous_plots.clicked.connect(self.plot_instantaneous)
        self.PB_remove_instantaneous_plots.clicked.connect(self.remove_plot_instantaneous)

        # Preparing the scroll area
        self.scroll1 = QtWidgets.QScrollArea()
        self.verticalLayout_2.addWidget(self.scroll1)

        # Preparing the vertical layout that will hold plots
        self.tab3_plot_layout = QtWidgets.QVBoxLayout()
        self.tab3_plot_layout.setAlignment(QtCore.Qt.AlignTop)
        self.tab3_plot_layout.setSpacing(5)

        # Variables to check which files have been plotted to avoid duplications
        self.plot_dict = {}
        self.plotted_plot = []

        #################################################################################################
        #  Tab-4 -> Segmentation tab:
        #################################################################################################
        # Initializing the variables
        self.q, self.z1, self.threshold = None, None, None
        self.super_q = None
        self.max_val = [0, 0]
        self.min_val = 0
        self.segments = None
        self.segments_copy = None
        self.signal_dataItems = {}
        self.difference_dataItems = {}
        # Adding grid to the plots
        self.PW_signal_segment.showGrid(x=True, y=True, alpha=1)
        self.PW_difference_segment.showGrid(x=True, y=True, alpha=1)

        self.PB_add_segments.clicked.connect(self.add_segments)
        self.PB_remove_segments.clicked.connect(self.delete_segments)

        # Calling functions
        self.CB_segment_voltage.stateChanged.connect(
            lambda: self.calculate_segmentation("RMS_voltage", self.CB_segment_voltage))
        self.CB_segment_current.stateChanged.connect(
            lambda: self.calculate_segmentation("RMS_current", self.CB_segment_current))
        self.CB_segment_frequency.stateChanged.connect(
            lambda: self.calculate_segmentation("Frequency F_avg", self.CB_segment_frequency))

        self.PB_manual_segmentation.clicked.connect(self.manual_segmentation)

        self.PB_shift_segment_left.clicked.connect(lambda: self.shift_segment(-1))
        self.PB_shift_segment_right.clicked.connect(lambda: self.shift_segment(1))

    #################################################################################################
    #  Tab-1 -> User input area:
    #################################################################################################
    def get_file(self):
        """
        Method used to select the file whose derived quantities needs to be computed.
        """
        dlg = QtWidgets.QFileDialog(self)
        # Change the path appropriately, the path you give will be the location where the pop-up window will start from,
        # default is C:/ (User will have to traverse multiple folders each time to select the file)
        self.file_path = dlg.getOpenFileName(self, 'Choose directory',
                                             r"C:\Users\dixit\OneDrive\Desktop\Ajey\Project\AFAS_dec2023\Mumbai Data\Oct12_2020_COMTRADE_Mumbai_Blackout\Unit 7 GRP",
                                             filter="Config files (*.cfg *.CFG)")[0]
        self.LE_file_path.setText(self.file_path)

        filename = self.LE_file_path.text().split('/')[-1][:-4]

        try:
            self.com.load(self.file_path)  # Loading the comtrade object with the file.
            self.LW_attribute_list.clear()  # Default behaviour
            # Adding all the analog signals available in the comtrade file
            self.LW_attribute_list.addItems(self.com.analog_channel_ids)
            # Clearing the sets, incase the signal names match the previous loaded file.
            self.LW_voltage_set.clear()
            self.LW_current_set.clear()

            if self.LE_file_path.text().endswith("100125 hrs.cfg"):
                self.LW_voltage_set.addItems(
                    ["GTG GEN.Va.", "GTG GEN.Vb.", "GTG GEN.Vc.", "STG GEN.Va.", "STG GEN.Vb.", "STG GEN.Vc."])
                self.LW_current_set.addItems(
                    ["GTG GEN.Ia.", "GTG GEN.Ib.", "GTG GEN.Ic.", "STG GEN.Ia.", "STG GEN.Ib.", "STG GEN.Ic."])

        except ComtradeError as err:
            QtWidgets.QMessageBox.information(self,
                                              "Fail",
                                              "File browse failed, please check the filepath")

    def move_to_voltage(self):
        item = self.LW_attribute_list.currentItem().text()
        if item not in self.voltage_set_items:
            self.LW_voltage_set.addItem(item)  # Adding signal to list widget
            self.voltage_set_items.add(item)  # Adding signal to the set
            self.LW_attribute_list.clearSelection()  # Removing the selection
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
        """
        The main engine for the computation of derived values
        """

        df_dict = {}
        number_of_voltage_sets = self.LW_voltage_set.count() // 3
        number_of_current_sets = self.LW_current_set.count() // 3

        filename = self.LE_file_path.text().split('/')[-1][:-4]
        print(f"For {filename}, starting calculations")

        df_dict['Time'] = self.com.time  # Adding time to the dictionary from the comtrade file.

        # The following code will add all the instantaneous voltages to the dictionary ending with the set number (Ex: Va1, Vb1, Vc1, Va2, Vb2...) for as many sets there are
        # And calculates the rms voltage for each set
        count = 0
        for i in range(self.LW_voltage_set.count()):
            if i % 3 == 0:
                count += 1
                df_dict[f'Va{count}'] = np.array(self.com.analog[
                                                     self.com.analog_channel_ids.index(
                                                         self.LW_voltage_set.item(i).text())]) / 1000
            if i % 3 == 1:
                df_dict[f'Vb{count}'] = np.array(self.com.analog[
                                                     self.com.analog_channel_ids.index(
                                                         self.LW_voltage_set.item(i).text())]) / 1000
            if i % 3 == 2:
                df_dict[f'Vc{count}'] = np.array(self.com.analog[
                                                     self.com.analog_channel_ids.index(
                                                         self.LW_voltage_set.item(i).text())]) / 1000

        for i in range(count):
            df_dict[f'RMS_voltage {i + 1}'] = ppf.instaLL_RMSVoltage(df_dict['Time'], df_dict[f'Va{i + 1}'],
                                                                     df_dict[f'Vb{i + 1}'], df_dict[f'Vc{i + 1}'])
        print(f"Instantaneous, RMS voltage: ✓")

        # Current instantaneous and rms
        count = 0
        for i in range(self.LW_current_set.count()):
            if i % 3 == 0:
                count += 1
                df_dict[f'Ia{count}'] = np.array(self.com.analog[
                                                     self.com.analog_channel_ids.index(
                                                         self.LW_current_set.item(i).text())]) / 1000
            if i % 3 == 1:
                df_dict[f'Ib{count}'] = np.array(self.com.analog[
                                                     self.com.analog_channel_ids.index(
                                                         self.LW_current_set.item(i).text())]) / 1000
            if i % 3 == 2:
                df_dict[f'Ic{count}'] = np.array(self.com.analog[
                                                     self.com.analog_channel_ids.index(
                                                         self.LW_current_set.item(i).text())]) / 1000

        for i in range(count):
            df_dict[f'RMS_current {i + 1}'] = ppf.instaLL_RMSVoltage(df_dict['Time'], df_dict[f'Ia{i + 1}'],
                                                                     df_dict[f'Ib{i + 1}'], df_dict[f'Ic{i + 1}'])
        print(f"Instantaneous, RMS current: ✓")

        # Creating a dataFrame using the dictionary we had been using so far (No use of the dictionary after this)
        df = pd.DataFrame(df_dict)

        # For derived quantities calculations:
        # Evaluating the value in the power selection, to check if multiple power/derived quantities calculation needs to be performed.
        # The power_input variable will be either a list with 2 values [1, 1] or a nested list signifying the sets of VI [[1, 1], [2, 2]]
        power_input = list(eval(self.LE_power_selection.text()))
        if type(power_input[
                    0]) == int:  # If this condition is True, we have to calculate power/derived quantities for a single set of VI

            if power_input[0] > number_of_voltage_sets or power_input[1] > number_of_current_sets:
                QtWidgets.QMessageBox.information(self, "Error", "Please input proper values for power calculation")
            try:
                # Storing the following values in variables as they are required multiple times for the calculation
                va, vb, vc = df[f'Va{power_input[0]}'], df[f'Vb{power_input[0]}'], df[f'Vc{power_input[0]}']
                ia, ib, ic = df[f'Ia{power_input[1]}'], df[f'Ib{power_input[1]}'], df[f'Ic{power_input[1]}']

                # Calling appropriate function from PPF.py file to calculate the required quantities.
                df["Real power"], df['Reactive power'] = ppf.instant_power(va, vb, vc, ia, ib, ic)
                print(f"Power: ✓")

                df["Z (Impedance)"] = ppf.impedance(va, vb, vc, ia, ib, ic)
                print(f"Impedance: ✓")

                df["DFT Va"] = ppf.window_phasor(np.array(va), np.array(df['Time']), 1, 1)[0]
                df["DFT Vb"] = ppf.window_phasor(np.array(vb), np.array(df['Time']), 1, 1)[0]
                df["DFT Vc"] = ppf.window_phasor(np.array(vc), np.array(df['Time']), 1, 1)[0]
                df["DFT Ia"] = ppf.window_phasor(np.array(ia), np.array(df['Time']), 1, 1)[0]
                df["DFT Ib"] = ppf.window_phasor(np.array(ib), np.array(df['Time']), 1, 1)[0]
                df["DFT Ic"] = ppf.window_phasor(np.array(ic), np.array(df['Time']), 1, 1)[0]

                print(f"DFT of instantaneous signals: ✓")

                df["DFT voltage RMS"] = ppf.instaLL_RMSVoltage(np.array(df['Time']),
                                                               np.abs(df["DFT Va"]),
                                                               np.abs(df["DFT Vb"]),
                                                               np.abs(df["DFT Vc"]), )
                print(f"RMS voltage using DFT: ✓")

                df["DFT current RMS"] = ppf.insta_RMSCurrent(np.array(df['Time']),
                                                             np.abs(df["DFT Ia"]),
                                                             np.abs(df["DFT Ib"]),
                                                             np.abs(df["DFT Ic"]), )
                print(f"RMS current using DFT: ✓")

                df['Positive sequence V'], df['Negative sequence V'], df['Zero sequence V'] = ppf.sequencetransform(
                    df['Time'], df["DFT Va"], df["DFT Vb"], df["DFT Vc"])
                print(f"Sequence transform (Voltage): ✓")

                df['Positive sequence I'], df['Negative sequence I'], df['Zero sequence I'] = ppf.sequencetransform(
                    df['Time'], df["DFT Ia"], df["DFT Ib"], df["DFT Ic"])
                print(f"Sequence transform (Current): ✓")

                fa = ppf.freq4mdftPhasor(np.array(df["DFT Va"]), np.array(df['Time']), 1)[0]
                fb = ppf.freq4mdftPhasor(np.array(df["DFT Vb"]), np.array(df['Time']), 1)[0]
                fc = ppf.freq4mdftPhasor(np.array(df["DFT Vc"]), np.array(df['Time']), 1)[0]

                fa[:np.argwhere(np.isnan(fa))[-1][0] + 1] = fa[np.argwhere(np.isnan(fa))[-1][0] + 1]
                fb[:np.argwhere(np.isnan(fb))[-1][0] + 1] = fb[np.argwhere(np.isnan(fb))[-1][0] + 1]
                fc[:np.argwhere(np.isnan(fc))[-1][0] + 1] = fc[np.argwhere(np.isnan(fc))[-1][0] + 1]

                f = (fa + fb + fc) / 3

                df[f'Frequency F_avg'] = np.real(f)
                print(f"Frequency: ✓")

            except KeyError as err:
                QtWidgets.QMessageBox.information(self,
                                                  "Error",
                                                  "Didn't obtain correct number of values, please check your input lists")
                return
        elif type(power_input[
                      0]) == list:  # If this condition is True, that means we have to calculate multiple sets of derived quantities.
            for _ in range(len(power_input)):  # Looping through the nested list
                print(f"\n---------------------------\nCalculations for set {_ + 1}\n---------------------------")
                try:
                    # The rest of the code is same as above, except the naming for each derived quantity, signifying the set of VI used for calculations
                    va, vb, vc = df[f'Va{power_input[_][0]}'], df[f'Vb{power_input[_][0]}'], df[
                        f'Vc{power_input[_][0]}']
                    ia, ib, ic = df[f'Ia{power_input[_][1]}'], df[f'Ib{power_input[_][1]}'], df[
                        f'Ic{power_input[_][1]}']

                    df[f"Real power {_ + 1}"], df[f'Reactive power {_ + 1}'] = ppf.instant_power(va, vb, vc, ia, ib, ic)
                    print(f"Power: ✓")

                    df[f"Z (Impedance) {_ + 1}"] = ppf.impedance(va, vb, vc, ia, ib, ic)
                    print(f"Impedance: ✓")

                    df[f"DFT Ia {_ + 1}"] = ppf.window_phasor(np.array(ia), np.array(df['Time']), 1, 1)[0]
                    df[f"DFT Ib {_ + 1}"] = ppf.window_phasor(np.array(ib), np.array(df['Time']), 1, 1)[0]
                    df[f"DFT Ic {_ + 1}"] = ppf.window_phasor(np.array(ic), np.array(df['Time']), 1, 1)[0]
                    df[f"DFT Va {_ + 1}"] = ppf.window_phasor(np.array(va), np.array(df['Time']), 1, 1)[0]
                    df[f"DFT Vb {_ + 1}"] = ppf.window_phasor(np.array(vb), np.array(df['Time']), 1, 1)[0]
                    df[f"DFT Vc {_ + 1}"] = ppf.window_phasor(np.array(vc), np.array(df['Time']), 1, 1)[0]
                    print(f"DFT of instantaneous signals: ✓")

                    df[f"DFT voltage RMS {_ + 1}"] = ppf.instaLL_RMSVoltage(np.array(df['Time']),
                                                                            np.abs(df[f"DFT Va {_ + 1}"]),
                                                                            np.abs(df[f"DFT Vb {_ + 1}"]),
                                                                            np.abs(df[f"DFT Vc {_ + 1}"]), )
                    print(f"RMS voltage using DFT: ✓")

                    df[f"DFT current RMS {_ + 1}"] = ppf.insta_RMSCurrent(np.array(df['Time']),
                                                                          np.abs(df[f"DFT Ia {_ + 1}"]),
                                                                          np.abs(df[f"DFT Ib {_ + 1}"]),
                                                                          np.abs(df[f"DFT Ic {_ + 1}"]), )
                    print(f"RMS current using DFT: ✓")

                    df[f'Positive sequence V {_ + 1}'], \
                    df[f'Negative sequence V {_ + 1}'], \
                    df[f'Zero sequence V {_ + 1}'] = ppf.sequencetransform(df['Time'],
                                                                           df[f"DFT Va {_ + 1}"],
                                                                           df[f"DFT Vb {_ + 1}"],
                                                                           df[f"DFT Vc {_ + 1}"])
                    print(f"Sequence transform (Voltage): ✓")
                    df[f'Positive sequence I {_ + 1}'], \
                    df[f'Negative sequence I {_ + 1}'], \
                    df[f'Zero sequence I {_ + 1}'] = ppf.sequencetransform(df['Time'],
                                                                           df[f"DFT Ia {_ + 1}"],
                                                                           df[f"DFT Ib {_ + 1}"],
                                                                           df[f"DFT Ic {_ + 1}"])
                    print(f"Sequence transform (Current): ✓")

                    fa = ppf.freq4mdftPhasor(df[f"DFT Va {_ + 1}"], np.array(df['Time']), 1)[0]
                    fa[:np.argwhere(np.isnan(fa))[-1][0] + 1] = fa[np.argwhere(np.isnan(fa))[-1][
                                                                       0] + 1]  # Replaces the rise cycle and Nan values to first Non Nan value.
                    fb = ppf.freq4mdftPhasor(df[f"DFT Vb {_ + 1}"], np.array(df['Time']), 1)[0]
                    fb[:np.argwhere(np.isnan(fb))[-1][0] + 1] = fb[np.argwhere(np.isnan(fb))[-1][0] + 1]
                    fc = ppf.freq4mdftPhasor(df[f"DFT Vc {_ + 1}"], np.array(df['Time']), 1)[0]
                    fc[:np.argwhere(np.isnan(fc))[-1][0] + 1] = fc[np.argwhere(np.isnan(fc))[-1][0] + 1]

                    f = (fa + fb + fc) / 3

                    df[f'Frequency F_avg{_ + 1}'] = np.real(f)
                    print(f"Frequency: ✓")

                except KeyError as err:
                    QtWidgets.QMessageBox.information(self,
                                                      "Error",
                                                      "Didn't obtain correct number of values, please check your input lists")
                    return

        # Once all the calculations are complete, we move to storing the calculated data along with some extra later-required quantities

        # Stores the horizontal/vertical shifted value of the file, by default the values are 0
        shifting_values = {item: 0 for item in df.columns[1:]}
        shifting_values['x'] = 0

        # Store the scaling for each signal in the file, default value is 1
        scaling_values = {item: 1 for item in df.columns[1:]}

        # Creating a final nested dictionary which stores all the required data corresponding to the file.
        self.files_data_dict[filename] = dict(data=df,
                                              shift_values=shifting_values,
                                              scaling_values=scaling_values,
                                              plot_color=self.color_list[self.color_index])

        self.color_index += 1

        # For tab-1
        self.number_of_files += 1
        self.label_list_of_files.setText(self.label_list_of_files.text() + f"\n\n{self.number_of_files}. {filename}")

        # For tab-2:
        self.file_names = list(self.files_data_dict.keys())
        self.ComB_list_of_files.clear()
        self.ComB_list_of_files.addItems([""] + self.file_names)
        self.groupBox.setEnabled(True)

        # For tab-3
        self.ComB_instantaneous_tab.clear()
        self.ComB_instantaneous_tab.addItems([""] + self.file_names)

        # Storing the final diction in pickle format(python binary file format), so that loading of the file is possible.
        with open(f"{self.LE_file_path.text()[:-4]}.pickle", "wb") as outfile:
            pickle.dump(self.files_data_dict[filename], outfile)
            print("Pickle file generated to load later after this session")

        self.showMessage()
        return

    def load_file(self):
        """
        Method used to load a pre-computed file directly, so that computation time and hassle is avoided.
        """
        dlg = QtWidgets.QFileDialog(self)
        # Change the path appropriately, the path you give will be the location where the pop-up window will start from,
        # default is C:/ (User will have to traverse multiple folders each time to select the file)
        self.file_path = dlg.getOpenFileName(self, 'Choose directory',
                                             r"C:\Users\dixit\OneDrive\Desktop\Ajey\Project\AFAS_dec2023\Mumbai Data\Oct12_2020_COMTRADE_Mumbai_Blackout\Unit 7 GRP",
                                             filter="Pickle (*.pickle)")[0]

        self.LE_file_path.setText(self.file_path)
        # Here we are using [:-7] as the loaded file will have ".pickle" extension
        filename = self.LE_file_path.text().split('/')[-1][:-7]

        # Clearing the sets, incase the signal names match the previous loaded file.
        self.LW_voltage_set.clear()
        self.LW_current_set.clear()
        self.LW_attribute_list.clear()

        try:
            # Here the self.files_data_dict dictionary will be populated for the corresponding file.
            with open(f"{self.file_path}", "rb") as infile:
                self.files_data_dict[filename] = pickle.load(infile)

            # Giving the signal particular color depending on color_list
            self.files_data_dict[filename]['plot_color'] = self.color_list[self.color_index]
            self.color_index += 1

            # Tab-1, populating the list of files that have been loaded
            self.number_of_files += 1
            self.label_list_of_files.setText(
                self.label_list_of_files.text() + f"\n\n{self.number_of_files}. {filename}")

            self.file_names = list(self.files_data_dict.keys())  # List of files that have been loaded.

            # Tab-2 default behaviour
            self.groupBox.setEnabled(True)
            self.ComB_list_of_files.clear()
            self.ComB_list_of_files.addItems([""] + self.file_names)

            # Tab-3 combo box
            self.ComB_instantaneous_tab.clear()  # Clearing the previous entries to avoid duplication.
            # Populating with list of files that have been loaded
            self.ComB_instantaneous_tab.addItems([""] + self.file_names)

            self.showMessage()
        except FileNotFoundError as err:
            QtWidgets.QMessageBox.information(self,
                                              "Fail",
                                              "The file doesn't exist, please compute the values before trying to load a file")

    def load_save_state(self):
        dlg = QtWidgets.QFileDialog(self)
        self.file_path = dlg.getExistingDirectory(self, 'Choose directory', r'C:\Users\dixit\OneDrive\Desktop')
        files = os.listdir(self.file_path)

        self.LW_voltage_set.clear()
        self.LW_current_set.clear()
        self.LW_attribute_list.clear()

        for file in files:
            # Here the self.files_data_dict dictionary will be populated for the corresponding file.
            with open(f"{self.file_path}\\{file}", "rb") as infile:
                self.files_data_dict[file] = pickle.load(infile)

            # Giving the signal particular color depending on color_list
            self.files_data_dict[file]['plot_color'] = self.color_list[self.color_index]
            self.color_index += 1

            # Tab-1, populating the list of files that have been loaded
            self.number_of_files += 1
            self.label_list_of_files.setText(
                self.label_list_of_files.text() + f"\n\n{self.number_of_files}. {file}")

        self.file_names = list(self.files_data_dict.keys())  # List of files that have been loaded.

        # Tab-2 default behaviour
        self.groupBox.setEnabled(True)
        self.ComB_list_of_files.clear()
        self.ComB_list_of_files.addItems([""] + self.file_names)

        # Tab-3 combo box
        self.ComB_instantaneous_tab.clear()  # Clearing the previous entries to avoid duplication.
        # Populating with list of files that have been loaded
        self.ComB_instantaneous_tab.addItems([""] + self.file_names)

        self.showMessage()

    def showMessage(self):
        # Helper function, not really required don't remember why I added this LOL
        # TO remove this function, just copy-paste the content where showMessage is called.
        QtWidgets.QMessageBox.information(self,
                                          "Success",
                                          "File loaded successfully, you can add more files/proceed to plotting")

    ################################################################################################
    # Tab-2 -> Signal plotting tab:
    ################################################################################################
    def plot_signal(self, ):
        # Calling function depending on the checkbox selected
        if self.CB_voltage_rms.isChecked():
            self.plot_selected_signals(0, "RMS_voltage")
        else:
            self.PW_voltage_rms.clear()

        if self.CB_voltage_rms_dft.isChecked():
            self.plot_selected_signals(1, "DFT voltage RMS")
        else:
            self.PW_voltage_rms_dft.clear()

        if self.CB_current_rms.isChecked():
            self.plot_selected_signals(2, "RMS_current")
        else:
            self.PW_current_rms.clear()

        if self.CB_current_rms_dft.isChecked():
            self.plot_selected_signals(3, "DFT current RMS")
        else:
            self.PW_current_rms_dft.clear()

        if self.CB_frequency.isChecked():
            self.plot_selected_signals(4, "Frequency F_avg")
        else:
            self.PW_frequency.clear()

        if self.CB_impedance.isChecked():
            self.plot_selected_signals(5, "Z (Impedance)")
        else:
            self.PW_impedance.clear()

        if self.CB_real_power.isChecked() and self.CB_reactive_power.isChecked():
            self.PW_power.clear()
            self.plot_selected_signals(6, "Real power")
            self.plot_selected_signals(6, "Reactive power")
        elif self.CB_real_power.isChecked():
            self.PW_power.clear()
            self.plot_selected_signals(6, "Real power")
        elif self.CB_reactive_power.isChecked():
            self.PW_power.clear()
            self.plot_selected_signals(6, "Reactive power")
        else:
            self.PW_power.clear()

        if self.CB_voltage_positive.isChecked() and self.CB_voltage_negative.isChecked() and self.CB_voltage_zero.isChecked():
            self.PW_voltage_seq.clear()
            self.plot_selected_signals(7, "Positive sequence V")
            self.plot_selected_signals(7, "Negative sequence V")
            self.plot_selected_signals(7, "Zero sequence V")
        elif self.CB_voltage_positive.isChecked() and self.CB_voltage_negative.isChecked():
            self.PW_voltage_seq.clear()
            self.plot_selected_signals(7, "Positive sequence V")
            self.plot_selected_signals(7, "Negative sequence V")
        elif self.CB_voltage_zero.isChecked() and self.CB_voltage_negative.isChecked():
            self.PW_voltage_seq.clear()
            self.plot_selected_signals(7, "Negative sequence V")
            self.plot_selected_signals(7, "Zero sequence V")
        elif self.CB_voltage_positive.isChecked() and self.CB_voltage_zero.isChecked():
            self.PW_voltage_seq.clear()
            self.plot_selected_signals(7, "Positive sequence V")
            self.plot_selected_signals(7, "Zero sequence V")
        elif self.CB_voltage_positive.isChecked():
            self.PW_voltage_seq.clear()
            self.plot_selected_signals(7, "Positive sequence V")
        elif self.CB_voltage_negative.isChecked():
            self.PW_voltage_seq.clear()
            self.plot_selected_signals(7, "Negative sequence V")
        elif self.CB_voltage_zero.isChecked():
            self.PW_voltage_seq.clear()
            self.plot_selected_signals(7, "Zero sequence V")
        else:
            self.PW_voltage_seq.clear()

        if self.CB_current_positive.isChecked() and self.CB_current_negative.isChecked() and self.CB_current_zero.isChecked():
            self.PW_current_seq.clear()
            self.plot_selected_signals(8, "Positive sequence I")
            self.plot_selected_signals(8, "Negative sequence I")
            self.plot_selected_signals(8, "Zero sequence I")
        elif self.CB_current_positive.isChecked() and self.CB_current_negative.isChecked():
            self.PW_current_seq.clear()
            self.plot_selected_signals(8, "Positive sequence I")
            self.plot_selected_signals(8, "Negative sequence I")
        elif self.CB_current_zero.isChecked() and self.CB_current_negative.isChecked():
            self.PW_current_seq.clear()
            self.plot_selected_signals(8, "Negative sequence I")
            self.plot_selected_signals(8, "Zero sequence I")
        elif self.CB_current_positive.isChecked() and self.CB_current_zero.isChecked():
            self.PW_current_seq.clear()
            self.plot_selected_signals(8, "Positive sequence I")
            self.plot_selected_signals(8, "Zero sequence I")
        elif self.CB_current_positive.isChecked():
            self.PW_current_seq.clear()
            self.plot_selected_signals(8, "Positive sequence I")
        elif self.CB_current_negative.isChecked():
            self.PW_current_seq.clear()
            self.plot_selected_signals(8, "Negative sequence I")
        elif self.CB_current_zero.isChecked():
            self.PW_current_seq.clear()
            self.plot_selected_signals(8, "Zero sequence I")
        else:
            self.PW_current_seq.clear()

    def plot_selected_signals(self, plotIndex, signal):
        """
        Helper function, which is actually plotting all the plots that are required.
        All the parameters are being called appropriately in "plot_signal" method.
        """
        if plotIndex in [0, 1, 2, 3, 4, 5]:
            self.tab2_plots[plotIndex].clear()
        self.tab2_plots[plotIndex].addLegend(offset=(350, 8))

        # Looping through all files and plotting.
        for file in self.file_names:
            pen = pg.mkPen(color=self.files_data_dict[file]['plot_color'], width=1.5)
            for column in [item for item in self.files_data_dict[file]['data'].keys() if item.startswith(signal)]:
                # This conditional is required because Sequence transform required plotting the absolute value of the signal.
                if plotIndex in [7, 8]:
                    self.tab2_plots[plotIndex].plot(
                        self.files_data_dict[file]['data']["Time"] + self.files_data_dict[file]['shift_values']['x'],
                        np.abs(self.files_data_dict[file]['data'][column] + self.files_data_dict[file]['shift_values'][
                            column]) *
                        self.files_data_dict[file]['scaling_values'][column],
                        pen=pen, name=file + f"_{column}")
                else:
                    self.tab2_plots[plotIndex].plot(
                        self.files_data_dict[file]['data']["Time"] + self.files_data_dict[file]['shift_values']['x'],
                        (self.files_data_dict[file]['data'][column] + self.files_data_dict[file]['shift_values'][
                            column]) *
                        self.files_data_dict[file]['scaling_values'][column],
                        pen=pen, name=file + f"_{column}")

    def move_horizontal(self, direction=1):
        """
        Method used to shift the signals left/right manually for alignment.
        :param direction: -1 to move left, +1 to move right
        """
        try:
            if self.LE_shift_value.text() == "":
                QtWidgets.QMessageBox.information(self,
                                                  "Error",
                                                  "Enter a valid shift value")
                return
            shift = direction * float(self.LE_shift_value.text())
            new_val = round(float(self.x_shift_value.text()) + shift, 4)
            self.x_shift_value.setText(str(new_val))

            self.files_data_dict[self.ComB_list_of_files.currentText()]['shift_values']['x'] += shift
            self.plot_signal()

        except KeyError as err:
            QtWidgets.QMessageBox.information(self,
                                              "Error",
                                              "Please select a file to shift.")

    def move_vertical(self, direction=1):
        """
        Method used to shift the signals up/down manually for alignment.
        :param direction: +1 to move signal up, -1 to move signal down
        """
        try:
            if self.LE_shift_value.text() == "":
                QtWidgets.QMessageBox.information(self,
                                                  "Error",
                                                  "Enter a valid shift value")
                return

            shift = direction * float(self.LE_shift_value.text())
            new_val = float(self.y_shift_value.text()) + shift
            self.y_shift_value.setText(str(new_val))

            self.files_data_dict[self.ComB_list_of_files.currentText()]['shift_values'][
                self.ComB_signals_list.currentText()] += float(self.y_shift_value.text())
            self.plot_signal()

        except KeyError as err:
            QtWidgets.QMessageBox.information(self,
                                              "Error",
                                              "Please select a file to shift.")

    def scale_signal(self):
        """
        Method used for scaling the selected signal of a particular file by some factor.
        """
        try:
            if self.current_scale.text() == "":
                QtWidgets.QMessageBox.information(self,
                                                  "Error",
                                                  "Enter a valid shift value")
                return

            self.current_scale.setText(str(float(self.current_scale.text()) * float(self.LE_scaling_factor.text())))
            value = float(self.current_scale.text())

            self.files_data_dict[self.ComB_list_of_files.currentText()]['scaling_values'][
                self.ComB_signals_list.currentText()] = value

            self.plot_signal()

        except KeyError as err:
            QtWidgets.QMessageBox.information(self,
                                              "Error",
                                              "Please select a file to shift.")

    def load_signals(self):  # Populating the signals in combobox depending on the file selected
        filename = self.ComB_list_of_files.currentText()
        self.x_shift_value.setText('0')
        self.ComB_signals_list.clear()
        if filename != "":
            self.ComB_signals_list.addItems([""] + list(self.files_data_dict[filename]['shift_values'].keys())[:-1])

    def hide_gb1(self):
        # Method to collapse the plot-selection area (Not really required, but logic can be used in different UIs)
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
        # Method to save the current visual state of the plots, to avoid aligning the signals everytime.
        directory_name = time.strftime('%d-%m-%Y %H-%M-%S',
                                       time.localtime())  # You can change the format of the directory name here!
        if not os.path.exists(rf'C:\Users\dixit\OneDrive\Desktop\Folder_forGUI\pickle files\{directory_name}'):
            os.makedirs(rf'C:\Users\dixit\OneDrive\Desktop\Folder_forGUI\pickle files\{directory_name}')

        for filename in self.file_names:
            with open(fr"C:\Users\dixit\OneDrive\Desktop\Folder_forGUI\pickle files\{directory_name}\{filename}.pickle",
                      "wb") as outfile:
                pickle.dump(self.files_data_dict[filename], outfile)
                print("Pickle file generated to load later after this session")

        QtWidgets.QMessageBox.information(self,
                                          "Success",
                                          "The current state has been saved, so you can continue from here!")

    #################################################################################################
    #  Tab-3 -> Instantaneous plots tab:
    #################################################################################################
    def plot_instantaneous(self):
        """
        Method to plot the 3 phase instantaneous signals, for each file, each set.
        """
        file = self.ComB_instantaneous_tab.currentText()

        if file == "":
            QtWidgets.QMessageBox.information(self,
                                              "Error",
                                              "Please select a file to shift.")
            return

        if file not in self.plotted_plot:
            self.plotted_plot.append(file)  # Adding the file to list
            # Creating a dictionary, which will store the plots and layouts corresponding to each file.
            if file not in self.plot_dict.keys():
                self.plot_dict[file] = {"plots": [],
                                        "h_layout": []}

            # Calculating how many sets are present for the file
            num_of_sets = max(len([item for item in self.files_data_dict[file]['data'].keys() if item.startswith("V")]),
                              len([item for item in self.files_data_dict[file]['data'].keys() if
                                   item.startswith("I")])) // 3

            for val in range(num_of_sets):
                layout = QtWidgets.QHBoxLayout()  # Creating a new horizontal layout which will store Voltage and Current plot of a set

                # Creating plot for voltage signals
                plot = pg.PlotWidget()
                # Default settings
                plot.addLegend(offset=(280, 8))
                plot.setMinimumSize(480, 250)
                plot.setMaximumSize(550, 280)

                # If in any case the number of sets are more than 3 (more than 3 voltage/current sets) then the 3 here needs to changed accordingly
                colors = ['r', 'y', 'b'] * 3  # => ['r', 'y', 'b', 'r', 'y', 'b', 'r', 'y', 'b']

                color_count = 0
                for column in [item for item in self.files_data_dict[file]['data'].keys() if
                               item.startswith("V") and item.endswith(str(val + 1))]:
                    pen = pg.mkPen(color=colors[color_count], width=1.5)
                    plot.plot(
                        self.files_data_dict[file]['data']["Time"] + self.files_data_dict[file]['shift_values']['x'],
                        self.files_data_dict[file]['data'][column] + self.files_data_dict[file]['shift_values'][column],
                        pen=pen, name=file + f"_{column}")
                    color_count += 1

                layout.addWidget(plot)  # Adding the voltage plot to horizontal layout
                self.plot_dict[file]['plots'] += [plot]  # Adding the plot object to dictionary

                # Similarly for current instantaneous
                plot = pg.PlotWidget()
                plot.addLegend(offset=(280, 8))
                plot.setMinimumSize(480, 250)
                plot.setMaximumSize(550, 280)
                color_count = 0

                for column in [item for item in self.files_data_dict[file]['data'].keys() if
                               item.startswith("I") and item.endswith(str(val + 1))]:
                    pen = pg.mkPen(color=colors[color_count], width=1.5)
                    plot.plot(
                        self.files_data_dict[file]['data']["Time"] + self.files_data_dict[file]['shift_values']['x'],
                        self.files_data_dict[file]['data'][column] + self.files_data_dict[file]['shift_values'][column],
                        pen=pen, name=file + f"_{column}")
                    color_count += 1

                layout.addWidget(plot)  # Adding the current plot to the horizontal layout
                self.plot_dict[file]['plots'] += [plot]  # Adding the plot object to the dictionary
                self.plot_dict[file]["h_layout"] += [layout]  # Adding the horizontal layout object to the dictionary

                # Adding the complete horizontal layout which contains the voltage, current plot to the vertical layout.
                self.tab3_plot_layout.addLayout(layout)

            # Adding the vertical layout to the scroll area
            scrollContent = QtWidgets.QWidget()
            scrollContent.setLayout(self.tab3_plot_layout)
            self.scroll1.setWidget(scrollContent)

        else:
            QtWidgets.QMessageBox.information(self,
                                              "Error",
                                              "Plots already plotted!")

    def remove_plot_instantaneous(self):
        """
        Removing the plots, horizontal layout corresponding to selected file
        """
        file = self.ComB_instantaneous_tab.currentText()
        if file in self.plotted_plot:
            for h_layout in self.plot_dict[file]["h_layout"]:
                self.tab3_plot_layout.removeItem(h_layout)
            for plot in self.plot_dict[file]['plots']:
                plot.deleteLater()
            # Removing the file from the list (so that it can be added again if required)
            self.plotted_plot.remove(file)
            del self.plot_dict[file]  # Deleting the dictionary due to the above reason.
        else:
            QtWidgets.QMessageBox.information(self,
                                              "Error",
                                              "Plot doesn't exist!")

    #################################################################################################
    #  Tab-4 -> Segmentation tab:
    #################################################################################################
    def calculate_segmentation(self, signal, button):
        """
        Calculates the segments based on the automatically calculated threshold, which uses the formula of [std_dev + 5 * mean]
        To change the default formula you can do so in "segmentation_functions.py" file on line 45
        """
        if button.isChecked():  # Unchecking all checkboxes, and checking the checked checkbox
            self.set_checkboxes_unchecked()
            button.setChecked(True)

        self.PW_signal_segment.clear()
        self.PW_difference_segment.clear()

        self.LE_add_segment_value.clear()
        self.LE_remove_segment_value.clear()
        self.LE_segment_shift_value.clear()

        self.signal_dataItems = {}
        self.difference_dataItems = {}
        self.max_val = [0, 0]
        self.min_val = 0

        self.LE_threshold_value.setText("")

        threshold_pen = pg.mkPen(color=(0, 94, 255),
                                 width=1.5)  # Setting color of threshold signal (horizontal line) in RGB values, can be changed to any other desired color

        self.super_q = {}  # Creating an empty dictionary to store "index" of segments and later will be merging all the timestamps to 1 variable

        for file in self.file_names:
            pen = pg.mkPen(color=self.files_data_dict[file]['plot_color'], width=1.5)
            for column in [item for item in self.files_data_dict[file]['data'].keys() if item.startswith(signal)]:
                self.q, self.z1, self.threshold = segment_function.segmentation_trendfilter(
                    self.files_data_dict[file]['data']["Time"] + self.files_data_dict[file]['shift_values']['x'],
                    self.files_data_dict[file]['data'][column] + self.files_data_dict[file]['shift_values'][column])

                self.super_q[file] = [val for val in self.q]

                signal_ = self.files_data_dict[file]['data'][column] + self.files_data_dict[file]['shift_values'][
                    column]

                self.max_val[0] = max(signal_) if self.max_val[0] < max(signal_) else self.max_val[0]
                self.max_val[1] = max(self.z1) if self.max_val[1] < max(self.z1) else self.max_val[1]
                self.min_val = min(signal_) if min(signal_) < self.min_val else self.min_val

                self.signal_dataItems[file + f"_{column}"] = pg.PlotDataItem(
                    self.files_data_dict[file]['data']["Time"] + self.files_data_dict[file]['shift_values']['x'],
                    (self.files_data_dict[file]['data'][column] + self.files_data_dict[file]['shift_values'][column]) *
                    self.files_data_dict[file]['scaling_values'][column], pen=pen, name=file + f"_{column}")

                self.difference_dataItems[file + f"_{column}"] = pg.PlotDataItem(
                    self.files_data_dict[file]['data']["Time"] + self.files_data_dict[file]['shift_values']['x'],
                    self.z1, pen=pen)

                self.PW_difference_segment.plot(
                    self.files_data_dict[file]['data']["Time"] + self.files_data_dict[file]['shift_values']['x'],
                    [self.threshold] * len(
                        self.files_data_dict[file]['data']["Time"] + self.files_data_dict[file]['shift_values']['x']),
                    pen=threshold_pen)

        self.merge_segments()
        self.plot_segmentation()

        if not any([button.isChecked() for button in self.tab_3.findChildren(QtWidgets.QCheckBox)]):
            self.PW_signal_segment.clear()
            self.PW_difference_segment.clear()

    def calculate_manual_segmentation(self, signal):
        """
        Calculates the segments based on the user given threshold value
        """
        self.PW_signal_segment.clear()
        self.PW_difference_segment.clear()
        self.LE_segment_shift_value.setText("")

        threshold_pen = pg.mkPen(color=(0, 94, 255), width=1.5)
        self.threshold = float(self.LE_threshold_value.text())  # Reading the user provided threshold value

        for file in self.file_names:
            pen = pg.mkPen(color=self.files_data_dict[file]['plot_color'], width=1.5)
            for column in [item for item in self.files_data_dict[file]['data'].keys() if item.startswith(signal)]:
                self.q, self.z1 = segment_function.manual_segmentation_trendfilter(
                    self.files_data_dict[file]['data']["Time"] + self.files_data_dict[file]['shift_values']['x'],
                    self.files_data_dict[file]['data'][column] + self.files_data_dict[file]['shift_values'][column],
                    self.threshold
                )
                signal_ = self.files_data_dict[file]['data'][column] + self.files_data_dict[file]['shift_values'][
                    column]
                self.super_q[file] = self.q
                self.max_val[0] = max(signal_) if self.max_val[0] < max(signal_) else self.max_val[0]
                self.max_val[1] = max(self.z1) if self.max_val[1] < max(self.z1) else self.max_val[1]

                self.PW_difference_segment.plot(
                    self.files_data_dict[file]['data']["Time"] + self.files_data_dict[file]['shift_values']['x'],
                    [self.threshold] * len(
                        self.files_data_dict[file]['data']["Time"] + self.files_data_dict[file]['shift_values']['x']),
                    pen=threshold_pen)

            self.merge_segments()
            self.plot_segmentation()

    def plot_segmentation(self):
        """
        Once the values required for segmentation are calculated, the plotting the same of both, this function just uses the above calculated values
        and plots them appropriately
        """
        segment_pen = pg.mkPen(color=(255, 255, 0),
                               width=1.5)  # Setting color of the actual segments we will be seeing (vertical lines) in RGB values

        self.PW_signal_segment.addLegend(offset=(350, 8))
        self.PW_difference_segment.addLegend(offset=(350, 8))

        # Adding the segments dataItem to the dictionary, so that plotting/adding/deleting the segments will be easy later on
        if self.segments is not None:
            for i in range(len(self.segments)):
                self.signal_dataItems[f"segment {i + 1}"] = pg.PlotDataItem([self.segments[i]] * 3,
                                                                            [self.min_val, 0, self.max_val[0]],
                                                                            pen=segment_pen)
                self.difference_dataItems[f"segment {i + 1}"] = pg.PlotDataItem([self.segments[i]] * 3,
                                                                                [0, 0, self.max_val[1]],
                                                                                pen=segment_pen)
            self.ComB_segment_selection.clear()
            # Updating the combobox
            self.ComB_segment_selection.addItems([""] + [str(val + 1) for val in range(len(self.segments))])

        # Plotting all the signals by looping over the dictionary
        for key in self.signal_dataItems.keys():
            self.PW_signal_segment.addItem(self.signal_dataItems[key])
            self.PW_difference_segment.addItem(self.difference_dataItems[key])

    def manual_segmentation(self):
        """
        When performing the manual segmentation, we call for this function which in turn calls the helper function written above
        with the appropriate arguments depending on the checkbox which is checked.
        """
        if self.CB_segment_voltage.isChecked():
            self.calculate_manual_segmentation("RMS_voltage")

        elif self.CB_segment_current.isChecked():
            self.calculate_manual_segmentation("RMS_current")

        elif self.CB_segment_frequency.isChecked():
            self.calculate_manual_segmentation("Frequency F_avg")

    def merge_segments(self):
        """
        Method were we collect all the required segments to 1 variable
        """
        self.segments = None
        self.ComB_segment_selection.clear()

        segment_time_stamps = []

        for file in self.super_q.keys():
            if len(self.super_q[file]) == 0:
                continue
            else:
                for segment_indices in (self.super_q[file]):
                    segment_time_stamps.append(
                        self.files_data_dict[file]['data']['Time'][segment_indices[0]] +
                        self.files_data_dict[file]['shift_values'][
                            'x'])  # Appending the starting value
                    segment_time_stamps.append(
                        self.files_data_dict[file]['data']['Time'][segment_indices[-1]] +
                        self.files_data_dict[file]['shift_values'][
                            'x'])  # Appending the ending value

        if len(segment_time_stamps) == 0:
            return

        self.segments = sorted(segment_time_stamps)

        output_list = []
        prev_value = None
        for value in self.segments:
            if prev_value is None or abs(value - prev_value) >= 0.02:  # Removing the segments which are too close to each other (redundant segments)
                output_list.append(value)
                prev_value = value

        self.segments = output_list
        self.ComB_segment_selection.addItems([""] + [str(val + 1) for val in range(len(self.segments))])

    def add_segments(self):
        segments_to_add = eval(self.LE_add_segment_value.text())
        if type(segments_to_add) in [float, int]:
            segments_to_add = [segments_to_add]

        max_dur = 0
        max_file = None
        # Searching the file with max length (All the segments will be plotted wrt this file's signals)
        for file in self.file_names:
            max_time = max(self.files_data_dict[file]['data']['Time'])
            if max_time > max_dur:
                max_dur = max_time
                max_file = file

        # Rounding the "Time" signal so that when adding new segments we can search for the index corresponding to that timestamp
        time_rounded = list(np.around(
            np.array(
                self.files_data_dict[max_file]['data']["Time"] + self.files_data_dict[max_file]['shift_values']['x']),
            2))

        if self.segments is None:
            self.segments = []

        # Appending the newly added values to the "self.segments" variables which stores all the segment timestamps.
        for time_value in segments_to_add:
            try:
                self.segments.append(self.files_data_dict[max_file]['data']["Time"][time_rounded.index(time_value)])
            except ValueError as err:
                print(f'Please change time to add, the step size is {time_rounded[1] - time_rounded[0]}')
                return

        self.segments = sorted(list(set(self.segments)))
        keys = [val for val in self.signal_dataItems.keys() if val.startswith("segment")]

        # Removing the previous segments (Otherwise the naming will clash)
        for val in keys:
            self.PW_signal_segment.removeItem(self.signal_dataItems[val])
            del self.signal_dataItems[val]

            self.PW_difference_segment.removeItem(self.difference_dataItems[val])
            del self.difference_dataItems[val]

        # Plotting all the signals again
        self.plot_segmentation()

    def delete_segments(self):
        segments_remove = np.array(eval(self.LE_remove_segment_value.text())) - 1
        if type(segments_remove) in [float, int, numpy.int32]:
            segments_remove = [segments_remove]

        # Storing all the segments to remove to a list so that we can remove them by looping over them
        keys = []
        for i in segments_remove:
            keys.append(f"segment {i + 1}")
            self.segments[i] = None
            self.ComB_segment_selection.removeItem(self.ComB_segment_selection.findText(str(i)))

        # Updating the timestamp list
        self.segments = [val for val in self.segments if val is not None]

        # Removing the desired segments
        for val in keys:
            self.PW_signal_segment.removeItem(self.signal_dataItems[val])
            del self.signal_dataItems[val]

            self.PW_difference_segment.removeItem(self.difference_dataItems[val])
            del self.difference_dataItems[val]

        # Renaming all the segments to avoid any type of bug
        key = [v for v in self.signal_dataItems.keys() if v.startswith("segment")]
        for v, new_key in zip(list(key), list(range(len(self.segments)))):
            self.signal_dataItems[f"segment {new_key + 1}"] = self.signal_dataItems.pop(v)
            self.difference_dataItems[f"segment {new_key + 1}"] = self.difference_dataItems.pop(v)

        self.ComB_segment_selection.clear()
        self.ComB_segment_selection.addItems([""] + [str(val + 1) for val in range(len(self.segments))])

    def shift_segment(self, direction=1):
        """
        Similar to move_horizontal, please refer that if any doubt
        """
        if self.LE_segment_shift_value.text() == "":
            QtWidgets.QMessageBox.information(self,
                                              "Error",
                                              "Enter a valid shift value")
            return

        segment_to_shift = int(self.ComB_segment_selection.currentText()) - 1
        shift_value = direction * float(self.LE_segment_shift_value.text())

        self.segments[segment_to_shift] += shift_value
        self.plot_shifted_segments(segment_to_shift)

    def plot_shifted_segments(self, segment_num):
        segment_pen = pg.mkPen(color=(255, 255, 0), width=1.5)
        key = f"segment {segment_num + 1}"

        # Removing the old segments plotItems
        self.PW_signal_segment.removeItem(self.signal_dataItems[key])
        self.PW_difference_segment.removeItem(self.difference_dataItems[key])

        # Adding the new timed segments
        self.signal_dataItems[key] = pg.PlotDataItem(
            [self.segments[segment_num]] * 2, [0, self.max_val[0]], pen=segment_pen)

        self.difference_dataItems[key] = pg.PlotDataItem(
            [self.segments[segment_num]] * 2, [0, self.max_val[1]], pen=segment_pen)

        # Adding the new plot
        self.PW_signal_segment.addItem(self.signal_dataItems[key])
        self.PW_difference_segment.addItem(self.difference_dataItems[key])

    #################################################################################################
    #  Helper/General functions
    #################################################################################################
    def set_checkboxes_unchecked(self):
        """
        Sets the other checkboxes as unchecked, prohibits the user from selecting more than 1 check boxes when it is not allowed.
        """
        for edit in self.tab_3.findChildren(QtWidgets.QCheckBox):
            edit.setChecked(False)

    def load_tooltips(self):
        """
        No changes/alterations need to made here, only change if you want to add some new tooltips, make sure to change the tooltip duration using the Qt Designer.
        """
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
        self.TT_add_segments.setToolTip("Add segments at some time instance. (Comma separated)\n"
                                        "Eg: 0.1, 0.3, 0.7")
        self.TT_remove_segments.setToolTip("Remove any redundant/wrong segment based on the segment number. (Comma separated)\n"
                                           "Eg: 1, 3, 4")


class DeselectableTreeView(
    QtWidgets.QListWidget):  # Class to de-select the selection in the list widgets in Tab-1 (To avoid unnecessary removal of items)
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
