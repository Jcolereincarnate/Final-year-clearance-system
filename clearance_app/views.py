from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db import transaction
from .models import *
from .forms import *
from .utils import *

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'clearance_app/home.html')

def register_student(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            create_audit_log(
                user=user,
                action='user_create',
                description=f'Student registered: {user.full_name}',
                ip_address=get_client_ip(request)
            )
            messages.success(request, 'Registration successful! Welcome to ACU Clearance System.')
            try:
                subject = "Welcome to Ajayi Crowther University Final Year Clearance Portal"
                message = (
                            f"Dear {request.user.full_name},\n\n"
                            "Welcome to the Ajayi Crowther University Final Year Clearance Portal. "
                            "This platform has been carefully designed to simplify and streamline "
                            "your clearance process.\n\n"
                            "You can now complete your departmental clearance, upload required documents, "
                            "and track your approval status in real time.\n\n"
                            "We wish you a smooth and successful clearance process.\n\n"
                            "Best regards,\n"
                            "Office of the Registrar,\n"
                            "Ajayi Crowther University "
                        )

                email= user.email
                send_email_notification(subject, message, email)
            except Exception as e:
                print (f"Error Occurred: {e}")
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentRegistrationForm()
    
    return render(request, 'clearance_app/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                login(request, user)
                create_audit_log(
                    user=user,
                    action='login',
                    description=f'User logged in: {user.full_name}',
                    ip_address=get_client_ip(request)
                )
                messages.success(request, f'Welcome back, {user.full_name}!')
                return redirect('dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
    else:
        form = UserLoginForm()
    
    return render(request, 'clearance_app/login.html', {'form': form})

@login_required
def logout_view(request):
    create_audit_log(
        user=request.user,
        action='logout',
        description=f'User logged out: {request.user.full_name}',
        ip_address=get_client_ip(request)
    )
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

@login_required
def dashboard(request):
    if request.user.is_student():
        return student_dashboard(request)
    elif request.user.is_officer():
        return officer_dashboard(request)
    elif request.user.is_admin():
        return admin_dashboard(request)
    else:
        messages.error(request, 'Invalid user role.')
        return redirect('login')

@login_required
def student_dashboard(request):
    if not request.user.is_student():
        messages.error(request, 'Access denied. Students only.')
        return redirect('dashboard')
    
    # Get or create clearance record
    clearance, created = Clearance.objects.get_or_create(
        student=request.user,
        defaults={'status': 'not_started'}
    )
    
    # Get all department approvals
    departments = Department.objects.filter(is_active=True).order_by('order')
    approvals = ClearanceApproval.objects.filter(clearance=clearance).select_related('department', 'officer')
    
    # Create approval status dictionary
    approval_status = {}
    for approval in approvals:
        approval_status[approval.department.id] = approval
    
    # Get uploaded documents
    documents = Document.objects.filter(clearance=clearance).order_by('-uploaded_at')
    
    context = {
        'clearance': clearance,
        'departments': departments,
        'approval_status': approval_status,
        'documents': documents,
        'progress_percentage': clearance.get_progress_percentage(),
    }
    
    return render(request, 'clearance_app/student_dashboard.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def start_clearance(request):
    if not request.user.is_student():
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    clearance = get_object_or_404(Clearance, student=request.user)
    
    if clearance.status not in ['not_started', 'rejected']:
        messages.warning(request, 'Clearance already in progress.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        # Check if this is a clearance submission (not document upload)
        if 'submit_clearance' in request.POST:
            # This is the final submission - no form validation needed
            if clearance.documents.count() > 0:
                
                active_departments = Department.objects.filter(is_active=True).order_by('order')
                first_department = active_departments.first()
                
                if first_department:
                    with transaction.atomic():
                        if clearance.status == 'rejected':
                            
                            # Find the department that rejected
                            rejected_approval = ClearanceApproval.objects.filter(
                                clearance=clearance,
                                status='rejected'
                            ).select_related('department').order_by('department__order').first()
                            
                            if rejected_approval:
                                rejecting_dept = rejected_approval.department

                                ClearanceApproval.objects.filter(
                                    id=rejected_approval.id
                                ).update(
                                    status='pending',
                                    officer=None,
                                    comment=''
                                )
                                

                                clearance.status = 'in_progress'
                                clearance.current_department = rejecting_dept
                                clearance.date_submitted = timezone.now()
                                clearance.save()
                                
                                create_audit_log(
                                    user=request.user,
                                    action='clearance_submit',
                                    description=f'Clearance resubmitted by {request.user.full_name}. Routed back to {rejecting_dept.name}.',
                                    ip_address=get_client_ip(request),
                                    clearance=clearance
                                )
                                
                                messages.success(
                                    request,
                                    f'Clearance resubmitted successfully! Your clearance has been sent back to '
                                    f'{rejecting_dept.name} for review.'
                                )
                                try:
                                    subject = "Resubmission Received – Clearance Under Review"
                                    message = (
                                        f"Dear {request.user.full_name},\n\n"
                                        "This is to confirm that your updated clearance documents have been successfully "
                                        "received on the Ajayi Crowther University Final Year Clearance Portal.\n\n"
                                        f"Your resubmission is currently under review by {rejecting_dept.name}. "
                                        "You will be notified once a decision has been made.\n\n"
                                        "Thank you for your prompt action and cooperation.\n\n"
                                        "Best regards,\n"
                                        "Office of the Registrar,\n"
                                        "Ajayi Crowther University"
                                    )

                                    email= request.user.email
                                    send_email_notification(subject, message, email)
                                except Exception as e:
                                    print (f"Error Occurred: {e}")
                                return redirect('dashboard')
                            
                            else:
                                ClearanceApproval.objects.filter(clearance=clearance).delete()
                                
                                clearance.status = 'in_progress'
                                clearance.current_department = first_department
                                clearance.date_submitted = timezone.now()
                                clearance.save()
                                
                                for dept in active_departments:
                                    ClearanceApproval.objects.create(
                                        clearance=clearance,
                                        department=dept,
                                        status='pending'
                                    )
                                
                                create_audit_log(
                                    user=request.user,
                                    action='clearance_submit',
                                    description=f'Clearance resubmitted by {request.user.full_name} (restarted from beginning).',
                                    ip_address=get_client_ip(request),
                                    clearance=clearance
                                )
                                try:
                                    subject = "Clearance Submission Received – Under Review"

                                    message = (
                                        f"Dear {request.user.full_name},\n\n"
                                        "This is to confirm that your final year clearance submission has been "
                                        "successfully received on the Ajayi Crowther University Clearance Portal.\n\n"
                                        "Your application is currently under review by the respective departments. "
                                        "You will receive a notification once the review process has been completed "
                                        "or if any further action is required from you.\n\n"
                                        "Kindly ensure you monitor your email and dashboard regularly for updates.\n\n"
                                        "Best regards,\n"
                                        "Office of the Registrar,\n"
                                        "Ajayi Crowther University"
                                    )
                                    email= request.user.email
                                    send_email_notification(subject, message, email)
                                except Exception as e:
                                    print (f"Error Occurred: {e}")
                                
                                messages.success(request, 'Clearance resubmitted successfully!')
                                return redirect('dashboard')
                        else:
                            clearance.status = 'pending'
                            clearance.current_department = first_department
                            clearance.date_submitted = timezone.now()
                            clearance.save()
                            
                            # Create approval records for all departments
                            for dept in active_departments:
                                ClearanceApproval.objects.get_or_create(
                                    clearance=clearance,
                                    department=dept,
                                    defaults={'status': 'pending'}
                                )
                            
                            create_audit_log(
                                user=request.user,
                                action='clearance_submit',
                                description=f'Clearance submitted by {request.user.full_name}',
                                ip_address=get_client_ip(request),
                                clearance=clearance
                            )
                            
                            messages.success(request, 'Clearance request submitted successfully!')
                            return redirect('dashboard')
                
                else:
                    messages.error(request, 'No active departments found. Contact administrator.')
            else:
                messages.error(request, 'Please upload at least one document before submitting.')
            
            return redirect('start_clearance')
        
        # This is a document upload (not final submission)
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Save document
            document_type = form.cleaned_data['document_type']
            file = form.cleaned_data['file']
            
            Document.objects.create(
                clearance=clearance,
                document_type=document_type,
                file=file,
                file_name=file.name,
                file_size=file.size
            )
            
            messages.success(request, 'Document uploaded successfully.')
            return redirect('start_clearance')
    else:
        form = DocumentUploadForm()
    
    documents = Document.objects.filter(clearance=clearance).order_by('-uploaded_at')
    
    context = {
        'form': form,
        'clearance': clearance,
        'documents': documents,
    }
    
    return render(request, 'clearance_app/start_clearance.html', context)

@login_required
def delete_document(request, document_id):
    if not request.user.is_student():
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    document = get_object_or_404(Document, id=document_id, clearance__student=request.user)
    
    # Only allow deletion if clearance not yet submitted
    if document.clearance.status in ['not_started', 'rejected']:
        document.file.delete()  # Delete physical file
        document.delete()
        messages.success(request, 'Document deleted successfully.')
    else:
        messages.error(request, 'Cannot delete documents after clearance submission.')
    
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def download_clearance_certificate(request):
    if not request.user.is_student():
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    clearance = get_object_or_404(Clearance, student=request.user)
    
    if clearance.status != 'approved':
        messages.error(request, 'Clearance certificate only available after full approval.')
        return redirect('dashboard')
    
    # Generate certificate (simplified HTML version)
    context = {
        'clearance': clearance,
        'student': request.user,
        'generated_date': timezone.now(),
    }
    
    return render(request, 'clearance_app/clearance_certificate.html', context)

@login_required
def officer_dashboard(request):
    if not request.user.is_officer():
        messages.error(request, 'Access denied. Officers only.')
        return redirect('dashboard')
    
    if not request.user.department:
        messages.error(request, 'You are not assigned to any department. Contact administrator.')
        return redirect('login')
    
    department = request.user.department
    pending_approvals = ClearanceApproval.objects.filter(
        department=department,
        status='pending',
        clearance__status__in=['pending', 'in_progress']
    ).select_related('clearance__student', 'clearance__student__faculty')
    
    # If officer is in Faculty department and has faculty assignment, filter by faculty
    if department.name == 'Faculty' and request.user.faculty_assignment:
        pending_approvals = pending_approvals.filter(
            clearance__student__faculty=request.user.faculty_assignment
        )
    
    pending_approvals = pending_approvals.order_by('-clearance__date_submitted')
    
    # Get statistics
    total_pending = pending_approvals.count()
    
    # Base query for stats
    stats_query = ClearanceApproval.objects.filter(department=department)
    if department.name == 'Faculty' and request.user.faculty_assignment:
        stats_query = stats_query.filter(clearance__student__faculty=request.user.faculty_assignment)
    
    total_approved = stats_query.filter(status='approved').count()
    total_rejected = stats_query.filter(status='rejected').count()
    
    # Recent actions by this officer
    recent_actions = ClearanceApproval.objects.filter(
        officer=request.user
    ).select_related('clearance__student', 'clearance__student__faculty', 'department').order_by('-updated_at')[:10]
    
    context = {
        'department': department,
        'pending_approvals': pending_approvals,
        'total_pending': total_pending,
        'total_approved': total_approved,
        'total_rejected': total_rejected,
        'recent_actions': recent_actions,
        'faculty_assignment': request.user.faculty_assignment,  # Show which faculty officer handles
    }
    
    return render(request, 'clearance_app/officer_dashboard.html', context)

@login_required
def review_clearance(request, clearance_id):
    if not request.user.is_officer():
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    clearance = get_object_or_404(Clearance, id=clearance_id)
    department = request.user.department
    
    # Check if officer can review this clearance
    if not request.user.can_review_clearance(clearance):
        messages.error(request, f'You can only review clearances for {request.user.faculty_assignment.name} faculty.')
        return redirect('officer_dashboard')
    
    # Check if this clearance is currently at this officer's department
    if clearance.current_department != department:
        messages.warning(request, 'This clearance is not at your department yet.')
        return redirect('officer_dashboard')

    # Check clearance is in a reviewable state
    if clearance.status not in ['pending', 'in_progress']:
        messages.info(request, 'This clearance is not currently active.')
        return redirect('dashboard')

    # Get or create approval record for this department
    approval, created = ClearanceApproval.objects.get_or_create(
        clearance=clearance,
        department=department,
        defaults={'status': 'pending'}
    )

    if approval.status != 'pending':
        messages.info(request, 'This clearance has already been processed by your department.')
        return redirect('officer_dashboard')
    
    if request.method == 'POST':
        form = ClearanceApprovalForm(request.POST, instance=approval)
        if form.is_valid():
            approval = form.save(commit=False)
            approval.officer = request.user
            approval.save()
            
            # Update clearance status
            if approval.status == 'approved':
                # Move to next department
                clearance.move_to_next_department()
                
                create_audit_log(
                    user=request.user,
                    action='approval_approve',
                    description=f'{department.name} approved clearance for {clearance.student.full_name}',
                    ip_address=get_client_ip(request),
                    clearance=clearance
                )
                try:
                    subject = "Department Clearance Approved – Proceeding to Next Stage"
                    message = (
                        f"Dear {clearance.student.full_name},\n\n"
                        "We are pleased to inform you that your clearance has been successfully "
                        f"approved by {approval.officer} .\n\n"
                        f"Your application has now been forwarded to the {clearance.current_department} for review "
                        "as part of the final year clearance process.\n\n"
                        "Kindly continue to monitor your clearance portal for further updates "
                        "regarding your progress.\n\n"
                        "Best regards,\n"
                        "Office of the Registrar,\n"
                        "Ajayi Crowther University"
                    )

                    email= clearance.student.email
                    send_email_notification(subject, message, email)
                except Exception as e:
                    print (f"Error Occurred: {e}")
                                
                
                messages.success(request, f'Clearance approved for {clearance.student.full_name}.')
                
            elif approval.status == 'rejected':
                clearance.status = 'rejected'
                clearance.save()
                
                create_audit_log(
                    user=request.user,
                    action='approval_reject',
                    description=f'{department.name} rejected clearance for {clearance.student.full_name}',
                    ip_address=get_client_ip(request),
                    clearance=clearance
                )
                try:
                    subject = "Clearance Update: Submission Not Approved"
                    message = (
                        f"Dear {clearance.student.full_name},\n\n"
                        "We regret to inform you that your recent clearance submission has not been "
                        f"approved by the {clearance.current_department}.\n\n"
                        "Kindly log in to the Final Year Clearance Portal to review the feedback "
                        "provided and take the necessary corrective action.\n\n"
                        "You may update and resubmit your documents once the required adjustments "
                        "have been made.\n\n"
                        "We encourage you to address the feedback promptly to avoid delays in your "
                        "clearance process.\n\n"
                        "Best regards,\n"
                        "Office of the Registrar,\n"
                        "Ajayi Crowther University"
                    )
                    email= clearance.student.email
                    send_email_notification(subject, message, email)
                except Exception as e:
                    print (f"Error Occurred: {e}")
                                
                messages.warning(request, f'Clearance rejected for {clearance.student.full_name}.')
            
            return redirect('dashboard')
    else:
        form = ClearanceApprovalForm(instance=approval)
    
    # Get student documents
    documents = Document.objects.filter(clearance=clearance).order_by('-uploaded_at')
    
    # Get all approvals for this clearance
    all_approvals = ClearanceApproval.objects.filter(
        clearance=clearance
    ).select_related('department', 'officer').order_by('department__order')
    
    context = {
        'form': form,
        'clearance': clearance,
        'approval': approval,
        'documents': documents,
        'all_approvals': all_approvals,
        'student_faculty': clearance.student.faculty,  
    }
    
    return render(request, 'clearance_app/review_clearance.html', context)

@login_required
def officer_history(request):
    if not request.user.is_officer():
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    approvals = ClearanceApproval.objects.filter(
        officer=request.user
    ).select_related('clearance__student', 'department').order_by('-updated_at')
    
    context = {
        'approvals': approvals,
    }
    
    return render(request, 'clearance_app/officer_history.html', context)

@login_required
def admin_dashboard(request):

    if not request.user.is_admin():
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('dashboard')
    
    # Overall statistics
    total_students = User.objects.filter(role='student').count()
    total_clearances = Clearance.objects.count()
    total_approved = Clearance.objects.filter(status='approved').count()
    total_pending = Clearance.objects.filter(status__in=['pending', 'in_progress']).count()
    total_rejected = Clearance.objects.filter(status='rejected').count()
    
    # Department statistics
    departments = Department.objects.filter(is_active=True).annotate(
        pending_count=Count('approvals', filter=Q(approvals__status='pending')),
        approved_count=Count('approvals', filter=Q(approvals__status='approved')),
        rejected_count=Count('approvals', filter=Q(approvals__status='rejected'))
    ).order_by('order')
    
    # Recent clearances
    recent_clearances = Clearance.objects.select_related('student', 'current_department').order_by('-date_created')[:10]
    
    # Recent audit logs
    recent_logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:15]
    
    context = {
        'total_students': total_students,
        'total_clearances': total_clearances,
        'total_approved': total_approved,
        'total_pending': total_pending,
        'total_rejected': total_rejected,
        'departments': departments,
        'recent_clearances': recent_clearances,
        'recent_logs': recent_logs,
    }
    
    return render(request, 'clearance_app/admin_dashboard.html', context)

@login_required
def manage_departments(request):
    if not request.user.is_admin():
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            department = form.save()
            create_audit_log(
                user=request.user,
                action='department_create',
                description=f'Department created: {department.name}',
                ip_address=get_client_ip(request)
            )
            messages.success(request, f'Department "{department.name}" created successfully.')
            return redirect('manage_departments')
    else:
        form = DepartmentForm()
    
    departments = Department.objects.all().order_by('order')
    
    context = {
        'form': form,
        'departments': departments,
    }
    
    return render(request, 'clearance_app/manage_departments.html', context)

@login_required
def edit_department(request, department_id):
    if not request.user.is_admin():
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    department = get_object_or_404(Department, id=department_id)
    
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, f'Department "{department.name}" updated successfully.')
            return redirect('manage_departments')
    else:
        form = DepartmentForm(instance=department)
    
    context = {
        'form': form,
        'department': department,
        'editing': True,
    }
    
    return render(request, 'clearance_app/edit_department.html', context)

@login_required
def manage_officers(request):
    if not request.user.is_admin():
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = OfficerCreationForm(request.POST)
        if form.is_valid():
            officer = form.save()
            create_audit_log(
                user=request.user,
                action='user_create',
                description=f'Officer created: {officer.full_name} for {officer.department.name}',
                ip_address=get_client_ip(request)
            )
            messages.success(request, f'Officer "{officer.full_name}" created successfully.')
            return redirect('manage_officers')
    else:
        form = OfficerCreationForm()
    
    officers = User.objects.filter(role='officer').select_related('department').order_by('full_name')
    
    context = {
        'form': form,
        'officers': officers,
    }
    
    return render(request, 'clearance_app/manage_officers.html', context)

@login_required
def view_all_clearances(request):
    if not request.user.is_admin():
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    clearances = Clearance.objects.select_related('student', 'current_department').order_by('-date_created')
    
    # Search and filter
    form = ClearanceSearchForm(request.GET)
    if form.is_valid():
        search_query = form.cleaned_data.get('search_query')
        status = form.cleaned_data.get('status')
        department = form.cleaned_data.get('department')
        
        if search_query:
            clearances = clearances.filter(
                Q(student__full_name__icontains=search_query) |
                Q(student__matric_number__icontains=search_query)
            )
        
        if status:
            clearances = clearances.filter(status=status)
        
        if department:
            clearances = clearances.filter(current_department=department)
    
    context = {
        'form': form,
        'clearances': clearances,
    }
    
    return render(request, 'clearance_app/view_all_clearances.html', context)

@login_required
def view_clearance_detail(request, clearance_id):
    if not request.user.is_admin():
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    clearance = get_object_or_404(Clearance, id=clearance_id)
    approvals = ClearanceApproval.objects.filter(clearance=clearance).select_related('department', 'officer').order_by('department__order')
    documents = Document.objects.filter(clearance=clearance).order_by('-uploaded_at')
    
    context = {
        'clearance': clearance,
        'approvals': approvals,
        'documents': documents,
    }
    
    return render(request, 'clearance_app/clearance_detail.html', context)


@login_required
def audit_logs(request):

    if not request.user.is_admin():
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    logs = AuditLog.objects.select_related('user', 'clearance').order_by('-timestamp')
    
    context = {
        'logs': logs,
    }
    
    return render(request, 'clearance_app/audit_logs.html', context)