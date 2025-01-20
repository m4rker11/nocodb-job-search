# transformations/email_transformations.py

import pandas as pd
from .transformations_base import BaseTransformation

class EmailFromNameDomain(BaseTransformation):
    """
    Example transformation:
    Creates an email address from a Name column and a Domain column.
    Expects exactly two input columns: Name, Domain.
    """

    name = "Get email from name & domain"
    description = "Combine `Name` + `Domain` -> email address"

    def transform(self, df, output_col_name, *args):
        if len(args) != 2:
            raise ValueError(
                "EmailFromNameDomain requires exactly 2 columns: (Name, Domain)."
            )
        name_col, domain_col = args

        # Create or overwrite the output_col_name in the DataFrame
        df[output_col_name] = (
            df[name_col]
            .astype(str)
            .str.lower()
            .str.replace(r"\s+", ".", regex=True)  # Replace spaces with dots
            + "@"
            + df[domain_col].astype(str).str.lower()
        )
        return df

    def required_inputs(self):
        """
        Returns labels for the input columns expected.
        """
        return ["Name Column", "Domain Column"]
