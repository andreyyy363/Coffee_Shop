import secrets
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser, BaseUserManager

BIRTH_DATE_CHANGE_COOLDOWN_DAYS = 365


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('manager', 'Manager'),
        ('admin', 'Administrator'),
    ]

    username = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    email_verified = models.BooleanField(default=False)

    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)

    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    birth_date = models.DateField(null=True, blank=True, verbose_name='Birth Date')
    birth_date_changed_at = models.DateTimeField(null=True, blank=True, verbose_name='Birth Date Changed At')

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email

    @property
    def display_name(self):
        return self.username or self.first_name or self.email.split('@')[0]

    @property
    def is_manager(self):
        return self.role in ['manager', 'admin']

    @property
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser

    @property
    def can_change_birth_date(self):
        if not self.birth_date or not self.birth_date_changed_at:
            return True
        return (timezone.now() - self.birth_date_changed_at).days >= BIRTH_DATE_CHANGE_COOLDOWN_DAYS

    @property
    def days_until_birth_date_change(self):
        if self.can_change_birth_date:
            return 0
        return BIRTH_DATE_CHANGE_COOLDOWN_DAYS - (timezone.now() - self.birth_date_changed_at).days


class EmailVerificationToken(models.Model):
    """Token for email verification."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Email Verification Token'
        verbose_name_plural = 'Email Verification Tokens'

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=6)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    used = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Password Reset Token'
        verbose_name_plural = 'Password Reset Tokens'

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.code:
            self.code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=1)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at
