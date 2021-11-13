from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db.models import DateTimeField, CharField, URLField, BooleanField, OneToOneField, TextChoices, ForeignKey, \
    CASCADE, Model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# Create your models here.
class ASVZUserManager(BaseUserManager):
    def create_user(self, username, institution_name, accepted_rules, password=None):
        if not username:
            raise ValueError("Users must have a username")
        if not institution_name:
            raise ValueError("Users must have a institution_name")
        if not accepted_rules:
            raise ValueError("Users must have accepted the rules")

        user_obj = self.model(
            username=username,
            institution_name=institution_name,
            accepted_rules=accepted_rules
        )
        user_obj.set_password(password)
        user_obj.save(using=self._db)
        return user_obj

    def create_superuser(self, username, institution_name, accepted_rules, password=None):
        user_obj = self.create_user(username, institution_name, accepted_rules, password)
        user_obj.is_superuser = True
        user_obj.is_staff = True
        user_obj.save(using=self._db)
        return user_obj


class ASVZUser(AbstractBaseUser, PermissionsMixin):
    username_validator = UnicodeUsernameValidator()
    username: CharField(
        _('username'),
        max_length=50,
        unique=True,
        help_text=_('Required. Your ETHZ, UZH or ASVZ username.'),
        validators=[username_validator],
        error_messages={
                         'unique': _("A user with that username already exists."),
                     },
    )
    open_password: CharField(max_length=4000)
    is_staff = BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    is_superuser = BooleanField(
        _('admin'),
        default=False,
        help_text=_('Designates whether this user should have superuser rights.')
    )

    date_joined = DateTimeField(_('date joined'), default=timezone.now)

    institution_name: CharField(_('institution'), max_length=5, choices=['ETHZ', 'UZH', 'ASVZ'], default='ETHZ')
    bearerToken: CharField = CharField(_('bearerToken'), max_length=4000)
    valid_until: DateTimeField = DateTimeField(_('valid date for bearertoken'))
    accepted_rules: BooleanField = BooleanField(default=False)
    is_updating: BooleanField = BooleanField(default=False)
    first_login_check: BooleanField = BooleanField(default=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['institution_name', 'accepted_rules']

    objects = ASVZUserManager()

    def get_bearertoken_valid(self):
        return f"{self.user.__str__()} - {self.valid_until.__str__()[:16]}"


class ASVZEvent(Model):
    user: CharField = ForeignKey(ASVZUser, on_delete=CASCADE, related_name="user")
    url: URLField = URLField()
    sport_name: CharField = CharField(max_length=100)
    title: CharField = CharField(max_length=100)
    location: CharField = CharField(max_length=100)
    event_start_date: DateTimeField = DateTimeField()
    register_start_date: DateTimeField = DateTimeField()
    niveau_short_name: CharField = CharField(max_length=100)

    class Meta:
        unique_together = ("user", "url")

    def __str__(self):
        return f"{self.user.__str__()} - {self.url[-6:]}"

