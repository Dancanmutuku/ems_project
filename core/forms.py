# core/forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Employee, LeaveRequest, Attendance, Department, Payroll, KPI

# --------------------------
# Payroll Form
# --------------------------
class PayrollForm(forms.ModelForm):
    class Meta:
        model = Payroll
        fields = ['employee', 'period_start', 'period_end', 'basic_salary', 'allowances', 'status']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'period_start': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'period_end': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'allowances': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

# --------------------------
# Leave Request Form
# --------------------------
class LeaveRequestForm(forms.ModelForm):
    # Employee selection only visible for HR
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = LeaveRequest
        fields = ['employee', 'leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.groups.filter(name="HR").exists():
            # Non-HR users cannot select employee
            self.fields['employee'].widget = forms.HiddenInput()
            if hasattr(user, 'employee_profile'):
                self.instance.employee = user.employee_profile

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        employee = cleaned_data.get('employee') or getattr(self.instance, 'employee', None)

        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'End date must be on or after the start date.')

        if employee and start_date and end_date and end_date >= start_date:
            overlapping = LeaveRequest.objects.filter(
                employee=employee,
                status__in=['P', 'A'],
                start_date__lte=end_date,
                end_date__gte=start_date,
            )
            if self.instance.pk:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            if overlapping.exists():
                raise forms.ValidationError(
                    'This employee already has a pending or approved leave request for part of these dates.'
                )

        return cleaned_data

# --------------------------
# Employee Form
# --------------------------
class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'employee_id', 'contact', 'dob', 'gender', 'address',
            'job_title', 'department', 'salary', 'hire_date',
            'is_active_employee', 'profile_picture',
            'emergency_contact_name', 'emergency_contact_phone',
            'annual_leave_balance', 'sick_leave_balance',
        ]
        widgets = {
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'contact': forms.TextInput(attrs={'class': 'form-control'}),
            'dob': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'hire_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active_employee': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'annual_leave_balance': forms.NumberInput(attrs={'class': 'form-control'}),
            'sick_leave_balance': forms.NumberInput(attrs={'class': 'form-control'}),
        }

# --------------------------
# User Registration Form
# --------------------------
class UserForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

# --------------------------
# Attendance Form
# --------------------------
class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['check_in', 'check_out', 'status']
        widgets = {
            'check_in': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'check_out': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

# --------------------------
# Department Form
# --------------------------
class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

# --------------------------
# Performance Review Form
# --------------------------
class KPIForm(forms.ModelForm):
    class Meta:
        model = KPI
        fields = ['employee', 'name', 'target', 'actual', 'review_date', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'target': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'actual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'review_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def clean_target(self):
        target = self.cleaned_data['target']
        if target <= 0:
            raise forms.ValidationError('Target must be greater than zero.')
        return target

    def clean_actual(self):
        actual = self.cleaned_data.get('actual')
        if actual is not None and actual < 0:
            raise forms.ValidationError('Actual performance cannot be negative.')
        return actual
