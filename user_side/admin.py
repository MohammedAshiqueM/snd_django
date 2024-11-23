from django.contrib import admin

from .models import (
    User, Follower, Tag, UserSkill, Blog, BlogTag, BlogVote, BlogComment, 
    Question, QuestionTag, QuestionVote, SkillSharingRequest, RequestTag,
    Schedule, Rating, Report, TimeTransaction
)

admin.site.register([User, Follower, Tag, UserSkill, Blog, BlogTag, BlogVote, BlogComment, 
    Question, QuestionTag, QuestionVote, SkillSharingRequest, RequestTag,
    Schedule, Rating, Report, TimeTransaction])