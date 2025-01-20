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
        condition_str: str
    ):
        """
        Add a new transformation entry to the metadata, overwriting if already exists.
        transform_id is a short string ID you use to reference it (e.g. 'EmailEnrich1').
        """
        self._metadata["transformations"][transform_id] = {
            "transformation_name": transformation_name,
            "input_cols": input_cols,
            "output_col": output_col,
            "condition_str": condition_str,
            "row_signatures": {}
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
                continue  # or raise an error

            input_cols = meta["input_cols"]
            output_col = meta["output_col"]
            condition_str = meta["condition_str"]

            # Evaluate condition (safe eval or use df.query) - be cautious with real security
            try:
                condition_series = df.eval(condition_str)
            except Exception:
                # If the user entered something invalid
                condition_series = pd.Series([True]*len(df), index=df.index)  # fallback: run on all

            for row_idx in range(len(df)):
                # Check condition for that row
                if not condition_series.iloc[row_idx]:
                    continue  # skip if condition is false

                # Compute row signature
                new_sig = self.compute_row_signature(df, row_idx, input_cols)
                old_sig = meta["row_signatures"].get(str(row_idx), None)

                # Only run if signature changed
                if new_sig != old_sig:
                    # Run transformation for that row
                    df = self.run_transformation_row(df, transformation, input_cols, output_col, row_idx)
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
            return df  # unknown transformation

        transformation = self.transformations_dict.get(meta["transformation_name"])
        if not transformation:
            return df  # unknown transformation type

        input_cols = meta["input_cols"]
        output_col = meta["output_col"]
        # Actually run transformation logic on that row
        df = self.run_transformation_row(df, transformation, input_cols, output_col, row_idx)
        # Recompute and store new signature
        new_sig = self.compute_row_signature(df, row_idx, input_cols)
        meta["row_signatures"][str(row_idx)] = new_sig
        return df

    def run_transformation_row(self, df: pd.DataFrame, transformation, input_cols, output_col, row_idx):
        """
        Actually call 'transformation.transform' for a single row.
        Because the default 'transform' often expects the entire DataFrame,
        we can do a partial approach or re-run for the entire DF but only row row_idx is changed.

        For demonstration, we'll re-run the entire column logic but
        it only truly updates row_idx if the transformation is well-coded.
        """
        # This approach calls the transformation on the entire DF (simple approach).
        # The transformation itself can handle logic row by row if desired.
        df = transformation.transform(df, output_col, *input_cols)
        return df
