"""
Database Models for Ajayi Crowther University Online Clearance System
"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.utils import timezone
import re


class UserManager(BaseUserManager):
    """Custom user manager for the clearance system"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class Faculty(models.Model):
    """
    Faculty model representing academic faculties
    Each student belongs to a faculty
    """
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=10, unique=True, help_text="e.g., SCI, ART, ENG")
    description = models.TextField(blank=True)
    dean_name = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Faculty'
        verbose_name_plural = 'Faculties'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with role-based access control
    Supports three roles: Student, Department Officer, Administrator
    """
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('officer', 'Department Officer'),
        ('admin', 'Administrator'),
    ]
    
    email = models.EmailField(unique=True, max_length=255)
    full_name = models.CharField(max_length=200)
    matric_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    
    # For students: their academic faculty
    faculty = models.ForeignKey('Faculty', on_delete=models.SET_NULL, 
                                null=True, blank=True, related_name='students',
                                help_text="Student's academic faculty")
    
    # For officers: the clearance department they work for
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='officers',
                                   help_text="Officer's clearance department")
    
    # For faculty officers: the specific faculty they handle (optional)
    faculty_assignment = models.ForeignKey('Faculty', on_delete=models.SET_NULL,
                                          null=True, blank=True, related_name='faculty_officers',
                                          help_text="For Faculty dept officers: which faculty they handle")
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.full_name} ({self.role})"
    
    def is_student(self):
        return self.role == 'student'
    
    def is_officer(self):
        return self.role == 'officer'
    
    def is_admin(self):
        return self.role == 'admin'
    
    def can_review_clearance(self, clearance):
        """Check if this officer can review a specific clearance"""
        if not self.is_officer():
            return False
        
        # If officer is not in Faculty department, they can review all clearances
        if self.department.name != 'Faculty':
            return True
        
        # If officer is in Faculty department, check faculty assignment
        if self.faculty_assignment:
            return clearance.student.faculty == self.faculty_assignment
        
        # If no faculty assignment, can review all faculties
        return True


class Department(models.Model):
    """
    Department model representing clearance departments
    Order field determines workflow sequence
    """
    name = models.CharField(max_length=100, unique=True)
    order = models.IntegerField(unique=True, help_text="Workflow sequence order")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
    
    def __str__(self):
        return f"{self.order}. {self.name}"
    
    def get_next_department(self):
        """Get the next department in workflow sequence"""
        try:
            return Department.objects.filter(order__gt=self.order, is_active=True).first()
        except Department.DoesNotExist:
            return None


class Clearance(models.Model):
    """
    Main Clearance model tracking student clearance progress
    """
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('rejected', 'Rejected'),
        ('approved', 'Fully Cleared'),
    ]
    
    student = models.OneToOneField(User, on_delete=models.CASCADE, related_name='clearance')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    current_department = models.ForeignKey(Department, on_delete=models.SET_NULL, 
                                          null=True, blank=True, related_name='current_clearances')
    
    # Timestamps
    date_created = models.DateTimeField(auto_now_add=True)
    date_submitted = models.DateTimeField(null=True, blank=True)
    date_completed = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    # Additional info
    remarks = models.TextField(blank=True, help_text="Admin remarks or notes")
    
    class Meta:
        verbose_name = 'Clearance'
        verbose_name_plural = 'Clearances'
        ordering = ['-date_created']
    
    def __str__(self):
        return f"Clearance for {self.student.full_name} - {self.status}"
    
    def get_progress_percentage(self):
        """Calculate clearance progress percentage"""
        total_departments = Department.objects.filter(is_active=True).count()
        if total_departments == 0:
            return 0
        
        approved_count = self.approvals.filter(status='approved').count()
        return int((approved_count / total_departments) * 100)
    
    def is_fully_approved(self):
        """Check if all departments have approved"""
        total_departments = Department.objects.filter(is_active=True).count()
        approved_count = self.approvals.filter(status='approved').count()
        return approved_count == total_departments and total_departments > 0
    
    def move_to_next_department(self):
        """Move clearance to next department in workflow"""
        if self.current_department:
            next_dept = self.current_department.get_next_department()
            self.current_department = next_dept
            if next_dept is None:
                # All departments done
                if self.is_fully_approved():
                    self.status = 'approved'
                    self.date_completed = timezone.now()
            self.save()


class ClearanceApproval(models.Model):
    """
    Tracks individual department approvals
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    clearance = models.ForeignKey(Clearance, on_delete=models.CASCADE, related_name='approvals')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='approvals')
    officer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approvals_made')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    comment = models.TextField(blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Clearance Approval'
        verbose_name_plural = 'Clearance Approvals'
        unique_together = ['clearance', 'department']
        ordering = ['department__order']
    
    def __str__(self):
        return f"{self.department.name} - {self.status} for {self.clearance.student.full_name}"


class Document(models.Model):
    """
    Model for storing uploaded documents
    """
    DOCUMENT_TYPES = [
        ('fee_receipt', 'School Fee Receipt'),
        ('id_card', 'ID Card'),
        ('other', 'Other Document'),
    ]
    
    clearance = models.ForeignKey(Clearance, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='clearance_documents/%Y/%m/')
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text="File size in bytes")
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.document_type} - {self.clearance.student.full_name}"
    
    def get_file_extension(self):
        """Get file extension"""
        return self.file.name.split('.')[-1].lower()


class AuditLog(models.Model):
    """
    Audit log for tracking all system actions
    """
    ACTION_CHOICES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('clearance_start', 'Clearance Started'),
        ('clearance_submit', 'Clearance Submitted'),
        ('approval_approve', 'Approved by Officer'),
        ('approval_reject', 'Rejected by Officer'),
        ('document_upload', 'Document Uploaded'),
        ('admin_override', 'Admin Override'),
        ('user_create', 'User Created'),
        ('user_update', 'User Updated'),
        ('department_create', 'Department Created'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Optional reference to related objects
    clearance = models.ForeignKey(Clearance, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action} by {self.user} at {self.timestamp}"


class SystemSettings(models.Model):
    """
    System-wide settings and configurations
    """
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'
    
    def __str__(self):
        return self.key