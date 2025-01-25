import hashlib
import pandas as pd
from typing import Dict, Any
from queue import Queue
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, QMutex
from services.metadata_service import load_metadata, save_metadata
from transformations.utils import find_transformations_in_package


class TransformationSignals(QObject):
    """Signals for transformation progress and completion"""
    started = pyqtSignal(int)  # row_idx
    finished = pyqtSignal(int, pd.Series)  # row_idx, updated_row
    error = pyqtSignal(int, str)  # row_idx, error_message


class TransformationWorker(QRunnable):
    """Worker for processing transformations on a single row"""
    def __init__(self, row_idx, df, trans_manager, sorted_transforms):
        super().__init__()
        self.row_idx = row_idx
        self.df = df.copy()
        self.trans_manager = trans_manager
        self.sorted_transforms = sorted_transforms
        self.signals = TransformationSignals()
        
    def run(self):
        try:
            self.signals.started.emit(self.row_idx)
            
            # Process transformations in sorted order
            for transform_id in self.sorted_transforms:
                print(f"Processing {transform_id} for row {self.row_idx}")
                try:
                    self.df = self.trans_manager.apply_single_transformation(
                        self.df, transform_id, self.row_idx
                    )
                except Exception as e:
                    print(f"Error in {transform_id}: {str(e)}")
            
            self.signals.finished.emit(self.row_idx, self.df.iloc[self.row_idx])
        except Exception as e:
            self.signals.error.emit(self.row_idx, str(e))


class TransformationManager:
    def __init__(self, csv_path: str):
        """
        :param csv_path: The path to the currently loaded CSV (or Excel).
        """
        self.csv_path = csv_path
        self.transformations_dict = find_transformations_in_package("transformations")
        
        # Load existing metadata
        self._metadata = load_metadata(csv_path)
        if "transformations" not in self._metadata:
            self._metadata["transformations"] = {}

        # Threading setup
        self.queue = Queue()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(3)  # 3 concurrent rows
        self.lock = QMutex()

    def get_metadata(self) -> dict:
        """Return the entire metadata dictionary (for debugging or saving)."""
        return self._metadata

    def add_transformation(
        self,
        transform_id: str,
        transformation_name: str,
        input_cols: list,
        output_col: str,
        condition_type: str = None,
        condition_cols: list = None,
        condition_value: str = None,
        extra_params: dict = None
    ):
        """
        Add a new transformation entry to the metadata.
        Supports both single column and multi-column conditions.
        """
        if extra_params is None:
            extra_params = {}

        self._metadata["transformations"][transform_id] = {
            "transformation_name": transformation_name,
            "input_cols": input_cols,
            "output_col": output_col,
            "condition_type": condition_type,
            "condition_cols": condition_cols,
            "condition_value": condition_value,
            "row_signatures": {},
            "extra_params": extra_params
        }

    def save_metadata(self):
        """Persist the metadata to sidecar JSON."""
        save_metadata(self.csv_path, self._metadata)

    def compute_row_signature(self, df: pd.DataFrame, row_idx: int, input_cols: list) -> str:
        """
        Build a signature (hash) from the row's input columns.
        """
        row_data = []
        for col in input_cols:
            val = df.at[row_idx, col]
            row_data.append(str(val))
        # Convert to a single string; then hash
        joined = "|".join(row_data)
        return hashlib.md5(joined.encode("utf-8")).hexdigest()

    def apply_all_transformations(self, df: pd.DataFrame, row_idx: int = None) -> pd.DataFrame:
        """Apply transformations optionally limited to a specific row."""
        for transform_id, meta in self._metadata["transformations"].items():
            transformation = self.transformations_dict.get(meta["transformation_name"])
            if not transformation:
                continue
                
            condition_series = self._build_condition_series(df, meta)

            # Determine rows to process
            if row_idx is not None:
                if row_idx < 0 or row_idx >= len(df):
                    continue
                if not condition_series.iloc[row_idx]:
                    continue
                rows_to_process = [row_idx]
            else:
                rows_to_process = [i for i, cond in enumerate(condition_series) if cond]

            for r_idx in rows_to_process:
                input_cols = meta["input_cols"]
                new_sig = self.compute_row_signature(df, r_idx, input_cols)
                old_sig = meta["row_signatures"].get(str(r_idx), None)
                if new_sig != old_sig:
                    df = self.run_transformation_row(df, transform_id, r_idx)
                    meta["row_signatures"][str(r_idx)] = new_sig

        return df

    def apply_single_transformation(self, df, transform_id, row_idx):
        """Thread-safe application of single transformation"""
        self.lock.lock()
        try:
            meta = self._metadata["transformations"][transform_id]
            if self._should_process_row(df, meta, row_idx):
                print(f"Processing row {row_idx} for transformation {transform_id}")
                new_sig = self.compute_row_signature(df, row_idx, meta["input_cols"])
                df = self.run_transformation_row(df, transform_id, row_idx)
                meta["row_signatures"][str(row_idx)] = new_sig
        finally:
            self.lock.unlock()
        return df

    def add_row_to_queue(self, row_idx, df, sorted_transforms):
        """Add a row to be processed by worker threads"""
        worker = TransformationWorker(row_idx, df, self, sorted_transforms)
        self.queue.put(worker)
        self._start_workers()

    def _start_workers(self):
        """Start workers if there's capacity"""
        while self.thread_pool.activeThreadCount() < self.thread_pool.maxThreadCount():
            try:
                worker = self.queue.get_nowait()
                self.thread_pool.start(worker)
            except:
                break

    def _should_process_row(self, df, meta, row_idx):
        """Check if row should be processed based on conditions"""
        condition_series = self._build_condition_series(df, meta)
        return condition_series.iloc[row_idx]

    def _build_condition_series(self, df: pd.DataFrame, meta: dict) -> pd.Series:
        """Handle both single and multi-column conditions with strict emptiness checks"""
        ctype = meta.get("condition_type")
        ccols = meta.get("condition_cols", [])
        cval = meta.get("condition_value")

        # Ensure condition columns are always a list
        if isinstance(ccols, str):
            ccols = [ccols]

        # Clean column list - only keep columns that exist in the DataFrame
        ccols = [ccol for ccol in ccols if ccol in df.columns]

        # Default to False if no valid columns (safer default for empty rows)
        if not ctype or not ccols:
            return pd.Series([False] * len(df), index=df.index)

        # Convert columns to string and clean
        col_series = df[ccols].astype(str)
        
        # Enhanced cleaning: handle NaN strings and whitespace
        col_series = col_series.replace({'nan': '', 'None': '', 'null': ''})
        col_series = col_series.apply(lambda x: x.str.strip())

        # Handle different condition types
        if ctype == "is_empty":
            return (col_series == "").any(axis=1)

        elif ctype == "is_not_empty":
            return (col_series != "").any(axis=1)

        elif ctype == "all_not_empty":
            return (col_series != "").all(axis=1)

        elif ctype == "equals" and cval is not None:
            return (col_series == str(cval).strip()).any(axis=1)

        elif ctype == "all_equals" and cval is not None:
            return (col_series == str(cval).strip()).all(axis=1)

        # Default to False for unknown condition types
        return pd.Series([False] * len(df), index=df.index)
    def run_transformation_row(self, df: pd.DataFrame, transform_id: str, row_idx: int) -> pd.DataFrame:
        """
        Actually call 'transformation.transform' for a single row.
        Because the default 'transform' often expects the entire DataFrame,
        we do it for the entire DF (simple approach).

        The transformation itself should handle row-by-row logic if needed.
        """
        meta = self._metadata["transformations"].get(transform_id)
        if not meta:
            return df

        transformation = self.transformations_dict.get(meta["transformation_name"])
        if not transformation:
            return df

        input_cols = meta["input_cols"]
        output_col = meta["output_col"]
        extra_params = meta.get("extra_params", {})

        # Call the transformation, passing **extra_params to handle any custom arguments
        df = transformation.transform(df, output_col, *input_cols, **extra_params)

        return df
    
    def should_process_transform(self, df: pd.DataFrame, transform_id: str, row_idx: int) -> bool:
        """Check if a row meets the conditions for a specific transformation."""
        meta = self._metadata["transformations"].get(transform_id)
        if not meta:
            return False
        condition_series = self._build_condition_series(df, meta)
        return condition_series.iloc[row_idx]