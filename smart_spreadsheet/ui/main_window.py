import os
from datetime import datetime

import pandas as pd
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableView, QComboBox, QFileDialog, QMessageBox,
    QInputDialog, QMenu, QDialog, QToolBar, QLineEdit,
)
from services.settings_service import get_email_account, get_resume_folder
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import QMainWindow, QMessageBox
from ui.settings_dialog import SettingsDialog
from ui.data_frame_model import DataFrameModel
from ui.compose_email_dialog import ComposeEmailDialog
from services.file_service import load_data, save_data
from transformations.utils import find_transformations_in_package
# from ui.transform_dialog import TransformDialog  # For future multi-column support
from transformations.manager import TransformationManager
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Spreadsheet (PyQt) - AutoSave & Timestamp")
        self.resize(1100, 700)
        self._init_menubar()
        self.load_user_settings()
        self.init_ui()
    def init_ui(self):
        """
        Initialize UI elements such as toolbar buttons.
        """
        main_widget = QWidget()
        layout = QVBoxLayout()
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        settings_action = QAction("Preferences", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        toolbar.addAction(settings_action)
        # # Add a single-click settings button at the top
        # self.settings_button = QPushButton("Settings")
        # self.settings_button.clicked.connect(self.open_settings_dialog)
        # layout.addWidget(self.settings_button)

        # Add other widgets here (TableView, etc.)
        self.setCentralWidget(main_widget)
        main_widget.setLayout(layout)

    def load_user_settings(self):
        """
        Automatically load settings on startup and check for necessary values.
        """
        email_account = get_email_account()
        resume_folder = get_resume_folder()

        if not email_account or not resume_folder:
            QMessageBox.warning(
                self, 
                "Incomplete Setup",
                "Please complete your settings before using the application."
            )
            self.open_settings_dialog()

    def _init_menubar(self):
        menubar = self.menuBar()

        open_settings_action = QAction("Preferences", self)
        open_settings_action.triggered.connect(self.open_settings_dialog)

    def open_settings_dialog(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            QMessageBox.information(self, "Settings Saved", "Your settings have been updated.")
        # Track if a file is loaded/created
        self.current_file_path = None

        # Initialize DataFrame model
        self.df_model = DataFrameModel(pd.DataFrame())
        # The transformation manager will be set once we have a file loaded
        self.trans_manager = None
        # Load transformations
        self.transformations_dict = find_transformations_in_package("transformations")

        # Main layout
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        self.setCentralWidget(widget)

        # Top row of buttons
        top_btn_layout = QHBoxLayout()

        self.load_button = QPushButton("Load File (CSV/XLS/XLSX)")
        self.load_button.clicked.connect(self.load_file_dialog)
        top_btn_layout.addWidget(self.load_button)

        self.create_save_button = QPushButton("Create New")
        self.create_save_button.clicked.connect(self.on_create_save_clicked)
        top_btn_layout.addWidget(self.create_save_button)

        main_layout.addLayout(top_btn_layout)

        # Table
        self.table_view = QTableView()
        self.table_view.setModel(self.df_model)
        main_layout.addWidget(self.table_view, stretch=1)

        # Column header context menu
        header = self.table_view.horizontalHeader()
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self.on_header_context_menu)

        # Table view context menu
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
        # auto-save is triggered via dataChanged

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

        # We'll guess if the user is right-clicking on a "subject" or "body" column
        # then we can do "Send Email"
        send_email_action = None
        # Alternatively, if you only want to show "Send Email" for subject columns:
        if "subject" in col_name.lower():
            send_email_action = menu.addAction("Send Email...")

        action = menu.exec(self.table_view.mapToGlobal(pos))

        if action == add_column_action:
            self.add_new_column()
        elif action == send_email_action:
            self.open_compose_dialog_for_row(row_idx)
    def open_compose_dialog_for_row(self, row_idx: int):
        """
        Use the row's data to populate the ComposeEmailDialog.
        """
        df = self.df_model.dataFrame()

        if row_idx < 0 or row_idx >= len(df):
            return

        # Example: find columns named "draft_subject", "draft_body", "Email"
        # or use whatever naming scheme you have
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

        # Get the row values
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

        transform_name = self.transform_combo.currentText()
        transformation = self.trans_manager.transformations_dict[transform_name]

        df = self.df_model.dataFrame()
        if df.empty:
            QMessageBox.information(self, "Info", "DataFrame is empty; cannot apply transformation.")
            return

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
        output_col, ok2 = QInputDialog.getText(self, "Output Column", "New Column Name:", text="new_column")
        if not ok2 or not output_col:
            return

        # Ask user for condition expression (optional)
        condition_str, ok3 = QInputDialog.getText(
            self,
            "Condition",
            "Enter a pandas condition (e.g. df['Email'].notnull()):",
            text="df['Email'].notnull()"
        )
        if not ok3:
            return

        # Let user pick an ID for this transformation (or auto-generate)
        transform_id, ok4 = QInputDialog.getText(self, "Transform ID", "Give an ID for this transformation:", text="Enrich1")
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

        QMessageBox.information(self, "Success", f"Transformation '{transform_id}' applied. Check new column '{output_col}'.")
        self.auto_save(force=True)

    # ------------------------------------------------------
    # Right-click context menu: Force Re-Run on a single cell
    # ------------------------------------------------------
    def show_table_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        add_column_action = menu.addAction("Add Column")

        # We'll add a "Force Re-Run" only if user clicks on a cell in an enrichment col
        index = self.table_view.indexAt(pos)
        col_index = index.column()

        col_name = None
        if col_index >= 0:
            col_name = self.df_model.dataFrame().columns[col_index]

        force_rerun_action = None
        if col_name:
            # Check if this column is an output_col in any transformation
            # We store these in the manager's metadata
            for tid, tmeta in self.trans_manager.get_metadata()["transformations"].items():
                if tmeta["output_col"] == col_name:
                    force_rerun_action = menu.addAction(f"Force Re-Run {tid} on This Row")
                    break

        action = menu.exec(self.table_view.mapToGlobal(pos))

        if action == add_column_action:
            self.add_new_column()
        elif force_rerun_action and action == force_rerun_action:
            # Force re-run for the row
            row_idx = index.row()
            df = self.df_model.dataFrame()

            # Find which transform_id matched
            for tid, tmeta in self.trans_manager.get_metadata()["transformations"].items():
                if tmeta["output_col"] == col_name:
                    # This is the one
                    new_df = self.trans_manager.force_rerun_transformation(df, tid, row_idx)
                    self.df_model.setDataFrame(new_df)
                    QMessageBox.information(self, "Success", f"Forcibly re-ran '{tid}' on row {row_idx}.")
                    self.auto_save(force=True)
                    break