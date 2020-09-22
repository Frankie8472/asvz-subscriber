from random import random

from django import forms


class EventForm(forms.Form):
    Events = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple())

    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        self.fields['Events'].widget.attrs.update({'class': 'filled-in'})
        self.fields['Events'].widget.attrs.update({'id': f"{random()}_"})

    def set_choices(self, events):
        self.fields['Events'].choices = events

