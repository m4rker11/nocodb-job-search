from abc import ABC, abstractmethod

class BaseTransformation(ABC):
    """
    Abstract base class for transformations.
    """

    name = "Base Transformation"
    description = "A base class for transformations"

    @abstractmethod
    def transform(self, df, output_col_name, *args):
        """
        Perform the transformation on DataFrame 'df'.
        """
        pass

    @abstractmethod
    def required_inputs(self):
        """
        Return a list describing the input columns or parameters needed.
        """
        pass
