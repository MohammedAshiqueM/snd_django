# Generated by Django 5.1.3 on 2025-01-15 04:34

import django.db.models.deletion
import user_side.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_side', '0013_user_available_time_user_held_time_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='skillsharingrequest',
            name='requested_time',
        ),
        migrations.AddField(
            model_name='skillsharingrequest',
            name='duration_minutes',
            field=models.PositiveIntegerField(default=5, help_text='Requested session duration in minutes'),
        ),
        migrations.AddField(
            model_name='skillsharingrequest',
            name='preferred_time',
            field=models.DateTimeField(default=user_side.models.default_preferred_time, help_text='Preferred time for the session'),
        ),
        migrations.AddField(
            model_name='skillsharingrequest',
            name='status',
            field=models.CharField(choices=[('DR', 'Draft'), ('PE', 'Pending'), ('SC', 'Scheduled'), ('CO', 'Completed'), ('CA', 'Cancelled')], default='DR', max_length=2),
        ),
        migrations.AddField(
            model_name='skillsharingrequest',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='skillsharingrequest',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='skillsharingrequest',
            name='title',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='skillsharingrequest',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='learning_requests', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddIndex(
            model_name='skillsharingrequest',
            index=models.Index(fields=['status'], name='request_status_idx'),
        ),
        migrations.AddIndex(
            model_name='skillsharingrequest',
            index=models.Index(fields=['preferred_time'], name='request_time_idx'),
        ),
        migrations.AddIndex(
            model_name='skillsharingrequest',
            index=models.Index(fields=['created_at'], name='request_created_idx'),
        ),
    ]
