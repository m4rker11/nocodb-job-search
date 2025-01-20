import os
import sys
import pandas as pd
import importlib
import pkgutil

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QTableView,
    QInputDialog,
    QMenu
)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, QPoint

from transformations.transformations_base import BaseTransformation


def find_transformations_in_package(package_name="transformations"):
    """
    Dynamically discovers and imports all modules in the given package,
    returning a dict of { transformation_name: instance_of_that_transformation }.
    """
    package = importlib.import_module(package_name)
    transformations = {}
    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
        if not is_pkg:
            full_module_name = f"{package_name}.{module_name}"
            module = importlib.import_module(full_module_name)
            for name, obj in vars(module).items():
                if isinstance(obj, type) and issubclass(obj, BaseTransformation) and obj is not BaseTransformation:
                    instance = obj()
                    transformations[instance.name] = instance
    return transformations


class DataFrameModel(QAbstractTableModel):
    """
    A custom Qt model that bridges a pandas DataFrame and a QTableView.
    Allows direct editing of cells.
    """

    def __init__(self, df=pd.DataFrame(), parent=None):
        super().__init__(parent)
        self._df = df.copy()

    def setDataFrame(self, df):
        """Replace the current DataFrame."""
        self.beginResetModel()
        self._df = df.copy()
        self.endResetModel()

    def dataFrame(self):
        """Return a copy of the current DataFrame."""
        return self._df.copy()

    def rowCount(self, parent=QModelIndex()):
        return len(self._df.index)

    def columnCount(self, parent=QModelIndex()):
        return len(self._df.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return QVariant()
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            value = self._df.iat[index.row(), index.column()]
            return str(value) if pd.notnull(value) else ""
        return QVariant()

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if index.isValid() and role == Qt.ItemDataRole.EditRole:
            self._df.iat[index.row(), index.column()] = value
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
            return True
        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return (
            Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsEditable
        )

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """
        Display column names as horizontal headers, row indices as vertical headers.
        """
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._df.columns[section])
            else:
                # row index
                return str(self._df.index[section])
        return QVariant()

    def insertRows(self, row, count=1, parent=QModelIndex()):
        """
        Insert new empty rows at the specified position (commonly, at the end).
        """
        self.beginInsertRows(QModelIndex(), row, row + count - 1)
        for _ in range(count):
            # Create a new row with None (or NaN) for each column
            new_row = pd.Series([None] * self.columnCount(), index=self._df.columns, name=len(self._df))
            self._df = self._df._append(new_row)
        self.endInsertRows()
        return True

    def removeColumn(self, col_idx):
        """
        Remove the given column index from the DataFrame.
        """
        self.beginResetModel()
        col_name = self._df.columns[col_idx]
        self._df.drop(columns=[col_name], inplace=True)
        self.endResetModel()

    def renameColumn(self, col_idx, new_name):
        """
        Rename a column by index.
        """
        self.beginResetModel()
        old_name = self._df.columns[col_idx]
        self._df.rename(columns={old_name: new_name}, inplace=True)
        self.endResetModel()

    def changeColumnDtype(self, col_idx, new_dtype):
        """
        Attempt to change the dtype of the specified column.
        """
        self.beginResetModel()
        col_name = self._df.columns[col_idx]
        try:
            self._df[col_name] = self._df[col_name].astype(new_dtype)
        except Exception as e:
            self.endResetModel()  # reset anyway
            raise e
        self.endResetModel()

    def insertColumn(self, col_name):
        """
        Add a new empty column with the given name.
        """
        self.beginResetModel()
        self._df[col_name] = None
        self.endResetModel()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Spreadsheet (PyQt)")
        self.resize(1100, 700)

        self.csv_folder_path = None
        self.current_csv_path = None

        self.df_model = DataFrameModel(pd.DataFrame())
        self.transformations_dict = find_transformations_in_package("transformations")

        # Main layout setup
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        self.setCentralWidget(widget)

        # Folder selection
        folder_layout = QHBoxLayout()
        folder_label = QLabel("CSV Folder:")
        self.folder_input = QLineEdit(".")
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_for_folder)

        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(browse_button)
        main_layout.addLayout(folder_layout)

        # Create new CSV
        create_layout = QHBoxLayout()
        self.new_csv_name_input = QLineEdit("new_file.csv")
        create_button = QPushButton("Create Empty CSV")
        create_button.clicked.connect(self.create_new_csv)
        create_layout.addWidget(QLabel("New CSV filename:"))
        create_layout.addWidget(self.new_csv_name_input)
        create_layout.addWidget(create_button)
        main_layout.addLayout(create_layout)

        # CSV select combo
        self.csv_select_combo = QComboBox()
        self.csv_select_combo.currentIndexChanged.connect(self.load_selected_csv)
        main_layout.addWidget(self.csv_select_combo)

        # Table View
        self.table_view = QTableView()
        self.table_view.setModel(self.df_model)
        main_layout.addWidget(self.table_view, stretch=1)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_table_context_menu)

        # Add row layout
        add_row_layout = QHBoxLayout()
        add_row_btn = QPushButton("Add Row")
        add_row_btn.clicked.connect(self.add_new_row)
        add_row_layout.addWidget(add_row_btn)
        main_layout.addLayout(add_row_layout)

        # Transformations
        transform_layout = QHBoxLayout()
        self.transform_combo = QComboBox()
        if self.transformations_dict:
            self.transform_combo.addItems(self.transformations_dict.keys())
        transform_layout.addWidget(self.transform_combo)

        apply_transform_button = QPushButton("Apply Transformation")
        apply_transform_button.clicked.connect(self.apply_transformation)
        transform_layout.addWidget(apply_transform_button)

        main_layout.addLayout(transform_layout)

        # Save Button
        save_button = QPushButton("Save Changes to CSV")
        save_button.clicked.connect(self.save_csv)
        main_layout.addWidget(save_button)

        # Initialize the UI with default folder
        self.update_csv_list()

    # -------------------------------
    # Folder and CSV file management
    # -------------------------------

    def browse_for_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select CSV Folder")
        if folder:
            self.folder_input.setText(folder)
            self.update_csv_list()

    def update_csv_list(self):
        self.csv_folder_path = self.folder_input.text()
        if not os.path.isdir(self.csv_folder_path):
            QMessageBox.warning(self, "Warning", "Please select a valid directory.")
            return

        csv_files = [f for f in os.listdir(self.csv_folder_path) if f.endswith(".csv")]
        self.csv_select_combo.clear()
        if csv_files:
            self.csv_select_combo.addItems(csv_files)
        else:
            self.csv_select_combo.addItem("No CSV files found")

    def create_new_csv(self):
        csv_name = self.new_csv_name_input.text().strip()
        if not csv_name.endswith(".csv"):
            QMessageBox.warning(self, "Error", "File name must end with .csv")
            return

        file_path = os.path.join(self.folder_input.text(), csv_name)
        if os.path.exists(file_path):
            QMessageBox.warning(self, "Error", f"File '{csv_name}' already exists.")
            return

        df_empty = pd.DataFrame(columns=["column1", "column2"])
        df_empty.to_csv(file_path, index=False)
        QMessageBox.information(self, "Success", f"New CSV file '{csv_name}' created.")
        self.update_csv_list()

    def load_selected_csv(self):
        selected_file = self.csv_select_combo.currentText()
        if selected_file == "No CSV files found":
            return

        self.current_csv_path = os.path.join(self.csv_folder_path, selected_file)
        if not os.path.isfile(self.current_csv_path):
            QMessageBox.warning(self, "Error", "Selected file does not exist.")
            return

        df = pd.read_csv(self.current_csv_path)
        self.df_model.setDataFrame(df)

    def save_csv(self):
        if not self.current_csv_path:
            QMessageBox.warning(self, "Error", "No CSV file selected.")
            return

        df = self.df_model.dataFrame()
        try:
            df.to_csv(self.current_csv_path, index=False)
            QMessageBox.information(self, "Success", f"Saved changes to {os.path.basename(self.current_csv_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save CSV:\n{e}")
    
    def show_table_context_menu(self, pos: QPoint):
        """
        Show context menu when user right-clicks anywhere in the table.
        """
        menu = QMenu(self)
        add_column_action = menu.addAction("Add Column")
        
        # Get the column header if clicked on one
        col_index = self.table_view.horizontalHeader().logicalIndexAt(pos.x())
        if col_index >= 0:
            rename_action = menu.addAction("Rename Column")
            delete_action = menu.addAction("Delete Column")
            dtype_action = menu.addAction("Change Data Type")
        
        action = menu.exec(self.table_view.mapToGlobal(pos))
        
        if action == add_column_action:
            self.add_new_column()
        elif col_index >= 0:
            if action == rename_action:
                self.rename_column(col_index)
            elif action == delete_action:
                self.delete_column(col_index)
            elif action == dtype_action:
                self.change_column_dtype(col_index)
    def add_new_column(self):
        """
        Prompt user for new column name and add it to the DataFrame.
        """
        new_name, ok = QInputDialog.getText(
            self, "Add Column", "Enter name for the new column:"
        )
        if ok and new_name.strip():
            try:
                self.df_model.insertColumn(new_name.strip())
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not add column:\n{e}")
    # -----------------
    # Row Manipulation
    # -----------------

    def add_new_row(self):
        """
        Insert a new blank row at the bottom.
        """
        row_position = self.df_model.rowCount()
        self.df_model.insertRows(row_position, 1)

    # -----------------------
    # Header Context Menu
    # -----------------------

    def on_header_context_menu(self, pos: QPoint):
        """
        Show context menu when user right-clicks the column header.
        """
        # Figure out which column was clicked
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

    def rename_column(self, col_index):
        """
        Prompt the user to rename the specified column.
        """
        df = self.df_model.dataFrame()
        old_name = df.columns[col_index]
        new_name, ok = QInputDialog.getText(
            self, "Rename Column", f"Enter a new name for '{old_name}':"
        )
        if ok and new_name.strip():
            self.df_model.renameColumn(col_index, new_name.strip())

    def delete_column(self, col_index):
        """
        Delete the specified column.
        """
        # Just confirm from user
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
        """
        Prompt the user to select a new data type for the given column.
        """
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

    # -----------------------
    # Transformations
    # -----------------------

    def apply_transformation(self):
        if not self.transformations_dict:
            QMessageBox.information(self, "Info", "No transformations found.")
            return

        transform_name = self.transform_combo.currentText()
        transformation = self.transformations_dict[transform_name]

        df = self.df_model.dataFrame()
        if df.empty:
            QMessageBox.information(self, "Info", "DataFrame is empty; cannot apply transformation.")
            return

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

        # Apply transformation
        try:
            df = transformation.transform(df, output_col, *chosen_cols)
            self.df_model.setDataFrame(df)
            QMessageBox.information(self, "Success", f"New column '{output_col}' created using '{transform_name}'.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
