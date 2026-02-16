"""
URL Configuration for Clearance Application
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register_student, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('student/clearance/start/', views.start_clearance, name='start_clearance'),
    path('student/document/<int:document_id>/delete/', views.delete_document, name='delete_document'),
    path('student/certificate/download/', views.download_clearance_certificate, name='download_certificate'),
    path('officer/clearance/<int:clearance_id>/review/', views.review_clearance, name='review_clearance'),
    path('officer/history/', views.officer_history, name='officer_history'),
    path('admins/departments/', views.manage_departments, name='manage_departments'),
    path('admins/departments/<int:department_id>/edit/', views.edit_department, name='edit_department'),
    path('admins/officers/', views.manage_officers, name='manage_officers'),
    path('admins/clearances/', views.view_all_clearances, name='view_all_clearances'),
    path('admins/clearances/<int:clearance_id>/', views.view_clearance_detail, name='view_clearance_detail'),
    path('admins/audit-logs/', views.audit_logs, name='audit_logs'),
]