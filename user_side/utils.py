from rest_framework.response import Response
from rest_framework import status

def api_response(status, message, data=None,):
    response = {
        "status" : status,
        "message" : message,
    }
    if data is not None:
        response.update(data)
    return Response(response, status=status)

from rest_framework_simplejwt.authentication import JWTAuthentication

class CustomJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        print("body is :",request.body)
        print("the.......",request.COOKIES)
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
