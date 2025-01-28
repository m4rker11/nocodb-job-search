from abc import ABC, abstractmethod
from string import Template
import os
from PyQt6.QtWidgets import QWidget

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
    def get_placeholder_wrapper(cls, extra_placeholders=None):
        """
        Returns a function that, given `text` and a row (a Series),
        will merge:
          1) row data (row.to_dict())
          2) user_info.txt content (if not already present)
          3) user_resume.txt content (if not already present)
          4) `extra_placeholders` (any transformation-specific placeholders)

        Then it performs SafeTemplate substitution.

        :param extra_placeholders: dict of additional placeholders
                                   e.g. {'user_template': '...', 'few_shot': '...'}
        """
        if extra_placeholders is None:
            extra_placeholders = {}

        def replace_placeholders(text, row):
            try:
                # 1) Gather row data
                context = row.to_dict()

                # 2) Add user_info if not in row
                if 'user_info' not in context:
                    if os.path.exists('user_info.txt'):
                        with open('user_info.txt', 'r', encoding='utf-8') as f:
                            context['user_info'] = f.read()
                
                # 3) Add resume if not in row
                if 'user_resume' not in context:
                    if os.path.exists('user_resume.txt'):
                        with open('user_resume.txt', 'r', encoding='utf-8') as f:
                            context['user_resume'] = f.read()

                # 4) Merge in any extra placeholders from the transformation
                for key, val in extra_placeholders.items():
                    context[key] = val

                # 5) Perform substitution
                return SafeTemplate(text).substitute(**context)
            except Exception as e:
                print(f"Placeholder substitution error: {e}")
                return text

        return replace_placeholders
    
    def has_custom_settings(self) -> bool:
        """
        Override in subclasses. Return True if this transformation
        has custom, user-facing configuration.
        """
        return False

    def create_settings_widget(self, parent=None) -> QWidget | None:
        """
        Return a QWidget that holds custom settings fields (e.g. QLineEdit, QTextEdit).
        The host dialog will embed it in a 'Transformations' settings tab.
        """
        return None

    def load_custom_settings(self):
        """
        Called before creating the settings widget so you can
        load existing data (e.g. from a file).
        Return anything you want to pre-fill your widget's fields with.
        """
        return {}

    def save_custom_settings(self, widget_data: dict):
        """
        Called when the user hits "OK" in the settings dialog.
        `widget_data` is everything your widget collected 
        (text from line edits, checkboxes, etc.).
        Save them to a file or QSettings or wherever you like.
        """
        pass