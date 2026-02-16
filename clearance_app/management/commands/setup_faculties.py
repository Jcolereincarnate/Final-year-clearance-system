"""
Management command to create default faculties for ACU
Usage: python manage.py setup_faculties
"""
from django.core.management.base import BaseCommand
from clearance_app.models import Faculty


class Command(BaseCommand):
    help = 'Creates default faculties for ACU'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Setting up faculties...'))
        
        # Define common ACU faculties
        faculties = [
            {
                'name': 'Faculty of Humanities',
                'code': 'HUM',
                'description': 'Arts, Languages, Philosophy, Religious Studies, History',
            },
            {
                'name': 'Faculty of Natural Sciences',
                'code': 'SCI',
                'description': 'Biology, Chemistry, Physics, Mathematics, Computer Science',
            },
            {
                'name': 'Faculty of Social Sciences',
                'code': 'SOC',
                'description': 'Economics, Sociology, Political Science, Psychology, Mass Communication',
            },
            {
                'name': 'Faculty of Management Sciences',
                'code': 'MGT',
                'description': 'Business Administration, Accounting, Banking & Finance',
            },
            {
                'name': 'Faculty of Environmental Sciences',
                'code': 'ENV',
                'description': 'Estate Management, Architecture, Urban & Regional Planning',
            },
            {
                'name': 'Faculty of Law',
                'code': 'LAW',
                'description': 'Law programs',
            },
            {
                'name': 'Faculty of Education',
                'code': 'EDU',
                'description': 'Education and Teaching programs',
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for faculty_data in faculties:
            faculty, created = Faculty.objects.update_or_create(
                code=faculty_data['code'],
                defaults={
                    'name': faculty_data['name'],
                    'description': faculty_data['description'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created: {faculty.name} ({faculty.code})')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Updated: {faculty.name} ({faculty.code})')
                )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'✓ Setup complete!'))
        self.stdout.write(self.style.SUCCESS(f'  - Created: {created_count} faculties'))
        self.stdout.write(self.style.SUCCESS(f'  - Updated: {updated_count} faculties'))
        self.stdout.write(self.style.SUCCESS(f'  - Total: {len(faculties)} faculties'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        
        # Display all faculties
        self.stdout.write(self.style.WARNING('Available Faculties:'))
        all_faculties = Faculty.objects.filter(is_active=True).order_by('name')
        for faculty in all_faculties:
            self.stdout.write(f'  {faculty.code}: {faculty.name}')
        self.stdout.write('')