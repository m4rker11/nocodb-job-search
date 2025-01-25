import pandas as pd
from PyQt6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, QVariant
)

class DataFrameModel(QAbstractTableModel):
    """
    A custom Qt model that bridges a pandas DataFrame and a QTableView.
    Allows direct editing of cells.
    """

    def __init__(self, df=pd.DataFrame(), parent=None):
        super().__init__(parent)
        self._df = df.copy()

    def setDataFrame(self, df: pd.DataFrame):
        """Replace the current DataFrame."""
        if '__Run_Row__' not in df.columns:
            df.insert(0, '__Run_Row__', '')
        self.beginResetModel()
        self._df = df.copy()
        self.endResetModel()

    def dataFrame(self) -> pd.DataFrame:
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
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                col_name = str(self._df.columns[section])
                display_name = col_name.replace('_', ' ')  # Convert underscores to spaces
                return display_name
            else:
                return str(self._df.index[section])
        return QVariant()

    def insertRows(self, row, count=1, parent=QModelIndex()):
        if row < 0 or row > self.rowCount():
            return False

        self.beginInsertRows(QModelIndex(), row, row + count - 1)
        
        new_rows = pd.DataFrame([{col: None for col in self._df.columns} for _ in range(count)])
        
        if self._df.empty:
            self._df = new_rows
        else:
            top = self._df.iloc[:row]
            bottom = self._df.iloc[row:]
            self._df = pd.concat([top, new_rows, bottom], ignore_index=True)
        
        self.endInsertRows()
        return True
    def removeRows(self, row: int, count: int, parent=QModelIndex()) -> bool:
        try:
            self.beginRemoveRows(parent, row, row + count - 1)
            self._df = self._df.drop(
                index=range(row, row + count)
            ).reset_index(drop=True)
            self.endRemoveRows()
            return True
        except Exception as e:
            print(f"Error removing rows: {e}")
            return False
    def removeColumn(self, col_idx: int):
        self.beginResetModel()
        col_name = self._df.columns[col_idx]
        self._df.drop(columns=[col_name], inplace=True)
        self.endResetModel()

    def renameColumn(self, col_idx, new_name: str):
        self.beginResetModel()
        old_name = self._df.columns[col_idx]
        self._df.rename(columns={old_name: new_name}, inplace=True)
        self.endResetModel()

    def changeColumnDtype(self, col_idx, new_dtype: str):
        self.beginResetModel()
        col_name = self._df.columns[col_idx]
        try:
            self._df[col_name] = self._df[col_name].astype(new_dtype)
        except Exception as e:
            self.endResetModel()
            raise e
        self.endResetModel()

    def insertColumn(self, col_name: str):
        self.beginResetModel()
        self._df[col_name] = None
        self.endResetModel()
    def clear_columns(self, columns, row_idx):
        """Clear specific columns in a row"""
        self.beginResetModel()
        for col in columns:
            if col in self._df.columns:
                self._df.at[row_idx, col] = None
        self.endResetModel()