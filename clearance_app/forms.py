"""
Forms for Ajayi Crowther University Online Clearance System
"""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from .models import User, Clearance, Document, ClearanceApproval, Department
from .validators import validate_matric_number, validate_document_upload


class StudentRegistrationForm(UserCreationForm):
    """Form for student registration"""
    
    full_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your full name'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your email address'
        })
    )
    
    faculty = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Select your faculty'
    )
    
    matric_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g., 20H12345 or ACU20201234'
        }),
        help_text='Enter your matric number in the correct format'
    )
    
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter password'
        })
    )
    
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm password'
        })
    )
    
    class Meta:
        model = User
        fields = ['full_name', 'email', 'faculty', 'matric_number', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Faculty
        self.fields['faculty'].queryset = Faculty.objects.filter(is_active=True)
    
    def clean_matric_number(self):
        """Validate matric number format"""
        matric_number = self.cleaned_data.get('matric_number')
        
        # Validate format
        validate_matric_number(matric_number)
        
        # Check for duplicates
        if User.objects.filter(matric_number=matric_number).exists():
            raise ValidationError('This matric number is already registered.')
        
        return matric_number
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'student'
        if commit:
            user.save()
            # Create clearance record for student
            Clearance.objects.create(student=user, status='not_started')
        return user


class UserLoginForm(AuthenticationForm):
    """Custom login form"""
    
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your email'
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your password'
        })
    )


class DocumentUploadForm(forms.Form):
    """Form for uploading clearance documents"""
    
    DOCUMENT_TYPE_CHOICES = [
        ('fee_receipt', 'School Fee Receipt'),
        ('id_card', 'ID Card'),
        ('other', 'Other Document'),
    ]
    
    document_type = forms.ChoiceField(
        choices=DOCUMENT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-file-input',
            'accept': '.pdf,.jpg,.jpeg,.png'
        }),
        help_text='Allowed formats: PDF, JPG, PNG (Max 5MB)'
    )
    
    def clean_file(self):
        """Validate uploaded file"""
        file = self.cleaned_data.get('file')
        if file:
            validate_document_upload(file)
        return file


class ClearanceApprovalForm(forms.ModelForm):
    """Form for department officers to approve/reject clearance"""
    
    STATUS_CHOICES = [
        ('approved', 'Approve'),
        ('rejected', 'Reject'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-radio'})
    )
    
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Add comment (required if rejecting)',
            'rows': 4
        })
    )
    
    class Meta:
        model = ClearanceApproval
        fields = ['status', 'comment']
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        comment = cleaned_data.get('comment')
        
        # Comment is mandatory when rejecting
        if status == 'rejected' and not comment:
            raise ValidationError('Comment is required when rejecting a clearance.')
        
        return cleaned_data


class DepartmentForm(forms.ModelForm):
    """Form for creating/editing departments"""
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Department name'
        })
    )
    
    order = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Workflow order (1, 2, 3...)'
        }),
        help_text='Order in which clearance is processed'
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Department description',
            'rows': 3
        })
    )
    
    class Meta:
        model = Department
        fields = ['name', 'order', 'description', 'is_active']
        widgets = {
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'})
        }


class OfficerCreationForm(forms.ModelForm):
    """Form for creating department officers"""
    
    full_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Officer full name'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Officer email'
        })
    )
    
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    faculty_assignment = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Only for Faculty department officers - assign to specific faculty'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Set password'
        })
    )
    
    class Meta:
        model = User
        fields = ['full_name', 'email', 'department', 'faculty_assignment', 'password']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Faculty
        self.fields['faculty_assignment'].queryset = Faculty.objects.filter(is_active=True)
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'officer'
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class ClearanceSearchForm(forms.Form):
    """Form for searching clearances"""
    
    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search by name or matric number'
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + Clearance.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    department = forms.ModelChoiceField(
        required=False,
        queryset=Department.objects.filter(is_active=True),
        empty_label='All Departments',
        widget=forms.Select(attrs={'class': 'form-select'})
    )