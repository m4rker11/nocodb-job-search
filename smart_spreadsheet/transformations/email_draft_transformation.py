# transformations/email_draft_transformation.py

from transformations.base import BaseTransformation
#TODO ADD AI
class EmailDraftTransformation(BaseTransformation):
    name = "Email Draft Generator"
    description = "Auto-generates email subject/body columns from row data."

    def required_inputs(self):
        # Example: we require columns for "ToEmail" and "RecipientName"
        return ["Recipient Email Column", "Recipient Name Column"]

    def transform(self, df, output_col_name, *args):
        """
        We'll define new columns like <output_col_name>_subject and
        <output_col_name>_body for each row.
        """
        if len(args) < 2:
            raise ValueError("Need two input columns: recipient email, recipient name")

        email_col, name_col = args[0], args[1]

        subject_col = f"{output_col_name}_subject"
        body_col = f"{output_col_name}_body"

        # Generate a subject
        df[subject_col] = df[name_col].apply(
            lambda name: f"Hello {name}, Quick Follow-Up"
        )

        # Generate a simple body
        df[body_col] = df.apply(
            lambda row: (
                f"Dear {row[name_col]},\n\n"
                "I'm reaching out to follow up on our conversation.\n\n"
                "Best regards,\n"
                "Your Company"
            ),
            axis=1
        )

        return df
