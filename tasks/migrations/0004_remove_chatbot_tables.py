from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql='''
            DROP TABLE IF EXISTS chatbot_chatmessage;
            DROP TABLE IF EXISTS chatbot_chatsession;
            DELETE FROM django_migrations WHERE app = 'chatbot';
            ''',
            reverse_sql='',
        ),
    ]
