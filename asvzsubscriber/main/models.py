# Copyright by your friendly neighborhood SaunaLord

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# Create your models here.
class ASVZUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, first_name, last_name, username, institution_name, accepted_rules, password, **extra_fields):
        """
        Create and save a user with the given username, institution_name, accepted_rules and password.
        """
        if not first_name:
            raise ValueError("User must have a first name")
        if not last_name:
            raise ValueError("User must have a last name")
        if not username:
            raise ValueError("User must have a username")
        if not institution_name:
            raise ValueError("User must have a institution_name")
        if not accepted_rules:
            raise ValueError("User must have accepted the rules")

        user_obj = self.model(
            first_name=first_name,
            last_name=last_name,
            username=username,
            institution_name=institution_name,
            accepted_rules=accepted_rules,
            **extra_fields
        )
        user_obj.set_password(password)
        user_obj.save(using=self._db)
        return user_obj

    def create_user(self, first_name, last_name, username, institution_name, accepted_rules, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('account_verified', False)
        extra_fields.setdefault('account_approved', False)

        if extra_fields.get('is_staff') is True:
            raise ValueError('Superuser must not have is_staff=True.')
        if extra_fields.get('is_superuser') is True:
            raise ValueError('Superuser must not have is_superuser=True.')
        if extra_fields.get('account_verified') is True:
            raise ValueError('Superuser must not have account_verified=True.')
        if extra_fields.get('account_approved') is True:
            raise ValueError('Superuser must not have account_approved=True.')
        return self._create_user(first_name, last_name, username, institution_name, accepted_rules, password, **extra_fields)

    def create_superuser(self, first_name, last_name, username, institution_name, accepted_rules, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('account_verified', True)
        extra_fields.setdefault('account_approved', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        if extra_fields.get('account_verified') is not True:
            raise ValueError('Superuser must have account_verified=True.')
        if extra_fields.get('account_approved') is not True:
            raise ValueError('Superuser must have account_approved=True.')

        return self._create_user(first_name, last_name, username, institution_name, accepted_rules, password, **extra_fields)


class ASVZUser(AbstractBaseUser):
    first_name: models.CharField = models.CharField(
        _('First name - required for identification'),
        max_length=30,
    )
    last_name: models.CharField = models.CharField(
        _('Last name - required for identification'),
        max_length=30,
    )
    username: models.CharField = models.CharField(
        _('Username - your institution login name'),
        max_length=20,
        unique=True,
        primary_key=True,
        error_messages={
                         'unique': _("A user with that username already exists."),
        },
    )

    institution_name: models.Field = models.CharField(
        _('Institution'),
        max_length=5,
        choices=[('ETHZ', 'ETHZ'), ('UZH', 'UZH'), ('ASVZ', 'ASVZ')],
        default='ETHZ',
    )

    password = models.CharField(
        _('Password - Required, your institution password'),
        max_length=128
    )

    open_password: models.CharField = models.CharField(
        max_length=4000,
        default="",
        help_text=_('Copy of the password. SHA256 enrypted. Used for automated ASVZ login.'),
    )

    is_active: models.BooleanField = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )

    is_staff: models.BooleanField = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )

    is_superuser = models.BooleanField(
        _('superuser status'),
        default=False,
        help_text=_(
            'Designates that this user has all permissions without '
            'explicitly assigning them.'
        ),
    )

    date_joined: models.DateTimeField = models.DateTimeField(_('date joined'), default=timezone.now)

    bearer_token: models.CharField = models.CharField(
        _('Bearer token'),
        max_length=4000,
        default="",
        help_text=_('Token for enrolling in the preferred lesson. Faster than multiple logins.'),
    )

    valid_until: models.DateTimeField = models.DateTimeField(
        _('Valid date for bearer token'),
        default=timezone.now,
        help_text=_('The bearer token is only valid for 2h. This is the tracker.'),
    )

    accepted_rules: models.BooleanField = models.BooleanField(
        _('Accepted rules - required, you have read and accepted the stated rules at the top of the page'),
        default=False,
    )

    is_updating: models.BooleanField = models.BooleanField(
        default=False,
        help_text=_('Indicates if the scheduler is updating this bearer token.'),
    )

    account_verified: models.BooleanField = models.BooleanField(
        default=False,
        help_text=_('Indicates if the account was verified by a "bearer token retrieval".'),
    )

    account_approved: models.BooleanField = models.BooleanField(
        default=False,
        help_text=_('Indicates whether the account has been approved by the administrator.'),
    )

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'institution_name', 'accepted_rules']

    objects = ASVZUserManager()

    def has_module_perms(self, app_label):
        """
        Return True if the user has any permissions in the given app label.
        Use similar logic as has_perm(), above.
        """
        # Active superusers have all permissions.
        return self.is_active and self.is_superuser

    def has_perm(self, perm, obj=None):
        return self.is_active and self.is_superuser

    def __str__(self):
        return f"{self.first_name.__str__()} {self.last_name.__str__()} - {self.institution_name.__str__()} - {self.username.__str__()} - {self.valid_until.__str__()[:16]}"


class ASVZEvent(models.Model):
    user: models.CharField = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user")
    url: models.URLField = models.URLField()
    sport_name: models.CharField = models.CharField(max_length=100)
    title: models.CharField = models.CharField(max_length=100)
    location: models.CharField = models.CharField(max_length=100)
    event_start_date: models.DateTimeField = models.DateTimeField()
    register_start_date: models.DateTimeField = models.DateTimeField()
    niveau_short_name: models.CharField = models.CharField(max_length=100)

    class Meta:
        unique_together = [["user", "url"]]

    def __str__(self):
        return f"{self.user.__str__()} - {self.url[-6:]}"
