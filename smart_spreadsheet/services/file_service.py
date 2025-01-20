import os
import pandas as pd

def load_data(file_path: str) -> pd.DataFrame:
    """
    Load data from CSV or Excel into a DataFrame.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(file_path)
    elif ext in [".xls", ".xlsx"]:
        return pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

def save_data(df: pd.DataFrame, file_path: str):
    """
    Save data to CSV or Excel, depending on the extension.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        df.to_csv(file_path, index=False)
    elif ext in [".xls", ".xlsx"]:
        df.to_excel(file_path, index=False)
    else:
        raise ValueError(f"Unsupported file format for saving: {ext}")
