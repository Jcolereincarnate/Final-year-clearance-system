"""
Validators for Ajayi Crowther University Online Clearance System
"""
import re
from django.core.exceptions import ValidationError
from django.conf import settings


def validate_matric_number(matric_number):
    patterns = [
        r'^\d{2}(H|M|S|L|ED|AGR|N|BMS|EV|EG)\d{5}$',
        r'^\d{2}(H|M|S|L|ED|AGR|N|BMS|EV|EG)\d{5}TS$',
        r'^ACU\d{4}\d{4}$',
        r'^ACU\d{4}\d{4}TS$',
    ]
    
    # Remove any spaces for validation
    clean_matric = matric_number.replace(' ', '')
    
    # Check if matches any pattern
    is_valid = any(re.match(pattern, clean_matric) for pattern in patterns)
    
    if not is_valid:
        raise ValidationError(
            'Invalid matric number format. Please use one of the following formats: '
            'YYCODE##### (e.g., 20H12345), '
            'YYCODE#####TS (e.g., 20H12345TS), '
            'ACU####-#### (e.g., ACU2020-1234), '
            'ACU####-####TS (e.g., ACU2020-1234TS). '
            'Valid codes: H, M, S, L, ED, AGR, N, BMS, EV, EG'
        )
    
    return True


def validate_file_extension(file):
    """
    Validate uploaded file extension
    Only allow: PDF, JPG, JPEG, PNG
    """
    allowed_extensions = getattr(settings, 'ALLOWED_DOCUMENT_TYPES', ['pdf', 'jpg', 'jpeg', 'png'])
    
    file_extension = file.name.split('.')[-1].lower()
    
    if file_extension not in allowed_extensions:
        raise ValidationError(
            f'Unsupported file type: .{file_extension}. '
            f'Allowed types: {", ".join(allowed_extensions)}'
        )
    
    return True


def validate_file_size(file):
    """
    Validate file size
    Maximum: 5MB
    """
    max_size = getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', 5242880)  # 5MB default
    
    if file.size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        raise ValidationError(
            f'File size exceeds maximum allowed size of {max_size_mb}MB. '
            f'Your file is {file.size / (1024 * 1024):.2f}MB'
        )
    
    return True


def validate_document_upload(file):
    """
    Combined validation for document uploads
    """
    validate_file_extension(file)
    validate_file_size(file)
    return True