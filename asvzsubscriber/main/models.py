from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# Create your models here.
class ASVZUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, username, institution_name, accepted_rules, password, **extra_fields):
        """
        Create and save a user with the given username, institution_name, accepted_rules and password.
        """
        if not username:
            raise ValueError("User must have a username")
        if not institution_name:
            raise ValueError("User must have a institution_name")
        if not accepted_rules:
            raise ValueError("User must have accepted the rules")

        user_obj = self.model(
            username=username,
            institution_name=institution_name,
            accepted_rules=accepted_rules,
            **extra_fields
        )
        user_obj.set_password(password)
        user_obj.save(using=self._db)
        return user_obj

    def create_user(self, username, institution_name, accepted_rules, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, institution_name, accepted_rules, password, **extra_fields)

    def create_superuser(self, username, institution_name, accepted_rules, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, institution_name, accepted_rules, password, **extra_fields)

    '''
    def with_perm(self, perm, is_active=True, include_superusers=True, backend=None, obj=None):
        if backend is None:
            backends = auth._get_backends(return_tuples=True)
            if len(backends) == 1:
                backend, _ = backends[0]
            else:
                raise ValueError(
                    'You have multiple authentication backends configured and '
                    'therefore must provide the `backend` argument.'
                )
        elif not isinstance(backend, str):
            raise TypeError(
                'backend must be a dotted import path string (got %r).'
                % backend
            )
        else:
            backend = auth.load_backend(backend)
        if hasattr(backend, 'with_perm'):
            return backend.with_perm(
                perm,
                is_active=is_active,
                include_superusers=include_superusers,
                obj=obj,
            )
        return self.none()
        '''


class ASVZUser(AbstractBaseUser, PermissionsMixin):
    username: models.CharField = models.CharField(
        _('username'),
        max_length=20,
        unique=True,
        primary_key=True,
        help_text=_('Required. Your ETHZ, UZH or ASVZ username.'),
        error_messages={
                         'unique': _("A user with that username already exists."),
                     },
    )
    open_password: models.CharField = models.CharField(max_length=4000, default="")

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

    date_joined: models.DateTimeField = models.DateTimeField(_('date joined'), default=timezone.now)

    institution_name: models.CharField = models.CharField(_('institution'), max_length=5, choices=[('ETHZ', 'ETHZ'), ('UZH', 'UZH'), ('ASVZ', 'ASVZ')], default='ETHZ')
    bearerToken: models.CharField = models.CharField(_('bearerToken'), max_length=4000, default="")
    valid_until: models.DateTimeField = models.DateTimeField(_('valid date for bearertoken'), default=timezone.now)
    accepted_rules: models.BooleanField = models.BooleanField(default=False)
    is_updating: models.BooleanField = models.BooleanField(default=False)
    first_login_check: models.BooleanField = models.BooleanField(default=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['institution_name', 'accepted_rules']

    objects = ASVZUserManager()

    def get_bearertoken_valid(self):
        return f"{self.user.__str__()} - {self.valid_until.__str__()[:16]}"


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

