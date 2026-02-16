"""
Django Admin Configuration for Clearance System
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (User, Faculty, Department, Clearance, ClearanceApproval, 
                     Document, AuditLog, SystemSettings)


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    """Faculty Admin"""
    list_display = ['name', 'code', 'dean_name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'dean_name']
    ordering = ['name']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin"""
    list_display = ['email', 'full_name', 'matric_number', 'role', 'faculty', 'department', 'faculty_assignment', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'faculty', 'department']
    search_fields = ['email', 'full_name', 'matric_number']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'matric_number')}),
        ('Role & Access', {'fields': ('role', 'faculty', 'department', 'faculty_assignment')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'role', 'password1', 'password2'),
        }),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Department Admin"""
    list_display = ['order', 'name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['order']


@admin.register(Clearance)
class ClearanceAdmin(admin.ModelAdmin):
    """Clearance Admin"""
    list_display = ['student', 'status', 'current_department', 'date_created', 'date_completed']
    list_filter = ['status', 'current_department', 'date_created']
    search_fields = ['student__full_name', 'student__matric_number']
    ordering = ['-date_created']
    readonly_fields = ['date_created', 'date_submitted', 'date_completed', 'last_updated']


@admin.register(ClearanceApproval)
class ClearanceApprovalAdmin(admin.ModelAdmin):
    """Clearance Approval Admin"""
    list_display = ['clearance', 'department', 'officer', 'status', 'timestamp']
    list_filter = ['status', 'department', 'timestamp']
    search_fields = ['clearance__student__full_name', 'department__name']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp', 'updated_at']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Document Admin"""
    list_display = ['clearance', 'document_type', 'file_name', 'file_size', 'uploaded_at']
    list_filter = ['document_type', 'uploaded_at']
    search_fields = ['clearance__student__full_name', 'file_name']
    ordering = ['-uploaded_at']
    readonly_fields = ['uploaded_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Audit Log Admin"""
    list_display = ['user', 'action', 'description', 'ip_address', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__full_name', 'description']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    """System Settings Admin"""
    list_display = ['key', 'value', 'updated_at', 'updated_by']
    search_fields = ['key', 'description']
    ordering = ['key']
    readonly_fields = ['updated_at']