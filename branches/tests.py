from django.test import TestCase
from .models import Branch, Bank

class BranchSetupTestCase(TestCase):

    def setUp(self):
        bank = Bank.objects.create(name="Test Bank", branch_code="12345")
        Branch.objects.create(
            name="Test Branch",
            bank=bank,
            location="Test Location",
            code="BR001",
            phone="1234567890",
            cell="0987654321"
        )

    def test_branch_creation(self):
        branch = Branch.objects.get(name="Test Branch")
        self.assertEqual(branch.location, "Test Location")
        self.assertEqual(branch.phone, "1234567890")
        self.assertEqual(branch.cell, "0987654321")
