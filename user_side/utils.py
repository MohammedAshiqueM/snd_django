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

import jwt
from django.core.exceptions import PermissionDenied
from django.conf import settings

from rest_framework_simplejwt.tokens import AccessToken
from jwt import ExpiredSignatureError, InvalidTokenError as TokenError

def validate_access_token(token):
    try:
        decoded_token = AccessToken(token)
        print("Token is valid:", decoded_token)
        return decoded_token
    except TokenError as e:
        print("Token error:", str(e))
        if isinstance(e, ExpiredSignatureError):
            raise PermissionDenied("Token has expired. Please refresh.")
        raise PermissionDenied("Token is invalid.")
