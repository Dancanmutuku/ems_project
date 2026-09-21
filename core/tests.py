from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .forms import LeaveRequestForm
from .models import Employee, KPI, LeaveRequest


class LeaveWorkflowTests(TestCase):
	def setUp(self):
		self.hr_user = User.objects.create_user(username='hr', password='test-password')
		hr_group, _ = Group.objects.get_or_create(name='HR')
		self.hr_user.groups.add(hr_group)
		employee_user = User.objects.create_user(username='employee', password='test-password')
		self.employee = Employee.objects.create(
			user=employee_user,
			annual_leave_balance=20,
			sick_leave_balance=10,
		)
		self.leave = LeaveRequest.objects.create(
			employee=self.employee,
			leave_type='Annual',
			start_date=date(2026, 10, 5),
			end_date=date(2026, 10, 7),
		)

	def test_form_rejects_reversed_dates(self):
		form = LeaveRequestForm(data={
			'leave_type': 'Annual',
			'start_date': '2026-10-10',
			'end_date': '2026-10-05',
			'reason': 'Annual leave',
		}, user=self.employee.user)

		self.assertFalse(form.is_valid())
		self.assertIn('End date must be on or after the start date.', form.errors['end_date'])

	def test_form_rejects_overlapping_pending_leave(self):
		form = LeaveRequestForm(data={
			'leave_type': 'Annual',
			'start_date': '2026-10-06',
			'end_date': '2026-10-08',
			'reason': 'Annual leave',
		}, user=self.employee.user)

		self.assertFalse(form.is_valid())
		self.assertIn('already has a pending or approved leave request', str(form.errors))

	def test_approval_deducts_once_and_rejection_restores_balance(self):
		self.client.login(username='hr', password='test-password')
		process_url = reverse('leave_process', args=[self.leave.pk, 'approve'])

		response = self.client.post(process_url)
		self.assertEqual(response.status_code, 302)
		self.employee.refresh_from_db()
		self.leave.refresh_from_db()
		self.assertEqual(self.leave.status, 'A')
		self.assertEqual(self.employee.annual_leave_balance, 17)

		self.client.post(process_url)
		self.employee.refresh_from_db()
		self.assertEqual(self.employee.annual_leave_balance, 17)

		self.client.post(reverse('leave_process', args=[self.leave.pk, 'reject']))
		self.employee.refresh_from_db()
		self.leave.refresh_from_db()
		self.assertEqual(self.leave.status, 'R')
		self.assertEqual(self.employee.annual_leave_balance, 20)

	def test_hr_employee_directory_can_search_by_username(self):
		self.client.login(username='hr', password='test-password')

		response = self.client.get(reverse('hr_employee_list'), {'q': 'employee'})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'employee')

	def test_hr_can_create_kpi_and_employee_can_view_only_their_kpis(self):
		self.client.login(username='hr', password='test-password')
		response = self.client.post(reverse('hr_kpi_create'), {
			'employee': self.employee.pk,
			'name': 'Monthly delivery target',
			'target': '10',
			'actual': '8',
			'review_date': '2026-10-31',
			'notes': 'Good progress.',
		})
		self.assertEqual(response.status_code, 302)
		self.assertEqual(KPI.objects.count(), 1)
		self.assertEqual(KPI.objects.get().rating(), 4.0)

		self.client.logout()
		self.client.login(username='employee', password='test-password')
		response = self.client.get(reverse('employee_kpi_list'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Monthly delivery target')
