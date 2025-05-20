from django.core.management.base import BaseCommand
from schemes.models import Plan, Scheme

class Command(BaseCommand):
    help = 'Assigns the Cherry Blossom scheme and age ranges to all plans'

    def handle(self, *args, **options):
        scheme = Scheme.objects.filter(name__icontains="cherry blossom").first()

        if not scheme:
            self.stdout.write(self.style.ERROR("❌ Cherry Blossom scheme not found."))
            return

        plans = Plan.objects.all()
        for plan in plans:
            plan.scheme = scheme
            name = plan.name.lower()

            if "18-64" in name:
                plan.min_age, plan.max_age = 18, 64
            elif "65-74" in name:
                plan.min_age, plan.max_age = 65, 74
            elif "75-84" in name:
                plan.min_age, plan.max_age = 75, 84
            else:
                plan.min_age, plan.max_age = 0, 100

            plan.save()

        self.stdout.write(self.style.SUCCESS("✅ Plans updated with Cherry Blossom scheme and age ranges."))
