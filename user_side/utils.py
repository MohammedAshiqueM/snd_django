from rest_framework.response import Response
from rest_framework import status

def api_response(status, message, data=None, code=status.HTTP_200_OK):
    response = {
        "status" : status,
        "message" : message,
    }
    if data is not None:
        response.update(data)
    return Response(response, status=code)

from rest_framework_simplejwt.authentication import JWTAuthentication

class CustomJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        if request.path.startswith('/admin/'):
            return None
        print("body is :",request.body)
        print("the.......",request.COOKIES)
        # Check for token in the Authorization header
        header = self.get_header(request)
        raw_token = None

        if header:
            raw_token = self.get_raw_token(header)

        # If no token in the header, look in cookies
        if raw_token is None:
            raw_token = request.COOKIES.get('access_token')  # Check cookies for the token

        if raw_token is None:  # No token found
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
