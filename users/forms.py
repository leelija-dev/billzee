from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Profile
from .utils import get_country_choices

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class CustomUserForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name']

class ProfileForm(forms.ModelForm):
    country = forms.ChoiceField(
        choices=[],  # Will be set dynamically in __init__
        widget=forms.Select(attrs={
            'id': 'id_country',
            'class': 'country-selector p-4'
        })
    )

    class Meta:
        model = Profile
        fields = [
            'company_name', 'company_email', 'password', 'phone_number', 'address',
            'city', 'state', 'country', 'pin_or_zip', 'gst_id'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3, 'style': 'padding: 10px;'}),
            'password': forms.PasswordInput(render_value=True),
            'gst_id': forms.TextInput(attrs={'data-india-only': 'true'}),
            'state': forms.Select(choices=[]),
            'city': forms.Select(choices=[]),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['country'].choices = get_country_choices()  # Fetch countries dynamically
        self.fields['gst_id'].required = False  # GST ID is optional initially

    def clean(self):
        cleaned_data = super().clean()
        country = cleaned_data.get('country', '').strip().upper()
        gst_id = cleaned_data.get('gst_id', '').strip()
        if country == 'IN' and not gst_id:
            self.add_error('gst_id', 'GST ID is required for India')
        elif country != 'IN' and gst_id:
            self.add_error('gst_id', 'GST ID should only be provided for India')
        return cleaned_data