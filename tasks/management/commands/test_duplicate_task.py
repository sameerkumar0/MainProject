from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tasks.models import Task
from tasks.serializers import TaskSerializer
from rest_framework.test import APIRequestFactory
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Test duplicate task prevention'

    def handle(self, *args, **options):
        # Find a manager user
        try:
            manager = User.objects.filter(role='Manager').first()
            if not manager:
                self.stdout.write(self.style.ERROR('No manager user found. Please create a manager user first.'))
                return
            
            self.stdout.write(self.style.SUCCESS(f'Using manager: {manager.username}'))
            
            # Create a factory request
            factory = APIRequestFactory()
            request = factory.post('/api/tasks/create/')
            request.user = manager
            
            # Task data
            task_data = {
                'title': 'Test Duplicate Task',
                'description': 'This is a test task to check duplicate prevention',
                'priority': 'medium',
                'due_date': timezone.now() + timezone.timedelta(days=7)
            }
            
            # First attempt - should succeed
            self.stdout.write(self.style.NOTICE('First task creation attempt:'))
            serializer1 = TaskSerializer(data=task_data, context={'request': request})
            
            if serializer1.is_valid():
                task = serializer1.save(assigned_by=manager)
                self.stdout.write(self.style.SUCCESS(f'Task created successfully with ID: {task.id}'))
            else:
                self.stdout.write(self.style.ERROR(f'Task creation failed: {serializer1.errors}'))
            
            # Second attempt with the same data - should fail
            self.stdout.write(self.style.NOTICE('\nSecond task creation attempt (duplicate):'))
            serializer2 = TaskSerializer(data=task_data, context={'request': request})
            
            if serializer2.is_valid():
                task = serializer2.save(assigned_by=manager)
                self.stdout.write(self.style.ERROR(f'Duplicate task created with ID: {task.id} - This should not happen!'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Duplicate task prevented: {serializer2.errors}'))
            
            # Third attempt with different title - should succeed
            self.stdout.write(self.style.NOTICE('\nThird task creation attempt (different title):'))
            task_data['title'] = 'Different Test Task'
            serializer3 = TaskSerializer(data=task_data, context={'request': request})
            
            if serializer3.is_valid():
                task = serializer3.save(assigned_by=manager)
                self.stdout.write(self.style.SUCCESS(f'Task with different title created successfully with ID: {task.id}'))
            else:
                self.stdout.write(self.style.ERROR(f'Task creation failed: {serializer3.errors}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
