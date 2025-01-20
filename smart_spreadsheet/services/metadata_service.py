import json
import os

def load_metadata(csv_path: str) -> dict:
    """
    Given a CSV path like 'data.csv', look for 'data_metadata.json'.
    If found, load and return it as a dict. Otherwise return empty dict.
    """
    base, ext = os.path.splitext(csv_path)
    meta_path = f"{base}_metadata.json"
    if not os.path.exists(meta_path):
        return {}  # No metadata yet
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_metadata(csv_path: str, metadata: dict):
    """
    Save the metadata dict to a sidecar JSON file.
    """
    base, ext = os.path.splitext(csv_path)
    meta_path = f"{base}_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

"""
{
  "transformations": {
    "EnrichEmail": {
      "transformation_name": "EmailEnrichment",
      "input_cols": ["Email"],
      "output_col": "EnrichedData",
      "condition_str": "df['Email'].notnull()",
      "row_signatures": {
        "0": "abc123",
        "1": "def456"
      }
    }
  }
}"""