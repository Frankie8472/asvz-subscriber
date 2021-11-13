from random import random
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class EventForm(forms.Form):
    Events = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple())

    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        self.fields['Events'].widget.attrs.update({'class': 'filled-in'})
        self.fields['Events'].widget.attrs.update({'id': f"{random()}_"})

    def set_choices(self, events):
        self.fields['Events'].choices = events


class NewUserForm(UserCreationForm):
    school = forms.ChoiceField()


    class Meta:
        model = User
        fields = ("username", "email", "password")

    def save(self, commit=True):
        user = super(NewUserForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user