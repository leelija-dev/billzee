from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Profile

COUNTRY_CHOICES = [
    ('', 'Select Country'),
    ('india', 'India'),
    ('us', 'United States'),
    ('uk', 'United Kingdom'),
    # Add more countries as needed
]

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
        choices=COUNTRY_CHOICES,
        widget=forms.Select(attrs={
            'id': 'id_country',
            'class': 'country-selector '
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
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['gst_id'].required = False  # Start as not required

    def clean(self):
        cleaned_data = super().clean()
        country = cleaned_data.get('country', '').strip().lower()
        gst_id = cleaned_data.get('gst_id', '').strip()

        if country == 'india' and not gst_id:
            self.add_error('gst_id', 'GST ID is required for India')
        elif country != 'india' and gst_id:
            self.add_error('gst_id', 'GST ID should only be provided for India')
