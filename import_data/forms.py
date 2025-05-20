# import_data/forms.py

from django import forms


class CSVUploadForm(forms.Form):
    """
    Base form for handling CSV file uploads.
    """
    csv_file = forms.FileField()

    def clean_csv_file(self):
        """
        Validate that the uploaded file is a valid CSV.
        """
        file = self.cleaned_data.get('csv_file')

        if not file.name.endswith('.csv'):
            raise forms.ValidationError("File is not a valid CSV.")
        
        # Optionally, you can check the file's content type (MIME type) for additional validation
        if file.content_type != 'text/csv':
            raise forms.ValidationError("Uploaded file is not of type CSV.")

        return file


class ImportForm(CSVUploadForm):
    """
    Generic CSV upload form for legacy & bulk imports.
    Inherits from CSVUploadForm for CSV file handling.
    """
    pass


class PolicyAmendmentUploadForm(CSVUploadForm):
    """
    Upload a CSV to amend existing policies.
    Expected headers: membership_number + columns to update.
    """
    csv_file = forms.FileField(
        label="CSV file",
        widget=forms.FileInput(attrs={"accept": ".csv"}),
        help_text="Upload a CSV with membership_number and fields to amend."
    )


class LapsedReactivateUploadForm(CSVUploadForm):
    """
    Upload a CSV to reactivate lapsed policies.
    Expected headers: membership_number, optional arrears, new_start_date (YYYY-MM-DD).
    """
    csv_file = forms.FileField(
        label="CSV file",
        widget=forms.FileInput(attrs={"accept": ".csv"}),
        help_text=(
            "Upload a CSV with membership_number, optional "
            "arrears, and new_start_date (YYYY-MM-DD)."
        )
    )


class AgentOnboardingUploadForm(CSVUploadForm):
    """
    Upload a CSV to bulk-create agents.
    Expected headers:
      full_name, surname, id_number, passport_number,
      scheme_code, code, contact_number, commission_percentage
    """
    csv_file = forms.FileField(
        label="CSV file",
        widget=forms.FileInput(attrs={"accept": ".csv"}),
        help_text=(
            "Headers: full_name, surname, id_number, passport_number,"
            "scheme_code, code, contact_number, commission_percentage"
        )
    )
