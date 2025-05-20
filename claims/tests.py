from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from members.models import Member
from claims.models import Claim

class ClaimTestCase(TestCase):

    def setUp(self):
        self.member = Member.objects.create(first_name='John', last_name='Doe', id_number='1234567890123')

    def test_claim_submission(self):
        response = self.client.post('/claims/submit/', {
            'member': self.member.id,
            'claim_type': 'medical',
            'amount': '1000.00',
            'description': 'Medical expenses',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/claims/status/')

    def test_claim_status_search(self):
        claim = Claim.objects.create(member=self.member, claim_type='medical', amount='1000.00', description='Medical expenses')
        response = self.client.get('/claims/status/', {'search': 'John'})
        self.assertContains(response, claim.id)
        self.assertEqual(response.status_code, 200)
