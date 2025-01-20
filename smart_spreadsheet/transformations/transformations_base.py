# transformations/transformations_base.py

from abc import ABC, abstractmethod

class BaseTransformation(ABC):
    """
    Abstract base class for transformations.
    Each transformation must provide:
    - name: A user-friendly name (string)
    - description: A short explanation of what the transformation does
    - an implementation of the transform(...) method
    - a required_inputs() method to indicate which columns/arguments it needs
    """

    name = "Base Transformation"
    description = "A base class for transformations"

    @abstractmethod
    def transform(self, df, output_col_name, *args):
        """
        Perform a transformation on the given DataFrame.

        :param df: The pandas DataFrame to modify
        :param output_col_name: The column to create or overwrite with the result
        :param args: The columns (or parameters) needed for this transformation
        :return: The modified DataFrame
        """
        pass

    @abstractmethod
    def required_inputs(self):
        """
        Returns a list of string labels describing which inputs or columns
        the transformation requires. e.g. ["Name Column", "Domain Column"]
        """
        pass
