from random import random
from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError

from main.asvz_crawler import encrypt_passphrase
from main.models import ASVZUser


class EventForm(forms.Form):
    Events = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple())

    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        self.fields['Events'].widget.attrs.update({'class': 'filled-in'})
        self.fields['Events'].widget.attrs.update({'id': f"{random()}_"})

    def set_choices(self, events):
        self.fields['Events'].choices = events


class ASVZUserCreationForm(forms.ModelForm):
    error_messages = {
        'password_mismatch': _('The two password fields didn’t match.'),
    }

    accepted_rules: forms.BooleanField = forms.BooleanField(
        label=_('Accepted rules - required, you have read and accepted the stated rules at the top of the page'),
        required=True,
        initial=False,
    )

    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name", "institution_name", "username", "password"]
        widgets = {
            'password': forms.PasswordInput(attrs={'autocomplete': 'new-password'})
        }

    def _post_clean(self):
        password = self.cleaned_data.get('password2')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except ValidationError as error:
                self.add_error('password2', error)
        return

    def save(self, commit=True):
        user: ASVZUser = super().save(commit=False)
        user.username = self.cleaned_data['username']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.institution_name = self.cleaned_data['institution_name']
        user.accepted_rules = self.cleaned_data['accepted_rules']
        password = self.cleaned_data['password']
        user.open_password = encrypt_passphrase(password)
        user.set_password(password)

        if commit:
            user.save()
            print(f"\n\n HERE {user.username} {user.first_name} {user.accepted_rules} \n")
        return user

