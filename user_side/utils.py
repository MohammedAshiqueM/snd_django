from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
import os
from django.utils.timezone import now


def api_response(status, message, data=None,):
    response = {
        "status" : status,
        "message" : message,
    }
    if data is not None:
        if isinstance(data, dict):
            response.update(data)
        else:
            response["data"] = data 
    return Response(response, status=status)


class CustomJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        print("body is :",request.body)
        # print("the.......",request.COOKIES)
        header = self.get_header(request)
        raw_token = None

        if header:
            raw_token = self.get_raw_token(header)

        if raw_token is None:
            raw_token = request.COOKIES.get('access_token') 

        if raw_token is None: 
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token


def user_profile_image_path(instance, filename):
    return os.path.join('profile_images', str(instance.id), filename)

def user_banner_image_path(instance, filename):
    return os.path.join('banner_images', str(instance.id), filename)
