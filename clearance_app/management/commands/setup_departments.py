"""
Management command to create default departments for ACU Clearance System
Usage: python manage.py setup_departments
"""
from django.core.management.base import BaseCommand
from clearance_app.models import Department


class Command(BaseCommand):
    help = 'Creates default clearance departments for ACU'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Setting up departments...'))
        
        # Define the 6 standard clearance departments
        departments = [
            {
                'name': 'Faculty',
                'order': 1,
                'description': 'Faculty clearance - Academic records and course completion verification'
            },
            {
                'name': 'Library',
                'order': 2,
                'description': 'Library clearance - No outstanding books or library fines'
            },
            {
                'name': 'Bursary',
                'order': 3,
                'description': 'Bursary clearance - All fees paid and financial obligations cleared'
            },
            {
                'name': 'ICT',
                'order': 4,
                'description': 'ICT clearance - Return of university ICT equipment and resources'
            },
            {
                'name': 'Hostel',
                'order': 5,
                'description': 'Hostel clearance - Room inspection and hostel fees verification'
            },
            {
                'name': 'Student Affairs',
                'order': 6,
                'description': 'Student Affairs clearance - Final verification and clearance certificate issuance'
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for dept_data in departments:
            dept, created = Department.objects.update_or_create(
                name=dept_data['name'],
                defaults={
                    'order': dept_data['order'],
                    'description': dept_data['description'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created: {dept.order}. {dept.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Updated: {dept.order}. {dept.name}')
                )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'✓ Setup complete!'))
        self.stdout.write(self.style.SUCCESS(f'  - Created: {created_count} departments'))
        self.stdout.write(self.style.SUCCESS(f'  - Updated: {updated_count} departments'))
        self.stdout.write(self.style.SUCCESS(f'  - Total: {len(departments)} departments'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        
        # Display the workflow order
        self.stdout.write(self.style.WARNING('Clearance Workflow Order:'))
        all_depts = Department.objects.filter(is_active=True).order_by('order')
        for dept in all_depts:
            self.stdout.write(f'  {dept.order}. {dept.name}')
        self.stdout.write('')