import pandas as pd
from transformations.base import BaseTransformation

class SampleTransformation(BaseTransformation):
    name = "Sample Transformation"
    description = "Demonstration transformation."

    def required_inputs(self):
        return ["Source Column"]

    def transform(self, df, output_col_name, *args):
        source_col = args[0]
        df[output_col_name] = df[source_col].astype(str) + "_transformed"
        return df
