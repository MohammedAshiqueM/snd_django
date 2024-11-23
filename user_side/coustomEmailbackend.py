from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

class EmailBackend(ModelBackend):
    """ custome authentication backend for users to log in with there email """
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email=username)
        except UserModel.DoesNotExist:
            return None
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None

    def user_can_authenticate(self, user):
        """ Rejects inactive users. Matches behavior of Django's built-in backends """
        return getattr(user, 'is_active', False)