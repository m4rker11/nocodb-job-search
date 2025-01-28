import os
from datetime import datetime
from ui.application_status_delegate import ApplicationStatusDelegate
import pandas as pd
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableView, QComboBox, QFileDialog, QMessageBox,
    QInputDialog, QMenu, QDialog, QToolBar, QSplitter, QTextEdit,
)
import re
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtCore import Qt, QPoint, QModelIndex, QTimer
from ui.compose_email_dialog import ComposeEmailDialog
from datetime import datetime
# Services and UI imports
from services.settings_service import get_email_account, get_resume_text
from ui.settings_dialog import SettingsDialog
from ui.data_frame_model import DataFrameModel
from ui.column_row_delegate import ColumnRoleDelegate
from ui.run_row_delegate import RunRowDelegate
from ui.compose_email_dialog import ComposeEmailDialog
from ui.transform_dialog import TransformDialog
from services.file_service import load_data, save_data
from transformations.utils import find_transformations_in_package
from transformations.manager import TransformationManager
from ui.transformation_header import TransformationHeader
from services.email_service import extract_email_address, load_incoming_emails_last_24h


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
        self.init_headers()
        self.processing_rows = set()
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
        self.add_row_action = QAction("Add Row", self)
        self.add_row_action.triggered.connect(self.add_new_row)
        toolbar.addAction(self.add_row_action)
        self.add_row_action.setVisible(False)  # Start hidd

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

        # Splitter for table and reading area
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.current_edit_index = QModelIndex()

        # Table View
        self.table_view = QTableView()
        self.table_view.setModel(self.df_model)

        # Initialize header with role-checking function
        self.header = TransformationHeader(
            get_column_role=self.get_column_role,  # Pass the method
            parent=self.table_view
        )
        self.table_view.setHorizontalHeader(self.header)
        self.table_view.setItemDelegate(ColumnRoleDelegate(get_column_role=self.get_column_role, parent=self.table_view))
        if "Application_Status" in self.df_model.dataFrame().columns:
            self.table_view.setItemDelegateForColumn(
                self.df_model.dataFrame().columns.get_loc("Application_Status"),
                ApplicationStatusDelegate(self.table_view)
            )
        self.splitter.addWidget(self.table_view)

        # Reading Area
        self.reading_area = QTextEdit()
        self.reading_area.setMinimumHeight(150)  # About 7 rows tall
        self.reading_area.textChanged.connect(self.update_cell_from_reading_area)
        self.reading_area.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border-top: 2px solid #dee2e6;
                font-family: monospace;
                padding: 8px;
            }
        """)
        self.splitter.addWidget(self.reading_area)

        # Set initial splitter sizes (75% table, 25% reading area)
        self.splitter.setSizes([self.height() * 3 // 4, self.height() // 4])
        main_layout.addWidget(self.splitter)

        # Enable context menus on header and table
        header = self.table_view.horizontalHeader()
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self.on_header_context_menu)

        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_table_context_menu)
        self.table_view.doubleClicked.connect(self.on_cell_double_clicked)

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
        self.df_model.dataChanged.connect(lambda: self.table_view.viewport().update())
        self.run_row_delegate = RunRowDelegate(self.table_view)
        self.table_view.setItemDelegateForColumn(0, self.run_row_delegate)
        self.run_row_delegate.clicked.connect(self.on_run_row_clicked)
        self.setCentralWidget(main_widget)
        
    def showEvent(self, event):
        super().showEvent(event)
        # Only run these once right after the GUI is shown
        QTimer.singleShot(0, self._startup_after_ui)

    def _startup_after_ui(self):
        """
        Called once the main window is fully visible.
        We can safely load user settings, load the last file, start email checks, etc.
        """
        self.load_user_settings()
        self.check_and_load_last_file()
        # If no file was loaded, set up default transformations
        if not self.current_file_path:
            self.setup_default_transformations()

        self.check_email_responses()
    def init_headers(self):
        """Initialize custom header with action buttons"""
        self.table_view.setHorizontalHeader(self.header)
        self.header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.header.customContextMenuRequested.connect(self.on_header_context_menu)
        self.header.action_requested.connect(self.on_header_action)
        self.update_header_actions()

    def update_header_actions(self):
        """Set which columns show action buttons based on transformations"""
        if not hasattr(self, "df_model") or not self.df_model.dataFrame().attrs.get("column_metadata"):
            return

        action_cols = [
            i for i, col in enumerate(self.df_model.dataFrame().attrs["column_metadata"])
            if col["transform"] is not None
        ]
        self.header.set_action_columns(action_cols)
    def on_header_action(self, col):
        """Handle header button clicks"""
        action = self.column_actions.get(col)
        if not action:
            return
            
        selected = self.table_view.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select rows to process")
            return
            
        for idx in selected:
            self.process_action(action, idx.row())
    def load_user_settings(self):
        """
        Check essential settings (like email credentials, resume folder) AFTER UI is loaded.
        Prompt user if missing.
        """
        email_account = get_email_account()
        resume_folder = get_resume_text()

        if not email_account or not resume_folder:
            msg = (
                "Some essential settings (Email or Resume folder) are missing.\n"
                "Please configure them now."
            )
            result = QMessageBox.warning(self, "Incomplete Setup", msg,
                                         QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            if result == QMessageBox.StandardButton.Ok:
                self.open_settings_dialog()
    def check_and_load_last_file(self):
        """Check for lastfile.txt and load the file if it exists and is valid."""
        if os.path.exists('lastfile.txt'):
            try:
                with open('lastfile.txt', 'r') as f:
                    last_path = f.read().strip()
                if last_path and os.path.exists(last_path):
                    self.load_file(last_path)
            except Exception as e:
                print(f"Error loading last file: {e}")
    # ------------------------------------------------------
    # SETTINGS DIALOG
    # ------------------------------------------------------
    def open_settings_dialog(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.accepted:
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
            return

        # Define column structure with metadata
        columns = [
            {"name": "CompanyName", "type": "text", "transform": None},
            {"name": "CompanyWebsite", "type": "text", "transform": "website_scrape"},
            {"name": "WebsiteSummary", "type": "text", "transform": None},
            {"name": "JobURL", "type": "text", "transform": "job_scrape"},
            {"name": "Job_Description", "type": "text", "transform": None},
            {"name": "Hiring_Manager_LinkedIn", "type": "text", "transform": "wiza_enrich"},
            {"name": "Application_Status", "type": "text", "transform": None},
            {"name": "Job_Title", "type": "text", "transform": None},
            {"name": "Hiring_Manager_Name", "type": "text", "transform": None},
            {"name": "Email", "type": "text", "transform": None},
            {"name": "LinkedIn_Summary", "type": "text", "transform": None},
            {"name": "Job_Description_Response", "type": "text", "transform": "jd_analysis"},
            {"name": "LinkedIn_Intro", "type": "text", "transform": "linkedin_msg"},
            {"name": "FollowUp_Email_1", "type": "text", "transform": "followup_email"},
            {"name": "FollowUp_Email_2", "type": "text", "transform": "followup_email"},
            
            {"name": "Job_ID", "type": "text", "transform": None},
        ]

        try:
            # Create DataFrame with 5 empty rows
            data = {col["name"]: [""] * 5 for col in columns}
            df = pd.DataFrame(data)

            # Save data file
            save_data(df, file_path)

            
            # Initialize application state
            self.df_model.setDataFrame(df)
            self.set_current_file_path(file_path)
            
            # Initialize transformation manager with empty transformations
            self.trans_manager = TransformationManager(file_path)
            # Set default transformations
            self.setup_default_transformations()
            
            # Force save initial transformations
            self.trans_manager.save_metadata()
            
            QMessageBox.information(
                self, 
                "File Created",
                f"Successfully created new file with 5 empty rows:\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Creation Error",
                f"Could not create file:\n{str(e)}"
            )
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
            df.columns = [col.replace(' ', '_') for col in df.columns]
            self.df_model.setDataFrame(df)
            self.set_current_file_path(file_path)

            # Create or load existing transformation manager for this file
            self.trans_manager = TransformationManager(file_path)

            # Attempt to re-apply transformations (to fill in existing data)  TODO
            new_df = self.trans_manager.apply_all_transformations(df)
            self.df_model.setDataFrame(new_df)

        except Exception as e:
            QMessageBox.critical(self, "Error Loading File", str(e))

    def set_current_file_path(self, path: str):
        self.current_file_path = path
        # Update lastfile.txt when a valid path is set
        if path:
            try:
                with open('lastfile.txt', 'w') as f:
                    f.write(path)
            except Exception as e:
                print(f"Error saving last file path: {e}")
        # Update button text
        # Update lastfile.txt and UI elements
        if path:
            self.create_save_button.setText("Save File")
            self.add_row_action.setVisible(True)  # Show when file exists
        else:
            self.create_save_button.setText("Create New")
            self.add_row_action.setVisible(False)  # Hide when no file

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
        add_column_action = menu.addAction("Add Column")
        add_row_action = menu.addAction("Add Row")

        # Add transformation actions if applicable
        if self.trans_manager:
            col_name = self.df_model.dataFrame().columns[col_index]
            transforms = []
            for tid, tmeta in self.trans_manager.get_metadata()["transformations"].items():
                if tmeta["output_col"] == col_name:
                    transforms.append((tid, tmeta))
            for tid, tmeta in transforms:
                action = menu.addAction(f"Re-run {tmeta['transformation_name']} on All Rows")
                action.triggered.connect(lambda checked, tid=tid: self.force_rerun_transformation(tid))

        action = menu.exec(self.table_view.horizontalHeader().mapToGlobal(pos))
        if action == rename_action:
            self.rename_column(col_index)
        elif action == add_column_action:
            self.add_new_column()
        elif action == delete_action:
            self.delete_column(col_index)
        elif action == dtype_action:
            self.change_column_dtype(col_index)
        elif action == add_row_action:
            self.add_new_row()

    # ------------------------------------------------------
    # UNIFIED TABLE CONTEXT MENU
    # (Add Column, Send Email, Force Re-Run)
    # ------------------------------------------------------
    def show_table_context_menu(self, pos: QPoint):
        menu = QMenu(self)

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
        if col_name in ["FollowUp_Email_1", "FollowUp_Email_2"]:
            send_email_action = menu.addAction(f"Send {col_name.capitalize()}...")
        # Force Re-Run if this column is known as an output_col in metadata
        force_rerun_action = None
        if self.trans_manager and col_name:
            for tid, tmeta in self.trans_manager.get_metadata()["transformations"].items():
                if tmeta["output_col"] == col_name:
                    force_rerun_action = menu.addAction(f"Force Re-Run {tid} on This Row")
                    break
        add_job_action = menu.addAction("Add Job to Company")
        add_hiring_action = menu.addAction("Add Hiring Member to Job")
        add_row_action = menu.addAction("Add Row")
        # NEW: Delete Row action
        delete_row_action = None
        if index.isValid():
            delete_row_action = menu.addAction("Delete Row")
        action = menu.exec(self.table_view.mapToGlobal(pos))
        
        if action == add_job_action:
            self.duplicate_row_for_new_job(row_idx)
        elif action == add_hiring_action:
            self.duplicate_row_for_new_hiring_manager(row_idx)
        elif send_email_action is not None and action == send_email_action:
            self.open_compose_dialog_for_email(row_idx, col_name)
        elif force_rerun_action and action == force_rerun_action:
            self.force_rerun_for_row(col_name, row_idx)
        elif action == add_row_action:
            self.add_new_row()
        elif action == delete_row_action and index.isValid():
            self.delete_row(index.row())
    def duplicate_row_for_new_job(self, row_idx):
        df = self.df_model.dataFrame()
        if row_idx < 0 or row_idx >= len(df):
            return

        new_row = df.iloc[row_idx].copy()
        new_row[['Job_Title', 'Job_Description', 'Application_Status',
                'Hiring_Manager_Name', 'Hiring_Manager_LinkedIn',
                'Email', 'LinkedIn_Intro',
                'FollowUp_Email_1', 'FollowUp_Email_2']] = ''

        self.df_model.insertRows(row_idx, 1)
        updated_df = self.df_model.dataFrame()
        updated_df.iloc[row_idx] = new_row
        self.df_model.setDataFrame(updated_df)
        old_row_idx = row_idx + 1
        new_row_idx = row_idx

        # 6) Copy the metadata (row_signatures) from the old row to this new row.
        if self.trans_manager:
            self.trans_manager.copy_row_signatures(old_idx=old_row_idx, new_idx=new_row_idx)
    def duplicate_row_for_new_hiring_manager(self, row_idx):
        df = self.df_model.dataFrame()
        if row_idx < 0 or row_idx >= len(df):
            return

        new_row = df.iloc[row_idx].copy()
        new_row[['Hiring_Manager_Name', 'Hiring_Manager_LinkedIn',
                'Email', 'LinkedIn_Intro',
                'FollowUp_Email_1', 'FollowUp_Email_2']] = ''

        self.df_model.insertRows(row_idx, 1)
        updated_df = self.df_model.dataFrame()
        updated_df.iloc[row_idx] = new_row
        self.df_model.setDataFrame(updated_df)
        old_row_idx = row_idx + 1
        new_row_idx = row_idx

        # 6) Copy the metadata (row_signatures) from the old row to this new row.
        if self.trans_manager:
            self.trans_manager.copy_row_signatures(old_idx=old_row_idx, new_idx=new_row_idx)

    
    def on_cell_double_clicked(self, index):
        if not index.isValid():
            return

        self.current_edit_index = index
        df = self.df_model.dataFrame()
        cell_value = str(df.iloc[index.row(), index.column()])
        col_name = df.columns[index.column()]

        if col_name in ["FollowUp_Email_1", "FollowUp_Email_2"]:
            self.open_compose_dialog_for_email(index.row(), col_name)
        else:
            # Block signals to prevent immediate update
            self.reading_area.blockSignals(True)
            self.reading_area.setPlainText(cell_value)
            self.reading_area.blockSignals(False)

    def update_cell_from_reading_area(self):
        """Update the DataFrame when reading area content changes"""
        if self.current_edit_index.isValid():
            new_text = self.reading_area.toPlainText()
            self.df_model.setData(
                self.current_edit_index, 
                new_text, 
                Qt.ItemDataRole.EditRole
            )
    def open_compose_dialog_for_email(self, row_idx: int, col_name: str):
        df = self.df_model.dataFrame()
        email_json = df.at[row_idx, col_name]
        to_email = df.at[row_idx, "Email"] if "Email" in df.columns else ""
        
        dlg = ComposeEmailDialog(
            to_email=to_email,
            email_json=email_json,
            parent=self
        )
        
        if dlg.exec() == QDialog.accepted:
            # Update sent status
            df.at[row_idx, f"{col_name}_sent"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
    def delete_row(self, row_idx: int):
        """Delete a row from the DataFrame with confirmation"""
        df = self.df_model.dataFrame()
        if row_idx < 0 or row_idx >= len(df):
            return

        reply = QMessageBox.question(
            self,
            "Delete Row",
            f"Are you sure you want to delete row {row_idx+1}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Remove the row from the model
                self.df_model.removeRows(row_idx, 1)
                QMessageBox.information(
                    self, 
                    "Success", 
                    f"Row {row_idx+1} deleted successfully."
                )
            except Exception as e:
                QMessageBox.critical(
                    self, 
                    "Error", 
                    f"Could not delete row:\n{str(e)}"
                )
    def add_new_column(self):
        new_name, ok = QInputDialog.getText(
            self, "Add Column", "Enter name for the new column:"
        )
        if ok and new_name.strip():
            try:
                internal_name = new_name.strip().replace(' ', '_')
                self.df_model.insertColumn(internal_name)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not add column:\n{e}")

    def rename_column(self, col_index):
        df = self.df_model.dataFrame()
        old_name = df.columns[col_index]
        new_name, ok = QInputDialog.getText(
            self, "Rename Column", f"Enter a new name for '{old_name}':"
        )
        if ok and new_name.strip():
            internal_name = new_name.strip().replace(' ', '_')
            self.df_model.renameColumn(col_index, internal_name)

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

        transform_name = self.transform_combo.currentText()
        transformation = self.transformations_dict.get(transform_name)
        
        if not transformation:
            QMessageBox.warning(self, "Error", "Transformation not found.")
            return

        df = self.df_model.dataFrame()
        if df.empty:
            QMessageBox.warning(self, "Empty Data", "No data to transform.")
            return

        # Get placeholder handler from the transformation
        placeholder_wrapper = transformation.get_placeholder_wrapper()

        # Create dialog with required parameters
        dialog = TransformDialog(
            transformation=transformation,
            df_columns=df.columns.tolist(),
            placeholder_wrapper=placeholder_wrapper,
            parent=self
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selections = dialog.get_selections()
        if not transformation.predefined_output and not selections["output_col"]:
            QMessageBox.warning(self, "Error", "Output column name is required.")
            return
        # Generate unique transform ID
        transform_id = f"{transform_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Register transformation
        self.trans_manager.add_transformation(
            transform_id=transform_id,
            transformation_name=transform_name,
            input_cols=selections["input_cols"],
            output_col=selections["output_col"],
            extra_params=selections["static_params"]
        )

        # Apply transformations
        new_df = self.trans_manager.apply_all_transformations(df)
        self.df_model.setDataFrame(new_df)
        QMessageBox.information(self, "Success", "Transformation applied!")
        self.auto_save(force=True)
    def setup_default_transformations(self):
        """Configure default transformations for new sheets"""
        if not self.trans_manager:
            return

        # Website Scrape
        self.trans_manager.add_transformation(
            transform_id="website_scrape",
            transformation_name="Stealth Browser Web Scraper",
            input_cols=["CompanyWebsite"],
            output_col="WebsiteSummary",
            condition_type="is_not_empty",
            condition_cols=["CompanyWebsite"]  # Changed to list
        )

        # Job Scrape
        self.trans_manager.add_transformation(
            transform_id="job_scrape",
            transformation_name="Stealth Browser Web Scraper",
            input_cols=["JobURL"],
            output_col="Job_Description",
            condition_type="is_not_empty",  # Add missing condition
            condition_cols=["JobURL"]  # Added as list
        )

        # Wiza Enrichment
        self.trans_manager.add_transformation(
            transform_id="wiza_enrich",
            transformation_name="Wiza Individual Reveal Transformation",
            input_cols=["Hiring_Manager_LinkedIn"],
            output_col="Email",  # Now properly sets Email column
            condition_type="is_not_empty",
            condition_cols=["Hiring_Manager_LinkedIn"]
        )

        # LinkedIn Message
        self.trans_manager.add_transformation(
            transform_id="linkedin_msg",
            transformation_name="LinkedIn Intro Message",
            input_cols=["Job_Description"],
            output_col="LinkedIn_Intro",
            condition_type="all_not_empty",
            condition_cols=["Hiring_Manager_LinkedIn", "Job_Description"]  # Fixed column name
        )

        # Follow-Up Emails
        self.trans_manager.add_transformation(
            transform_id="followup_email",
            transformation_name="Professional Follow-Up Emails",
            input_cols=["Job_Description"],
            output_col= "FollowUp_Email_1", 
            condition_type="all_not_empty",
            condition_cols=["Email", "Job_Description", "Hiring_Manager_LinkedIn"]
        )
    def get_column_roles(self):
        """Return a dict mapping column names to 'input' or 'output'."""
        column_roles = {}
        if not self.trans_manager:
            return column_roles
        metadata = self.trans_manager.get_metadata()
        for t_meta in metadata.get("transformations", {}).values():
            for input_col in t_meta.get("input_cols", []):
                column_roles[input_col] = 'input'
            output_col = t_meta.get("output_col")
            if output_col:
                column_roles[output_col] = 'output'
        return column_roles

    def get_column_role(self, column_index: int) -> str | None:
        """Check if column is input/output considering multi-output transforms"""
        if not self.trans_manager or column_index < 0:
            return None

        df = self.df_model.dataFrame()
        col_name = df.columns[column_index]
        
        # Check both single and multi-output transformations
        for t_meta in self.trans_manager.get_metadata()["transformations"].values():
            if col_name in t_meta.get("input_cols", []):
                return 'input'
            if col_name == t_meta.get("output_col"):
                return 'output'
        return None

    def on_run_row_clicked(self, row_idx):
        """Queue row for processing and print condition status"""
        if row_idx in self.processing_rows:
            return
            
        df = self.df_model.dataFrame()
        sorted_transforms = self.get_sorted_transformations()
        
        # Check conditions for each transformation
        print(f"\n--- Condition checks for row {row_idx} ---")
        for transform_id in sorted_transforms:
            condition_met = self.trans_manager.should_process_transform(df, transform_id, row_idx)

            transform_name = self.trans_manager.get_metadata()["transformations"][transform_id]["transformation_name"]
            status = "MET" if condition_met else "NOT MET"
            print(f"{transform_name} ({transform_id}): {status}")
        
        self.processing_rows.add(row_idx)
        worker = self.trans_manager.add_row_to_queue(row_idx, df, sorted_transforms)
        self._connect_worker_signals(worker) 
        self._update_row_style(row_idx, "processing")
    def _connect_worker_signals(self, worker):
        worker.signals.started.connect(self._handle_transform_start)
        worker.signals.finished.connect(self._handle_transform_finish)
        worker.signals.error.connect(self._handle_transform_error)

    def _handle_transform_start(self, row_idx):
        self._update_row_style(row_idx, "processing")

    def _handle_transform_finish(self, row_idx, new_data):
        """Update the DataFrame after transformations, handling new columns."""
        try:
            df = self.df_model.dataFrame().copy()

            # Check for new columns added during transformation
            new_columns = new_data.index.difference(df.columns)
            print(new_columns)
            if not new_columns.empty:
                # Add missing columns to the DataFrame
                for col in new_columns:
                    df[col] = pd.NA  # Initialize with NaN/empty
                self.df_model.setDataFrame(df)  # Update model structure first

            # Align the new_data Series with current DataFrame columns
            aligned_data = new_data.reindex(df.columns, fill_value=pd.NA)
            
            # Update the specific row
            df.iloc[row_idx] = aligned_data
            self.df_model.setDataFrame(df)  # Update model with new data

            self.processing_rows.discard(row_idx)
            self._update_row_style(row_idx, "success")
            self.statusBar().showMessage(f"Row {row_idx+1} processed successfully", 3000)
            self.auto_save()
            print(f"Row {row_idx+1} transformation complete.")
        except Exception as e:
            print(f"Error updating row {row_idx}: {str(e)}")
            self.processing_rows.discard(row_idx)
            self._update_row_style(row_idx, "error")

    def _handle_transform_error(self, row_idx, error_msg):
        self.processing_rows.discard(row_idx)
        self._update_row_style(row_idx, "error")
        QMessageBox.warning(self, "Processing Error", 
                           f"Row {row_idx+1}: {error_msg}")

    def _update_row_style(self, row_idx, state):
        # Visual feedback using delegate
        self.table_view.viewport().update(
            self.table_view.visualRect(self.df_model.index(row_idx, 0))
        )

    def get_sorted_transformations(self):
        """Sort transformations by their output column's position."""
        df = self.df_model.dataFrame()
        transformations = []
        for transform_id, meta in self.trans_manager.get_metadata()["transformations"].items():
            output_col = meta.get("output_col")
            if output_col and output_col in df.columns:
                col_index = df.columns.get_loc(output_col)
                transformations.append((col_index, transform_id))
            else:
                # Place transformations without output_col at the end
                transformations.append((len(df.columns), transform_id))
        # Sort by column index
        transformations.sort(key=lambda x: x[0])
        return [tid for _, tid in transformations]
    

    def check_email_responses(self):
        """Check for email responses in the last 24 hours and show matches."""
        if not self.current_file_path:
            return

        df = self.df_model.dataFrame()
        if df.empty:
            return

        # Get unique emails and company names
        emails = df['Email'].dropna().unique().tolist()
        if len(emails)==0:
            return 
        company_names = df['CompanyName'].dropna().unique().tolist()

        # Fetch recent emails
        recent_emails = load_incoming_emails_last_24h()

        matched_indices = set()

        # Check each recent email for matches
        for email_info in recent_emails:
            # Extract sender's email
            sender_email = extract_email_address(email_info['from'])

            # Check if sender is in the Email column
            email_matches = df.index[df['Email'].str.lower() == sender_email.lower()].tolist()
            matched_indices.update(email_matches)

            # Check if company name is in email content
            email_content = f"{email_info['subject']} {email_info['body']}"
            for company in company_names:
                if pd.isna(company):
                    continue
                pattern = re.compile(re.escape(str(company)), re.IGNORECASE)
                if pattern.search(email_content):
                    company_matches = df.index[
                        df['CompanyName'].str.lower() == str(company).lower()
                    ].tolist()
                    matched_indices.update(company_matches)

        if matched_indices:
            matched_df = df.iloc[list(matched_indices)]
            self.show_response_matches(matched_df)

    def show_response_matches(self, matched_df):
        """Display matching responses in a dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("New Responses Found")
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(dialog)

        # Table view to display matches
        table = QTableView()
        model = DataFrameModel(matched_df[['CompanyName', 'Job_Title', 'Hiring_Manager_Name']])
        table.setModel(model)
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)

        # Close button
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close)

        dialog.exec()