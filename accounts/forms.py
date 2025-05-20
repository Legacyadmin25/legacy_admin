"""
Forms for the accounts application.

This module contains all the forms used for user authentication, profile management,
and role-based access control in the accounts app.
"""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm as BasePasswordChangeForm,
    PasswordResetForm as BasePasswordResetForm,
    SetPasswordForm as BaseSetPasswordForm,
    UserChangeForm as BaseUserChangeForm,
    UserCreationForm as BaseUserCreationForm,
)
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Profile

User = get_user_model()


class UserRegistrationForm(BaseUserCreationForm):
    """
    Form for user registration.
    """
    email = forms.EmailField(
        label=_('Email'),
        max_length=254,
        help_text=_('Required. Enter a valid email address.'),
    )
    phone = forms.CharField(
        label=_('Phone'),
        max_length=20,
        required=False,
        help_text=_('Enter your phone number (optional).'),
    )
    
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email required
        self.fields['email'].required = True
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
    
    def clean_email(self):
        """
        Validate that the email is unique.
        """
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_('A user with that email already exists.'))
        return email


class UserLoginForm(AuthenticationForm):
    """
    Form for user login.
    """
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            if field_name != 'remember_me':
                field.widget.attrs.update({'class': 'form-control'})


class ProfileUpdateForm(forms.ModelForm):
    """
    Form for updating a user's profile.
    """
    class Meta:
        model = Profile
        fields = [
            'phone', 'date_of_birth', 'address', 'city',
            'state', 'postal_code', 'country',
            'profile_picture', 'bio', 'is_verified', 'is_active'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'bio': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            if field_name != 'profile_picture':
                field.widget.attrs.update({'class': 'form-control'})
    
    def save(self, commit=True):
        """
        Save the profile instance.
        """
        profile = super().save(commit=False)
        if commit:
            profile.save()
        return profile


class PasswordChangeForm(BasePasswordChangeForm):
    """
    Form for changing a user's password.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})


class AdminPasswordChangeForm(forms.Form):
    """
    Form for an admin to change a user's password.
    """
    new_password1 = forms.CharField(
        label=_('New password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False,
    )
    new_password2 = forms.CharField(
        label=_('New password confirmation'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False,
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_new_password2(self):
        """
        Validate that the two password entries match.
        """
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError(_('The two password fields didn\'t match.'))
        
        return password2
    
    def save(self, commit=True):
        """
        Set the new password.
        """
        password = self.cleaned_data['new_password1']
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user


class EmailChangeForm(forms.Form):
    """
    Form for changing a user's email address.
    """
    new_email = forms.EmailField(
        label=_('New email address'),
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )
    current_password = forms.CharField(
        label=_('Current password'),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_current_password(self):
        """
        Validate that the current password is correct.
        """
        current_password = self.cleaned_data.get('current_password')
        if not self.user.check_password(current_password):
            raise ValidationError(_('Your current password was entered incorrectly.'))
        return current_password
    
    def clean_new_email(self):
        """
        Validate that the new email is not already in use.
        """
        new_email = self.cleaned_data.get('new_email')
        if User.objects.filter(email__iexact=new_email).exclude(pk=self.user.pk).exists():
            raise ValidationError(_('This email address is already in use.'))
        return new_email


class UserCreateForm(forms.ModelForm):
    """
    Form for creating a new user (admin only).
    """
    password1 = forms.CharField(
        label=_('Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text=_('Leave blank to generate a random password.'),
        required=False,
    )
    password2 = forms.CharField(
        label=_('Password confirmation'),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text=_('Enter the same password as above, for verification.'),
        required=False,
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'groups']
        widgets = {
            'groups': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            if field_name not in ['is_active', 'is_staff', 'groups']:
                field.widget.attrs.update({'class': 'form-control'})
    
    def clean_password2(self):
        """
        Validate that the two password entries match.
        """
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError(_('The two password fields didn\'t match.'))
        
        return password2
    
    def save(self, commit=True):
        """
        Save the user instance.
        """
        user = super().save(commit=False)
        
        # Set the password if provided
        if self.cleaned_data.get('password1'):
            user.set_password(self.cleaned_data['password1'])
        
        if commit:
            user.save()
            self.save_m2m()
        
        return user


class UserUpdateForm(forms.ModelForm):
    """
    Form for updating a user's details (admin only).
    """
    password1 = forms.CharField(
        label=_('Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text=_('Leave blank to keep the current password.'),
        required=False,
    )
    password2 = forms.CharField(
        label=_('Password confirmation'),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text=_('Enter the same password as above, for verification.'),
        required=False,
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'groups']
        widgets = {
            'groups': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            if field_name not in ['is_active', 'is_staff', 'groups']:
                field.widget.attrs.update({'class': 'form-control'})
    
    def clean_password2(self):
        """
        Validate that the two password entries match.
        """
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError(_('The two password fields didn\'t match.'))
        
        return password2
    
    def save(self, commit=True):
        """
        Save the user instance.
        """
        user = super().save(commit=False)
        
        # Set the password if provided
        if self.cleaned_data.get('password1'):
            user.set_password(self.cleaned_data['password1'])
        
        if commit:
            user.save()
            self.save_m2m()
        
        return user


class RoleForm(forms.ModelForm):
    """
    Form for creating and updating roles (groups).
    """
    class Meta:
        model = Group
        fields = ['name', 'permissions']
        widgets = {
            'permissions': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '15'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        
        # Group permissions by content type for better organization
        from django.contrib.auth.models import Permission
        from django.db.models import Prefetch
        
        # Prefetch related content types to avoid N+1 queries
        permissions = Permission.objects.select_related('content_type').order_by(
            'content_type__app_label', 'content_type__model', 'codename'
        )
        
        # Create a dictionary to organize permissions by app label
        permission_choices = {}
        for perm in permissions:
            app_label = perm.content_type.app_label
            if app_label not in permission_choices:
                permission_choices[app_label] = []
            permission_choices[app_label].append((perm.id, perm.name))
        
        # Convert the dictionary to a list of tuples for the choices
        choices = [(app_label, permission_choices[app_label]) for app_label in sorted(permission_choices.keys())]
        
        # Update the choices for the permissions field
        self.fields['permissions'].choices = choices
    
    def clean_name(self):
        """
        Validate that the role name is unique.
        """
        name = self.cleaned_data.get('name')
        if name and Group.objects.filter(name__iexact=name).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError(_('A role with this name already exists.'))
        return name
