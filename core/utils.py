from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from decimal import Decimal
def group_required(group_name):
    def in_group(u):
        return u.is_authenticated and u.groups.filter(name=group_name).exists()
    return user_passes_test(in_group)


class HRRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.groups.filter(name='HR').exists()
from decimal import Decimal

def calc_nssf(gross: Decimal) -> Decimal:
    # Placeholder: simple fixed percentage or bracket
    return (gross * Decimal('0.06')).quantize(Decimal('0.01'))

def calc_sha(gross: Decimal) -> Decimal:
    # Placeholder flat logic
    return (gross * Decimal('0.02')).quantize(Decimal('0.01'))

def calc_paye(gross: Decimal) -> Decimal:
    # Placeholder progressive sample — replace with real logic
    if gross <= 24000:
        rate = Decimal('0.10')
    elif gross <= 32333:
        rate = Decimal('0.25')
    else:
        rate = Decimal('0.30')
    return (gross * rate).quantize(Decimal('0.01'))
