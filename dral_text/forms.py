from django import forms


class ImportSheetForm(forms.Form):
    file = forms.FileField()
