import hashlib
import pandas as pd
from typing import Dict, Any
from services.metadata_service import load_metadata, save_metadata
from transformations.utils import find_transformations_in_package

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
        condition_col: str = None,
        condition_value: str = None,
        extra_params: dict = None
    ):
        """
        Add a new transformation entry to the metadata, overwriting if already exists.
        transform_id is a short string ID you use to reference it (e.g. 'EmailEnrich1').

        Accepts legacy `condition_str` parameter but does not use it,
        preferring simplified condition parameters.
        """
        if extra_params is None:
            extra_params = {}

        self._metadata["transformations"][transform_id] = {
            "transformation_name": transformation_name,
            "input_cols": input_cols,
            "output_col": output_col,
            "condition_type": condition_type,
            "condition_col": condition_col,
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

    def force_rerun_transformation(self, transform_id):
        """Force re-run a transformation on all rows."""
        df = self.df_model.dataFrame()
        if df.empty:
            return
        # Clear all row signatures for this transformation
        meta = self.trans_manager.get_metadata()["transformations"].get(transform_id)
        if not meta:
            return
        meta["row_signatures"].clear()
        # Apply transformation
        new_df = self.trans_manager.apply_all_transformations(df)
        self.df_model.setDataFrame(new_df)
        self.auto_save(force=True)

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

    def _build_condition_series(self, df: pd.DataFrame, meta: dict) -> pd.Series:
        """Handle both single and multi-column conditions"""
        ctype = meta.get("condition_type")
        ccols = meta.get("condition_cols") or [meta.get("condition_col")]  # Backward compatible
        cval = meta.get("condition_value")

        # Clean column list
        ccols = [ccol for ccol in ccols if ccol in df.columns] if ccols else []

        # Default to True if no valid columns
        if not ctype or not ccols:
            return pd.Series([True]*len(df), index=df.index)

        # Convert columns to string series
        col_series = df[ccols].astype(str)

        if ctype == "is_empty":
            return (col_series == "") | (col_series == "nan").any(axis=1)
            
        elif ctype == "is_not_empty":
            return ((col_series != "") & (col_series != "nan")).any(axis=1)
            
        elif ctype == "all_not_empty":
            return ((col_series != "") & (col_series != "nan")).all(axis=1)
            
        elif ctype == "equals" and cval is not None:
            return (col_series == str(cval)).any(axis=1)
            
        elif ctype == "all_equals" and cval is not None:
            return (col_series == str(cval)).all(axis=1)
            
        else:
            return pd.Series([True]*len(df), index=df.index)