from abc import ABC, abstractmethod
from string import Template
import os

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
    Abstract base class for transformations with enhanced placeholder support
    """
    name = "Base Transformation"
    description = "A base class for transformations"
    predefined_output = False  # Add this class variable

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
        """
        Enhanced placeholder replacement with user info/resume support
        """
        def replace_placeholders(text, row):
            try:
                # Start with row data
                context = row.to_dict()
                # Add user info if not already in row
                if 'user_info' not in context:
                    if os.path.exists('user_info.txt'):
                        with open('user_info.txt', 'r', encoding='utf-8') as f:
                            context['user_info'] = f.read()
                
                # Add resume if not already in row
                if 'user_resume' not in context:
                    if os.path.exists('user_resume.txt'):
                        with open('user_resume.txt', 'r', encoding='utf-8') as f:
                            context['user_resume'] = f.read()
                
                # Perform substitution
                return SafeTemplate(text).substitute(**context)
            except Exception as e:
                print(f"Placeholder substitution error: {e}")
                return text
        return replace_placeholders