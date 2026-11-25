from django import forms

TAILWIND_INPUT = (
    'w-full px-4 py-2.5 rounded-lg border border-gray-300 bg-white '
    'text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 '
    'focus:border-indigo-500 transition-colors'
)


class CSVUploadForm(forms.Form):
    """Form for uploading a bank-statement CSV file."""

    file = forms.FileField(
        label='CSV File',
        widget=forms.ClearableFileInput(attrs={
            'class': TAILWIND_INPUT,
            'accept': '.csv',
        }),
    )

    def clean_file(self):
        """Validate the uploaded file is a CSV under 2 MB."""
        uploaded = self.cleaned_data['file']

        if not uploaded.name.lower().endswith('.csv'):
            raise forms.ValidationError('Only .csv files are accepted.')

        max_size = 2 * 1024 * 1024  # 2 MB
        if uploaded.size > max_size:
            raise forms.ValidationError('File size must be under 2 MB.')

        return uploaded
