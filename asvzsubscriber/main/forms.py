# Copyright by your friendly neighborhood SaunaLord

import pytz
from random import random
from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError

from .asvz_crawler import encrypt_passphrase
from .models import ASVZUser, ASVZToken


class ASVZEventForm(forms.Form):
    Events = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple())

    def __init__(self, *args, **kwargs):
        super(ASVZEventForm, self).__init__(*args, **kwargs)
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
        fields = ["first_name", "last_name", "username", "password"]
        widgets = {
            'password': forms.PasswordInput(attrs={'autocomplete': 'new-password'})
        }

    def _post_clean(self):
        super()._post_clean()
        password = self.cleaned_data.get('password')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except ValidationError as error:
                self.add_error('password', error)
        return

    def save(self, commit=True):
        user: ASVZUser = super().save(commit=False)
        user.username = self.cleaned_data.get('username')
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        user.accepted_rules = self.cleaned_data.get('accepted_rules')
        password = self.cleaned_data.get('password')
        user.open_password = encrypt_passphrase(password)
        user.set_password(password)

        if commit:
            user.save()
        return user


class ASVZUserChangeForm(forms.Form):
    """
    A form that lets a user change their profile.
    """
    error_messages = {
        'password_incorrect': _("Your old password was entered incorrectly. Please enter it again."),
        'password_mismatch': _('The two password fields didn’t match.'),
    }
    old_password = forms.CharField(
        label=_("Old password"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'autofocus': True}),
    )

    new_username = forms.CharField(
        label=_('New usename - your ASVZ login name'),
        min_length=1,
        max_length=50,
    )

    new_password = forms.CharField(
        label=_("New password - your ASVZ password"),
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        strip=False,
    )

    field_order = ['old_password', 'new_username', 'new_password']

    def __init__(self, user, *args, **kwargs):
        self.user: ASVZUser = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        """
        Validate that the old_password field is correct.
        """
        old_password = self.cleaned_data.get("old_password")
        if not self.user.check_password(old_password):
            raise ValidationError(
                self.error_messages['password_incorrect'],
                code='password_incorrect',
            )
        return old_password

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        password_validation.validate_password(password, self.user)
        return password

    def save(self, commit=True):
        self.user.username = self.cleaned_data.get('new_username')
        password = self.cleaned_data.get("new_password")
        self.user.open_password = encrypt_passphrase(password)
        self.user.set_password(password)
        self.user.account_verified = False

        token = ASVZToken.objects.get_or_create(user=self.user)
        token.bearer_token = ""
        token.valid_until = timezone.datetime.now(tz=pytz.timezone('Europe/Zurich')) - timezone.timedelta(hours=4)

        if commit:
            self.user.save()
            token.save()
        return self.user
