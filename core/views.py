# core/views.py

from decimal import Decimal
from datetime import date
import calendar
import logging
import os

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import models
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.conf import settings

from .models import Employee, Attendance, LeaveRequest, Payroll, Notification, Department
from .forms import LeaveRequestForm, AttendanceForm
from .utils import calc_nssf, calc_sha, calc_paye
from django.views.decorators.http import require_POST
# ================================================================
# Logger
# ================================================================
logger = logging.getLogger(__name__)

# ================================================================
# PDF Helper
# ================================================================
def link_callback(uri, rel):
    """Convert HTML URIs to absolute system paths for xhtml2pdf."""
    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    elif uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
    else:
        return uri
    if not os.path.exists(path):
        raise Exception(f"Media URI not found: {path}")
    return path

# ================================================================
# Role & Group Helpers
# ================================================================
def group_required(group_name):
    """Decorator to require user to belong to a specific group."""
    def check(user):
        return user.is_superuser or user.groups.filter(name=group_name).exists()
    return user_passes_test(check)

def is_hr(user):
    """Check if user is HR or superuser."""
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name="HR").exists())

# ================================================================
# Login / Logout
# ================================================================
def hr_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user and is_hr(user):
            login(request, user)
            return redirect("hr_dashboard")
        messages.error(request, "Invalid HR credentials or not authorized.")
    return render(request, "registration/hr_login.html")

def employee_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            Employee.objects.get_or_create(user=user)  # Ensure Employee profile exists
            return redirect('hr_dashboard') if is_hr(user) else redirect('employee_dashboard')
        messages.error(request, "Invalid username or password")
    return render(request, 'registration/login.html')

@login_required
@require_POST
def employee_logout(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect("login")
# ================================================================
# Employee Dashboard
# ================================================================
@login_required
def employee_dashboard(request):
    try:
        employee = get_object_or_404(Employee, user=request.user)
        payrolls = Payroll.objects.filter(employee=employee).order_by('-period_start')[:5]
        attendance_records = employee.attendance.order_by('-date')[:5] if hasattr(employee, 'attendance') else []
        leaves = employee.leaves.order_by('-start_date')[:5] if hasattr(employee, 'leaves') else []
        notifications = employee.user.notifications.order_by('-created_at')[:5] if hasattr(employee.user, 'notifications') else []
        total_present = employee.attendance.filter(status='Present').count() if hasattr(employee, 'attendance') else 0

        context = {
            "employee": employee,
            "payrolls": payrolls,
            "attendance_records": attendance_records,
            "leaves": leaves,
            "notifications": notifications,
            "total_present": total_present,
        }
        return render(request, "core/employee_dashboard.html", context)
    except Employee.DoesNotExist:
        logger.error(f"No Employee profile found for user {request.user.username}")
        messages.error(request, "Employee profile not found. Contact admin.")
        return redirect('login')
    except Exception as e:
        logger.exception(f"Error in employee_dashboard for user {request.user.username}: {e}")
        messages.error(request, "An unexpected error occurred. Try again later.")
        return redirect('login')

# ================================================================
# Profile
# ================================================================
@login_required
def my_profile(request):
    emp = get_object_or_404(Employee, user=request.user)
    return render(request, 'core/my_profile.html', {'employee': emp})

# ================================================================
# HR Management: Employees, Departments, Leaves
# ================================================================
@login_required
@group_required('HR')
def hr_employee_list(request):
    employees = Employee.objects.select_related('user', 'department').all()
    return render(request, 'core/hr_employee_list.html', {'employees': employees})

@login_required
@group_required('HR')
def hr_department_list(request):
    departments = Department.objects.all()
    return render(request, 'core/hr_department_list.html', {'departments': departments})

@login_required
@group_required('HR')
def hr_leave_list(request):
    leaves = LeaveRequest.objects.select_related("employee").all().order_by("-requested_at")
    return render(request, 'core/hr_leave_list.html', {"leaves": leaves})

@login_required
@group_required('HR')
def approve_leave(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    leave.status = "A"
    leave.save()
    return redirect("hr_leave_list")

@login_required
@group_required('HR')
def reject_leave(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    leave.status = "R"
    leave.save()
    return redirect("hr_leave_list")

# ================================================================
# Attendance
# ================================================================
@login_required
def mark_attendance(request):
    emp = get_object_or_404(Employee, user=request.user)
    today = timezone.localdate()
    att, _ = Attendance.objects.get_or_create(employee=emp, date=today)

    if request.method == 'POST':
        action = request.POST.get('action')
        now = timezone.localtime()
        if action == 'checkin':
            att.check_in = now.time()
        elif action == 'checkout':
            att.check_out = now.time()
        att.save()
        return redirect('attendance_view')
    return render(request, 'core/attendance_mark.html', {'attendance': att})

@login_required
def add_attendance(request):
    employee = get_object_or_404(Employee, user=request.user)
    if request.method == "POST":
        form = AttendanceForm(request.POST)
        if form.is_valid():
            attendance = form.save(commit=False)
            attendance.employee = employee
            attendance.save()
            return redirect("employee_dashboard")
    else:
        form = AttendanceForm()
    return render(request, "core/add_attendance.html", {"form": form})

@login_required
def attendance_view(request):
    emp = get_object_or_404(Employee, user=request.user)
    records = Attendance.objects.filter(employee=emp).order_by('-date')[:50]
    return render(request, 'core/attendance_view.html', {'records': records})

# ================================================================
# Leave Requests
# ================================================================
@login_required
def leave_request_create(request):
    emp = get_object_or_404(Employee, user=request.user)
    if request.method == "POST":
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = emp
            leave.status = 'P'
            leave.save()
            # Notify HR/Admin
            admins = User.objects.filter(groups__name__in=["HR", "Admin"])
            for a in admins:
                Notification.objects.create(
                    user=a,
                    title="New leave request",
                    message=f"{emp.user.username} requested leave {leave.start_date} → {leave.end_date}",
                )
            return redirect("leave_list")
    else:
        form = LeaveRequestForm()
    return render(request, "core/leave_request_form.html", {"form": form})

@login_required
def leave_list(request):
    if is_hr(request.user):
        leaves = LeaveRequest.objects.select_related("employee").all().order_by("-requested_at")
    else:
        emp = get_object_or_404(Employee, user=request.user)
        leaves = LeaveRequest.objects.filter(employee=emp).order_by("-requested_at")
    return render(request, "core/leave_list.html", {"leaves": leaves})

@login_required
@group_required('HR')
def leave_process(request, pk, action):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    leave.status = 'A' if action == 'approve' else 'R'
    leave.processed_by = request.user
    leave.processed_at = timezone.now()
    leave.save()
    Notification.objects.create(
        user=leave.employee.user,
        title='Leave update',
        message=f'Your leave request from {leave.start_date} to {leave.end_date} was {leave.get_status_display()}'
    )
    return redirect('leave_list')

# ================================================================
# Payroll
# ================================================================
@login_required
@group_required('HR')
def generate_payroll_for_employee(request, emp_id):
    employee = get_object_or_404(Employee, pk=emp_id)
    today = date.today()
    start = date(today.year, today.month, 1)
    end = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])

    gross = employee.salary
    nssf = calc_nssf(gross)
    sha = calc_sha(gross)
    paye = calc_paye(gross)
    other = Decimal('0.00')
    net = gross - nssf - sha - paye - other

    payroll = Payroll.objects.create(
        employee=employee,
        period_start=start,
        period_end=end,
        gross_salary=gross,
        nssf=nssf,
        sha=sha,
        paye=paye,
        net_pay=net,
        status=request.POST.get("status", "Pending")
    )

    Notification.objects.create(
        user=employee.user,
        title='Payslip generated',
        message=f'Payslip for {start} to {end} generated.'
    )
    return redirect('payroll_detail', pk=payroll.pk)

@login_required
def payroll_detail(request, pk):
    payroll = get_object_or_404(Payroll, pk=pk)
    if request.user != payroll.employee.user and not is_hr(request.user):
        return redirect('employee_dashboard')
    return render(request, 'core/payroll_detail.html', {'payroll': payroll})

@login_required
@group_required('HR')
def payroll_mark_paid(request, pk):
    payroll = get_object_or_404(Payroll, pk=pk)
    payroll.status = "Paid"
    payroll.save()
    Notification.objects.create(
        user=payroll.employee.user,
        title="Salary Payment",
        message=f"Your salary for {payroll.period_start} → {payroll.period_end} has been marked as PAID."
    )
    return redirect("payroll_detail", pk=pk)

# ================================================================
# Employee Payroll Views
# ================================================================
@login_required
def employee_payroll(request):
    """View payroll history in browser."""
    employee = get_object_or_404(Employee, user=request.user)
    payrolls = Payroll.objects.filter(employee=employee).order_by('-period_end')
    return render(request, "employee/employee_payroll.html", {"payrolls": payrolls})

@login_required
def payroll_pdf(request, payroll_id):
    """Download payroll as PDF."""
    payroll = get_object_or_404(Payroll, id=payroll_id)
    employee = payroll.employee

    if request.user != employee.user and not is_hr(request.user):
        return HttpResponse("Unauthorized access", status=403)

    html = render_to_string("employee/payroll_pdf.html", {
        "payroll": payroll,
        "employee": employee,
        "generated_at": timezone.now(),
    })

    filename = f"payslip_{employee.user.username}_{payroll.period_start}_{payroll.period_end}.pdf"
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    try:
        pisa_status = pisa.CreatePDF(html, dest=response, link_callback=link_callback)
        if pisa_status.err:
            logger.error(f"PDF generation failed for payroll {payroll.id}: {pisa_status.err}")
            return HttpResponse("Error generating PDF.", status=500)
    except Exception as e:
        logger.exception(f"Exception during PDF generation: {e}")
        return HttpResponse("Error generating PDF.", status=500)

    return response

# ================================================================
# HR Dashboard
# ================================================================
@login_required
@group_required('HR')
def hr_dashboard(request):
    employees = Employee.objects.all()
    departments = Department.objects.all()
    pending_leaves = LeaveRequest.objects.filter(status='P')
    payrolls = Payroll.objects.all().order_by("-period_end")[:5]

    context = {
        "employees_count": employees.count(),
        "departments_count": departments.count(),
        "pending_leaves": pending_leaves,
        "recent_payrolls": payrolls,
    }
    return render(request, 'core/hr_dashboard.html', context)

# ================================================================
# Reports
# ================================================================
@login_required
@group_required('HR')
def employee_report(request):
    """Report: Count of employees per department"""
    data = Employee.objects.values('department__name').annotate(total=models.Count('id')).order_by('department__name')
    return render(request, "reports/employee_report.html", {"data": data})

@login_required
@group_required('HR')
def attendance_report(request):
    """Report: Count of attendance status per date"""
    data = Attendance.objects.values('date', 'status').annotate(total=models.Count('id')).order_by('date')
    return render(request, "reports/attendance_report.html", {"data": data})

@login_required
@group_required('HR')
def salary_report(request):
    """Report: Total salary expense of all employees"""
    total_salary = Employee.objects.aggregate(total_salary=models.Sum('salary'))
    return render(request, "reports/salary_report.html", {"total_salary": total_salary})
