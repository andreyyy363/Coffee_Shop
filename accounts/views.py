from datetime import datetime
import re
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, get_user_model
from django.shortcuts import render, redirect, get_object_or_404

from .forms import (
    LoginForm, SignUpForm, ForgotPasswordForm, ResetPasswordForm,
    ProfileForm, ChangePasswordForm
)
from .models import EmailVerificationToken, PasswordResetToken

User = get_user_model()


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()

            if not user.email_verified:
                messages.warning(request, 'Please verify your email first')
                return redirect('accounts:resend_verification')

            login(request, user)

            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)

            messages.success(request, f'Welcome, {user.display_name}!')

            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()

            token = EmailVerificationToken.objects.create(user=user)

            verification_url = request.build_absolute_uri(
                reverse('accounts:verify_email', kwargs={'token': token.token})
            )
            send_mail(
                'Email Verification - KAVASOUL',
                f'Please verify your email by clicking this link: {verification_url}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )

            messages.success(request, 'Registration successful! Please check your email to verify.')
            return redirect('accounts:login')
    else:
        form = SignUpForm()

    return render(request, 'accounts/signup.html', {'form': form})


def verify_email(request, token):
    verification = get_object_or_404(EmailVerificationToken, token=token)

    if verification.is_valid:
        verification.user.email_verified = True
        verification.user.save()
        verification.used = True
        verification.save()
        messages.success(request, 'Your email has been verified! You can now log in.')
    else:
        messages.error(request, 'This link is invalid or expired.')

    return redirect('accounts:login')


def resend_verification(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email, email_verified=False)
            user.verification_tokens.update(used=True)
            token = EmailVerificationToken.objects.create(user=user)

            verification_url = request.build_absolute_uri(
                reverse('accounts:verify_email', kwargs={'token': token.token})
            )
            send_mail(
                'Email Verification - KAVASOUL',
                f'Please verify your email by clicking this link: {verification_url}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
            messages.success(request, 'Email sent! Please check your inbox.')

        except User.DoesNotExist:
            messages.error(request, 'User not found or already verified.')

    return render(request, 'accounts/resend_verification.html')


def forgot_password(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email=email)
            user.password_reset_tokens.update(used=True)
            token = PasswordResetToken.objects.create(user=user)

            send_mail(
                'Password Reset - KAVASOUL',
                f'Your password reset code: {token.code}\n\nThis code is valid for 1 hour.',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )

            messages.success(request, 'Code sent to your email.')
            return redirect('accounts:reset_password', email=email)
    else:
        form = ForgotPasswordForm()

    return render(request, 'accounts/forgot_password.html', {'form': form})


def reset_password(request, email):
    """Handle password reset with code."""
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('accounts:forgot_password')

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']

            token = user.password_reset_tokens.filter(
                code=code, used=False
            ).first()

            if token and token.is_valid:
                user.set_password(form.cleaned_data['new_password'])
                user.save()
                token.used = True
                token.save()

                messages.success(request, 'Password changed successfully! You can now log in.')
                return redirect('accounts:login')
            else:
                messages.error(request, 'Invalid or expired code.')
    else:
        form = ResetPasswordForm()

    return render(request, 'accounts/reset_password.html', {'form': form, 'email': email})


@login_required
def account_settings(request):
    profile_form = ProfileForm(instance=request.user)
    password_form = ChangePasswordForm(request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_username':
            username = request.POST.get('username', '').strip()
            if username:
                if len(username) < 3:
                    messages.error(request, 'Username must be at least 3 characters long.')
                elif not re.match(r'^[a-zA-Z0-9_]+$', username):
                    messages.error(request, 'Username can only contain letters, numbers and underscores.')
                elif User.objects.filter(username__iexact=username).exclude(pk=request.user.pk).exists():
                    messages.error(request, 'This username is already taken.')
                else:
                    request.user.username = username
                    request.user.save()
                    messages.success(request, 'Username updated.')
            else:
                request.user.username = ''
                request.user.save()
                messages.success(request, 'Username cleared.')

        elif action == 'update_profile':
            profile_form = ProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profile updated.')
            else:
                for field, errors in profile_form.errors.items():
                    for error in errors:
                        messages.error(request, error)

        elif action == 'change_password':
            password_form = ChangePasswordForm(request.user, request.POST)
            if password_form.is_valid():
                request.user.set_password(password_form.cleaned_data['new_password'])
                request.user.save()
                login(request, request.user)
                messages.success(request, 'Password changed.')
            else:
                for field, errors in password_form.errors.items():
                    for error in errors:
                        messages.error(request, error)

        elif action == 'update_birth_date':
            birth_date_str = request.POST.get('birth_date')
            if birth_date_str:
                if not request.user.can_change_birth_date:
                    messages.error(request, f'You can change your birthday in '
                                            f'{request.user.days_until_birth_date_change} days.')
                else:
                    try:
                        new_birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
                        # Basic validation
                        today = timezone.now().date()
                        if new_birth_date > today:
                            messages.error(request, 'Birth date cannot be in the future.')
                        elif (today.year - new_birth_date.year) > 120:
                            messages.error(request, 'Please enter a valid birth date.')
                        else:
                            request.user.birth_date = new_birth_date
                            request.user.birth_date_changed_at = timezone.now()
                            request.user.save()
                            messages.success(request, 'Birthday updated! You may receive a special discount '
                                                      'around this date.')
                    except ValueError:
                        messages.error(request, 'Invalid date format.')

        return redirect('accounts:settings')

    return render(request, 'accounts/settings.html', {
        'profile_form': profile_form,
        'password_form': password_form,
    })


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')
