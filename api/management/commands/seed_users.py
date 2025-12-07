from django.core.management.base import BaseCommand
from faker import Faker
from api.models import User  # sesuaikan dengan app kamu
from django.contrib.auth.hashers import make_password

fake = Faker()

class Command(BaseCommand):
    help = "Seeding fake users"

    def handle(self, *args, **kwargs):
        for _ in range(5):
            User.objects.create(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                username=fake.user_name(),
                email=fake.email(),
                phone=fake.phone_number(),
                password=make_password("password123"),
            )

        self.stdout.write(self.style.SUCCESS("Successfully seeded users"))
