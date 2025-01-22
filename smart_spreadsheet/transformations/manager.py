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

    def apply_all_transformations(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Go through each transformation in metadata. For each row, evaluate condition,
        check signature, and (re)run if needed.
        """
        for transform_id, meta in self._metadata["transformations"].items():
            transformation = self.transformations_dict.get(meta["transformation_name"])
            if not transformation:
                # Could raise an error or skip
                continue

            # Condition logic
            condition_series = self._build_condition_series(df, meta)

            for row_idx in range(len(df)):
                # Check condition for that row
                if not condition_series.iloc[row_idx]:
                    continue  # skip if condition is false

                # Compute row signature
                input_cols = meta["input_cols"]
                new_sig = self.compute_row_signature(df, row_idx, input_cols)
                old_sig = meta["row_signatures"].get(str(row_idx), None)

                # Only run if signature changed
                if new_sig != old_sig:
                    # Run transformation for that row
                    df = self.run_transformation_row(df, transform_id, row_idx)
                    # Update signature
                    meta["row_signatures"][str(row_idx)] = new_sig

        return df

    def force_rerun_transformation(
        self,
        df: pd.DataFrame,
        transform_id: str,
        row_idx: int
    ) -> pd.DataFrame:
        """
        Force a re-run on a single row, ignoring the old signature or condition.
        """
        meta = self._metadata["transformations"].get(transform_id)
        if not meta:
            # Unknown transformation
            return df

        # Actually run transformation logic on that row
        df = self.run_transformation_row(df, transform_id, row_idx)

        # Recompute and store new signature
        new_sig = self.compute_row_signature(df, row_idx, meta["input_cols"])
        meta["row_signatures"][str(row_idx)] = new_sig

        return df

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
        """
        Construct a boolean series based on condition_type, condition_col, condition_value.
        If none is given, default to True for all rows.
        """
        ctype = meta.get("condition_type")
        ccol = meta.get("condition_col")
        cval = meta.get("condition_value")

        # If no condition type or no column, run on all rows
        if not ctype or not ccol or ccol not in df.columns:
            return pd.Series([True]*len(df), index=df.index)

        # Convert column to string type (just to handle None vs empty gracefully)
        col_series = df[ccol].astype(str)

        # Build condition
        if ctype == "is_empty":
            # True if cell is "" or "nan" (after astype(str))
            return (col_series == "") | (col_series.str.lower() == "nan")

        elif ctype == "is_not_empty":
            # Opposite of is_empty
            return ~((col_series == "") | (col_series.str.lower() == "nan"))

        elif ctype == "equals" and cval is not None:
            return col_series == str(cval)

        elif ctype == "not_equals" and cval is not None:
            return col_series != str(cval)

        else:
            # If something is missing or invalid, default to all True
            return pd.Series([True]*len(df), index=df.index)
