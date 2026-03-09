from django import forms
from .models import Artisan, Product, Buyer, Order


class ArtisanForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create a strong password'}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Re-enter your password'}),
    )

    class Meta:
        model = Artisan
        fields = ['name', 'email', 'phone', 'location', 'state', 'language', 'craft_type', 'story', 'photo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Village/City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'language': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('Hindi', 'Hindi'), ('Tamil', 'Tamil'), ('Bengali', 'Bengali'),
                ('Telugu', 'Telugu'), ('Marathi', 'Marathi'), ('Gujarati', 'Gujarati'),
                ('Kannada', 'Kannada'), ('Malayalam', 'Malayalam'), ('Odia', 'Odia'),
                ('Punjabi', 'Punjabi'), ('Rajasthani', 'Rajasthani'), ('Urdu', 'Urdu'),
                ('English', 'English'),
            ]),
            'craft_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Madhubani Painting, Pottery'}),
            'story': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell us about your craft journey... (or speak using the mic button)'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if email and Artisan.objects.filter(email=email).exists():
            raise forms.ValidationError('An artisan with this email already exists.')
        return email or None

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password', '')
        cpw = cleaned.get('confirm_password', '')
        if pw and cpw and pw != cpw:
            self.add_error('confirm_password', 'Passwords do not match.')
        if pw and len(pw) < 6:
            self.add_error('password', 'Password must be at least 6 characters.')
        return cleaned


class BuyerRegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create a password'}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Re-enter password'}),
    )

    class Meta:
        model = Buyer
        fields = ['name', 'email', 'phone', 'location']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number (optional)'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City (optional)'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if email and Buyer.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password', '')
        cpw = cleaned.get('confirm_password', '')
        if pw and cpw and pw != cpw:
            self.add_error('confirm_password', 'Passwords do not match.')
        if pw and len(pw) < 6:
            self.add_error('password', 'Password must be at least 6 characters.')
        return cleaned


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['message', 'quantity']
        widgets = {
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Hi, I am interested in this product...'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'value': 1}),
        }


class ProductUploadForm(forms.ModelForm):
    voice_note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Describe your product in your own words... (or use mic button)'
        }),
        help_text="Tell us about this product — the AI will use this to create the listing"
    )

    class Meta:
        model = Product
        fields = ['image', 'price']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'id': 'product-image-input'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Your asking price in ₹ (optional)', 'step': '0.01'}),
        }


class ProductEditForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['title', 'description', 'cultural_story', 'category', 'art_form',
                  'materials', 'techniques', 'price', 'tags', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'cultural_story': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'art_form': forms.TextInput(attrs={'class': 'form-control'}),
            'materials': forms.TextInput(attrs={'class': 'form-control'}),
            'techniques': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tags': forms.TextInput(attrs={'class': 'form-control'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
