import os
from datetime import datetime

import pandas as pd
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableView, QComboBox, QFileDialog, QMessageBox,
    QInputDialog, QMenu, QDialog, QToolBar
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QPoint

# Services and UI imports
from services.settings_service import get_email_account, get_resume_folder
from ui.settings_dialog import SettingsDialog
from ui.data_frame_model import DataFrameModel
from ui.compose_email_dialog import ComposeEmailDialog
from services.file_service import load_data, save_data
from transformations.utils import find_transformations_in_package
from transformations.manager import TransformationManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Spreadsheet (PyQt) - AutoSave & Timestamp")
        self.resize(1100, 700)

        # Track if a file is loaded/created
        self.current_file_path = None

        # DataFrame model
        self.df_model = DataFrameModel(pd.DataFrame())

        # Transformation manager (set when a file is loaded)
        self.trans_manager = None

        # Discover transformations
        self.transformations_dict = find_transformations_in_package("transformations")

        # Build UI immediately so it’s visible
        self.init_ui()

        # After building UI, load/check user settings
        self.load_user_settings()

    def init_ui(self):
        """
        Initialize the main UI elements: toolbar, table, transformations row, etc.
        """
        # ========== TOOLBAR ==========
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        settings_action = QAction("Preferences", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        toolbar.addAction(settings_action)

        # ========== CENTRAL WIDGET & LAYOUT ==========
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # Top row of buttons
        top_btn_layout = QHBoxLayout()

        self.load_button = QPushButton("Load File (CSV/XLS/XLSX)")
        self.load_button.clicked.connect(self.load_file_dialog)
        top_btn_layout.addWidget(self.load_button)

        self.create_save_button = QPushButton("Create New")
        self.create_save_button.clicked.connect(self.on_create_save_clicked)
        top_btn_layout.addWidget(self.create_save_button)

        main_layout.addLayout(top_btn_layout)

        # Table View
        self.table_view = QTableView()
        self.table_view.setModel(self.df_model)
        main_layout.addWidget(self.table_view, stretch=1)

        # Enable context menus on header and table
        header = self.table_view.horizontalHeader()
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self.on_header_context_menu)

        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_table_context_menu)

        # Add row button
        add_row_layout = QHBoxLayout()
        add_row_btn = QPushButton("Add Row")
        add_row_btn.clicked.connect(self.add_new_row)
        add_row_layout.addWidget(add_row_btn)
        main_layout.addLayout(add_row_layout)

        # Transformation UI
        if self.transformations_dict:
            transformation_layout = QHBoxLayout()
            self.transform_combo = QComboBox()
            self.transform_combo.addItems(self.transformations_dict.keys())
            transformation_layout.addWidget(self.transform_combo)

            apply_transform_button = QPushButton("Apply Transformation")
            apply_transform_button.clicked.connect(self.apply_transformation)
            transformation_layout.addWidget(apply_transform_button)

            main_layout.addLayout(transformation_layout)

        # Auto-save on data change
        self.df_model.dataChanged.connect(self.auto_save)

        self.setCentralWidget(main_widget)

    def load_user_settings(self):
        """
        Check essential settings (like email credentials, resume folder) AFTER UI is loaded.
        Prompt user if missing.
        """
        email_account = get_email_account()
        resume_folder = get_resume_folder()

        if not email_account or not resume_folder:
            msg = (
                "Some essential settings (Email or Resume folder) are missing.\n"
                "Please configure them now."
            )
            result = QMessageBox.warning(self, "Incomplete Setup", msg,
                                         QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            if result == QMessageBox.StandardButton.Ok:
                self.open_settings_dialog()

    # ------------------------------------------------------
    # SETTINGS DIALOG
    # ------------------------------------------------------
    def open_settings_dialog(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            QMessageBox.information(self, "Settings Saved", "Your settings have been updated.")

    # ------------------------------------------------------
    # CREATE NEW vs SAVE FILE button (toggled by file state)
    # ------------------------------------------------------
    def on_create_save_clicked(self):
        """
        If no file is currently loaded, create a new empty CSV.
        Otherwise, manually save (though we are also auto-saving).
        """
        if self.current_file_path is None:
            self.create_new_file_dialog()
        else:
            self.save_current_file()

    def create_new_file_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Create New CSV",
            "",
            "CSV Files (*.csv)"
        )
        if not file_path:
            return  # user canceled

        # Create empty DataFrame with some default columns
        df = pd.DataFrame(columns=["Column1", "Column2"])
        try:
            save_data(df, file_path)  # via services.file_service
            self.df_model.setDataFrame(df)
            self.set_current_file_path(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Error Creating File", str(e))

    def save_current_file(self):
        if not self.current_file_path:
            return
        self.auto_save(force=True)
        QMessageBox.information(self, "Saved", f"File saved to:\n{self.current_file_path}")

    # ------------------------------------------------------
    # LOADING FILES
    # ------------------------------------------------------
    def load_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "All Supported Files (*.csv *.xls *.xlsx);;CSV Files (*.csv);;Excel Files (*.xls *.xlsx)"
        )
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path):
        try:
            df = load_data(file_path)
            self.df_model.setDataFrame(df)
            self.set_current_file_path(file_path)

            # Create or load existing transformation manager for this file
            self.trans_manager = TransformationManager(file_path)

            # Attempt to re-apply transformations (to fill in existing data) 
            new_df = self.trans_manager.apply_all_transformations(df)
            self.df_model.setDataFrame(new_df)

        except Exception as e:
            QMessageBox.critical(self, "Error Loading File", str(e))

    def set_current_file_path(self, path: str):
        self.current_file_path = path
        # Now that a file is loaded, switch button text to "Save File"
        if self.current_file_path:
            self.create_save_button.setText("Save File")
        else:
            self.create_save_button.setText("Create New")

    # ------------------------------------------------------
    # AUTO-SAVE
    # ------------------------------------------------------
    def auto_save(self, *args, force=False):
        """
        Auto-save the current DataFrame if a file is open.
        Also persist transformations metadata.
        """
        if not self.current_file_path:
            return
        try:
            df = self.df_model.dataFrame()
            save_data(df, self.current_file_path)
            # Save metadata if we have a manager
            if self.trans_manager:
                self.trans_manager.save_metadata()
        except Exception as e:
            if force:
                QMessageBox.critical(self, "Auto-Save Error", str(e))

    # ------------------------------------------------------
    # CLOSE EVENT => SAVE TIMESTAMPED CSV
    # ------------------------------------------------------
    def closeEvent(self, event):
        """
        On close, do final backup as CSV, plus save metadata.
        """
        if self.current_file_path:
            df = self.df_model.dataFrame()
            base, _ = os.path.splitext(self.current_file_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_path = f"{base}_{timestamp}.csv"
            try:
                df.to_csv(new_path, index=False)
                print(f"[INFO] Final backup saved to {new_path}")
            except Exception as e:
                print(f"[ERROR] Could not save timestamped file: {e}")

            # Also save transformation metadata
            if self.trans_manager:
                self.trans_manager.save_metadata()

        super().closeEvent(event)

    # ------------------------------------------------------
    # ROW / COLUMN Operations
    # ------------------------------------------------------
    def add_new_row(self):
        row_position = self.df_model.rowCount()
        self.df_model.insertRows(row_position, 1)
        # auto-save triggered via dataChanged signal

    def on_header_context_menu(self, pos: QPoint):
        col_index = self.table_view.horizontalHeader().logicalIndexAt(pos.x())
        if col_index < 0:
            return

        menu = QMenu(self)
        rename_action = menu.addAction("Rename Column")
        delete_action = menu.addAction("Delete Column")
        dtype_action = menu.addAction("Change Data Type")

        action = menu.exec(self.table_view.horizontalHeader().mapToGlobal(pos))
        if action == rename_action:
            self.rename_column(col_index)
        elif action == delete_action:
            self.delete_column(col_index)
        elif action == dtype_action:
            self.change_column_dtype(col_index)

    # ------------------------------------------------------
    # UNIFIED TABLE CONTEXT MENU
    # (Add Column, Send Email, Force Re-Run)
    # ------------------------------------------------------
    def show_table_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        add_column_action = menu.addAction("Add Column")

        index = self.table_view.indexAt(pos)
        if not index.isValid():
            menu.exec(self.table_view.mapToGlobal(pos))
            return

        row_idx = index.row()
        col_idx = index.column()
        df = self.df_model.dataFrame()
        col_name = df.columns[col_idx]

        # If user is right-clicking on a "subject" column,
        # let's offer "Send Email..."
        send_email_action = None
        if "subject" in col_name.lower():
            send_email_action = menu.addAction("Send Email...")

        # Force Re-Run if this column is known as an output_col in metadata
        force_rerun_action = None
        if self.trans_manager and col_name:
            for tid, tmeta in self.trans_manager.get_metadata()["transformations"].items():
                if tmeta["output_col"] == col_name:
                    force_rerun_action = menu.addAction(f"Force Re-Run {tid} on This Row")
                    break

        action = menu.exec(self.table_view.mapToGlobal(pos))

        if action == add_column_action:
            self.add_new_column()
        elif action == send_email_action:
            self.open_compose_dialog_for_row(row_idx)
        elif force_rerun_action and action == force_rerun_action:
            self.force_rerun_for_row(col_name, row_idx)

    def open_compose_dialog_for_row(self, row_idx: int):
        """
        Use the row's data to populate the ComposeEmailDialog.
        """
        df = self.df_model.dataFrame()
        if row_idx < 0 or row_idx >= len(df):
            return

        subject_col = None
        body_col = None
        to_col = None

        for col in df.columns:
            if "subject" in col.lower():
                subject_col = col
            if "body" in col.lower():
                body_col = col
            if "email" in col.lower():
                to_col = col

        subject_val = str(df.at[row_idx, subject_col]) if subject_col else ""
        body_val = str(df.at[row_idx, body_col]) if body_col else ""
        to_val = str(df.at[row_idx, to_col]) if to_col else ""

        dlg = ComposeEmailDialog(
            to_email=to_val,
            subject=subject_val,
            body=body_val,
            parent=self
        )
        if dlg.exec() == QDialog.Accepted:
            # Optionally mark the row as 'sent'
            df.at[row_idx, "SentAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.df_model.setDataFrame(df)
            self.auto_save(force=True)

    def force_rerun_for_row(self, col_name: str, row_idx: int):
        """
        Force re-run for the row if the column is recognized as an output_col.
        """
        df = self.df_model.dataFrame()
        for tid, tmeta in self.trans_manager.get_metadata()["transformations"].items():
            if tmeta["output_col"] == col_name:
                new_df = self.trans_manager.force_rerun_transformation(df, tid, row_idx)
                self.df_model.setDataFrame(new_df)
                QMessageBox.information(
                    self,
                    "Success",
                    f"Forcibly re-ran '{tid}' on row {row_idx}."
                )
                self.auto_save(force=True)
                break

    def add_new_column(self):
        new_name, ok = QInputDialog.getText(
            self, "Add Column", "Enter name for the new column:"
        )
        if ok and new_name.strip():
            try:
                self.df_model.insertColumn(new_name.strip())
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not add column:\n{e}")

    def rename_column(self, col_index):
        df = self.df_model.dataFrame()
        old_name = df.columns[col_index]
        new_name, ok = QInputDialog.getText(
            self, "Rename Column", f"Enter a new name for '{old_name}':"
        )
        if ok and new_name.strip():
            self.df_model.renameColumn(col_index, new_name.strip())

    def delete_column(self, col_index):
        df = self.df_model.dataFrame()
        col_name = df.columns[col_index]
        reply = QMessageBox.question(
            self,
            "Delete Column",
            f"Are you sure you want to delete column '{col_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.df_model.removeColumn(col_index)

    def change_column_dtype(self, col_index):
        dtype_options = ["str", "int", "float", "bool", "datetime64[ns]"]
        chosen_dtype, ok = QInputDialog.getItem(
            self,
            "Change Data Type",
            "Select new data type:",
            dtype_options,
            0,
            editable=False
        )
        if ok and chosen_dtype:
            try:
                self.df_model.changeColumnDtype(col_index, chosen_dtype)
            except Exception as e:
                QMessageBox.critical(self, "Error Changing DType", str(e))

    # ------------------------------------------------------
    # TRANSFORMATIONS
    # ------------------------------------------------------
    def apply_transformation(self):
        if not self.trans_manager:
            QMessageBox.warning(self, "No File", "Load a file first.")
            return

        if not self.trans_manager.transformations_dict:
            QMessageBox.information(self, "Info", "No transformations found in package.")
            return

        df = self.df_model.dataFrame()
        if df.empty:
            QMessageBox.information(self, "Info", "DataFrame is empty; cannot apply transformation.")
            return

        transform_name = self.transform_combo.currentText()
        transformation = self.trans_manager.transformations_dict[transform_name]

        # Ask user for input columns
        required_inputs = transformation.required_inputs()
        chosen_cols = []
        for label in required_inputs:
            col_list = df.columns.tolist()
            if not col_list:
                QMessageBox.warning(self, "Error", f"No columns available for '{label}'.")
                return
            col, ok = QInputDialog.getItem(
                self, "Select Column", f"Column for '{label}':", col_list, 0, False
            )
            if not ok:
                return
            chosen_cols.append(col)

        # Ask user for output column name
        output_col, ok2 = QInputDialog.getText(
            self, "Output Column", "New Column Name:", text="new_column"
        )
        if not ok2 or not output_col:
            return

        # Optional condition expression
        condition_str, ok3 = QInputDialog.getText(
            self,
            "Condition",
            "Enter a pandas condition (e.g. df['Email'].notnull()):",
            text="df['Email'].notnull()"
        )
        if not ok3:
            return

        # Transform ID
        transform_id, ok4 = QInputDialog.getText(
            self, "Transform ID", "Give an ID for this transformation:", text="Enrich1"
        )
        if not ok4 or not transform_id.strip():
            return

        # Register transformation in the manager metadata
        self.trans_manager.add_transformation(
            transform_id=transform_id.strip(),
            transformation_name=transform_name,
            input_cols=chosen_cols,
            output_col=output_col.strip(),
            condition_str=condition_str.strip()
        )

        # Now apply it, which will run or skip rows as needed
        new_df = self.trans_manager.apply_all_transformations(df)
        self.df_model.setDataFrame(new_df)

        QMessageBox.information(
            self, "Success",
            f"Transformation '{transform_id}' applied. Check new column '{output_col}'."
        )
        self.auto_save(force=True)
