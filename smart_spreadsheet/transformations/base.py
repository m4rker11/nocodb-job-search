from abc import ABC, abstractmethod
from string import Template

class SafeTemplate(Template):
    delimiter = '{{'
    pattern = r'''
    \{\{(?:
    (?P<escaped>\{\{)|
    (?P<named>[_a-z][_a-z0-9]*)\}\}|
    (?P<braced>[_a-z][_a-z0-9]*)\}\}|
    (?P<invalid>)
    )
    '''

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
    @classmethod
    def get_placeholder_wrapper(cls):
        """Default placeholder replacement method"""
        def replace_placeholders(text, row):
            try:
                return SafeTemplate(text).substitute(**row.to_dict())
            except:
                return text
        return replace_placeholders
