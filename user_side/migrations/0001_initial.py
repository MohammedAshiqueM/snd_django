# Generated by Django 5.1.3 on 2024-11-20 16:38

import django.contrib.auth.models
import django.contrib.auth.validators
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import user_side.models
from django.conf import settings
from django.db import migrations, models
from cloudinary.models import CloudinaryField

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'db_table': 'tags',
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('profile_image', CloudinaryField('profile_image',folder='profile_images',null=True,blank=True,validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png']),user_side.models.validate_image_size],transformation={'width': 300,'height': 300,'crop': 'fill','gravity': 'face','quality': 'auto','format': 'jpg','fetch_format': 'auto'},help_text="Profile image of the user (max 5MB)")),
                ('banner_image', CloudinaryField('banner_image',folder='banner_images',null=True,blank=True,validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png']),user_side.models.validate_image_size],transformation={'width': 1200,'height': 400,'crop': 'fill','quality': 'auto','format': 'jpg'},help_text="Banner image for the user profile page (max 5MB)")),
                ('linkedin_url', models.URLField(blank=True, help_text='Your LinkedIn profile URL', validators=[django.core.validators.RegexValidator(message='Enter a valid LinkedIn URL (e.g., https://www.linkedin.com/in/username)', regex='^https:\\/\\/(www\\.)?linkedin\\.com\\/.*$')])),
                ('github_url', models.URLField(blank=True, help_text='Your GitHub profile URL', validators=[django.core.validators.RegexValidator(message='Enter a valid GitHub URL (e.g., https://github.com/username)', regex='^https:\\/\\/(www\\.)?github\\.com\\/.*$')])),
                ('about', models.TextField(blank=True, help_text='Tell us about yourself')),
                ('rating', models.DecimalField(blank=True, decimal_places=1, help_text='User rating (0-5)', max_digits=2, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(5)])),
                ('time_balance', models.IntegerField(default=0, help_text="User's remaining time balance in minutes", validators=[django.core.validators.MinValueValidator(0)])),
                ('last_active', models.DateTimeField(blank=True, help_text='Last time the user was active', null=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'db_table': 'user',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Blog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='Blog post title', max_length=50)),
                ('slug', models.SlugField(blank=True, help_text='URL-friendly version of the title', max_length=60, unique=True)),
                ('body_content', models.TextField(help_text='Main content of the blog post')),
                ('image', CloudinaryField('blog_image',folder='blog_images',null=True,blank=True,validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png']),user_side.models.validate_image_size],transformation={'width': 800,'height': 600,'crop': 'fill','quality': 'auto','format': 'jpg'},help_text="Featured image for the blog post (max 5MB)")),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_published', models.BooleanField(default=True, help_text='Whether the blog post is publicly visible')),
                ('view_count', models.PositiveIntegerField(default=0, help_text='Number of times this post has been viewed')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blogs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'blogs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BlogComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('blog', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user_side.blog')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'blog_comments',
            },
        ),
        migrations.CreateModel(
            name='Follower',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('followed_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('follower', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_followers', to=settings.AUTH_USER_MODEL)),
                ('following', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_following', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'followers',
                'unique_together': {('follower', 'following')},
            },
        ),
        migrations.AddField(
            model_name='user',
            name='followers',
            field=models.ManyToManyField(related_name='following', through='user_side.Follower', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('body_content', models.TextField()),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'questions',
            },
        ),
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.DecimalField(decimal_places=2, max_digits=3, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(5)])),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='student_ratings', to=settings.AUTH_USER_MODEL)),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='teacher_ratings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'ratings',
            },
        ),
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('note', models.TextField()),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('reported_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports_made', to=settings.AUTH_USER_MODEL)),
                ('reported_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports_received', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'reports',
            },
        ),
        migrations.CreateModel(
            name='SkillSharingRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=50)),
                ('body_content', models.TextField()),
                ('requested_time', models.DateTimeField()),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'skill_sharing_requests',
            },
        ),
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scheduled_at', models.DateTimeField()),
                ('timezone', models.CharField(max_length=50)),
                ('status', models.CharField(choices=[('PE', 'Pending'), ('AC', 'Accepted'), ('RE', 'Rejected'), ('CO', 'Completed'), ('CA', 'Cancelled')], default='PE', max_length=2)),
                ('note', models.TextField(blank=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='learning_schedules', to=settings.AUTH_USER_MODEL)),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='teaching_schedules', to=settings.AUTH_USER_MODEL)),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user_side.skillsharingrequest')),
            ],
            options={
                'db_table': 'schedules',
            },
        ),
        migrations.CreateModel(
            name='RequestTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user_side.skillsharingrequest')),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user_side.tag')),
            ],
            options={
                'db_table': 'request_tags',
                'unique_together': {('request', 'tag')},
            },
        ),
        migrations.AddField(
            model_name='skillsharingrequest',
            name='tags',
            field=models.ManyToManyField(through='user_side.RequestTag', to='user_side.tag'),
        ),
        migrations.CreateModel(
            name='QuestionTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user_side.question')),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user_side.tag')),
            ],
            options={
                'db_table': 'question_tags',
                'unique_together': {('question', 'tag')},
            },
        ),
        migrations.AddField(
            model_name='question',
            name='tags',
            field=models.ManyToManyField(through='user_side.QuestionTag', to='user_side.tag'),
        ),
        migrations.CreateModel(
            name='BlogTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('blog', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user_side.blog')),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user_side.tag')),
            ],
            options={
                'db_table': 'blog_tags',
                'unique_together': {('blog', 'tag')},
            },
        ),
        migrations.AddField(
            model_name='blog',
            name='tags',
            field=models.ManyToManyField(through='user_side.BlogTag', to='user_side.tag'),
        ),
        migrations.CreateModel(
            name='TimeTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_type', models.CharField(choices=[('CR', 'Credit'), ('DE', 'Debit')], max_length=2)),
                ('amount', models.IntegerField()),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('related_schedule', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='user_side.schedule')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'time_transactions',
            },
        ),
        migrations.CreateModel(
            name='UserSkill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user_side.tag')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'user_skills',
            },
        ),
        migrations.AddField(
            model_name='user',
            name='skills',
            field=models.ManyToManyField(through='user_side.UserSkill', to='user_side.tag'),
        ),
        migrations.CreateModel(
            name='BlogVote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vote', models.BooleanField()),
                ('blog', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user_side.blog')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'blog_votes',
                'unique_together': {('user', 'blog')},
            },
        ),
        migrations.CreateModel(
            name='QuestionVote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vote', models.BooleanField()),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user_side.question')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'question_vote',
                'unique_together': {('user', 'question')},
            },
        ),
        migrations.AddIndex(
            model_name='blog',
            index=models.Index(fields=['created_at'], name='blog_date_idx'),
        ),
        migrations.AddIndex(
            model_name='blog',
            index=models.Index(fields=['user'], name='blog_user_idx'),
        ),
        migrations.AddIndex(
            model_name='blog',
            index=models.Index(fields=['slug'], name='blog_slug_idx'),
        ),
        migrations.AddIndex(
            model_name='blog',
            index=models.Index(fields=['is_published'], name='blog_published_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='userskill',
            unique_together={('user', 'tag')},
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['email'], name='user_email_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['username'], name='user_username_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['rating'], name='user_rating_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['last_active'], name='user_last_active_idx'),
        ),
    ]
