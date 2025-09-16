# Register your models here.
from django.contrib import admin
from .models import (
    Department,
    Employee,
    EmployeeDocument,
    Attendance,
    LeaveRequest,
    Payroll,
    KPI,
    Notification,
)

# Simple registrations
admin.site.register(Department)
admin.site.register(EmployeeDocument)
admin.site.register(KPI)
admin.site.register(Notification)

# Employee admin
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("user", "job_title", "department", "salary", "is_active_employee")
    list_filter = ("department", "is_active_employee")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "job_title",
        "department__name",
    )

# Attendance admin
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'check_in', 'check_out', 'status')
    list_filter = ('date', 'status', 'employee')

# LeaveRequest admin
@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "start_date", "end_date", "status")
    list_filter = ("status", "leave_type")
    search_fields = (
        "employee__user__username",
        "employee__user__first_name",
        "employee__user__last_name",
    )

# Payroll admin
@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "period_start",
        "period_end",
        "gross_salary",
        "net_pay",
        "status",
    )
    list_filter = ("status", "period_start", "period_end")
    search_fields = (
        "employee__user__username",
        "employee__user__first_name",
        "employee__user__last_name",
    )
    list_editable = ("status",)
    actions = ["mark_selected_as_paid", "mark_selected_as_pending"]

    def mark_selected_as_paid(self, request, queryset):
        updated = queryset.update(status="Paid")
        self.message_user(request, f"{updated} payroll(s) marked as Paid.")
    mark_selected_as_paid.short_description = "Mark selected payrolls as Paid"

    def mark_selected_as_pending(self, request, queryset):
        updated = queryset.update(status="Pending")
        self.message_user(request, f"{updated} payroll(s) marked as Pending.")
    mark_selected_as_pending.short_description = "Mark selected payrolls as Pending"
