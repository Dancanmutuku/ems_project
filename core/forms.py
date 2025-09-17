
# core/forms.py
from django import forms
from .models import LeaveRequest
from .models import Attendance
class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ["check_in", "check_out", "status"]
        widgets = {
            "check_in": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "check_out": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }
