from django import forms


class ImportOccurrencesForm(forms.Form):
    file = forms.FileField()
