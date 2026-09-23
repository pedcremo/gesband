from rest_framework.authentication import TokenAuthentication


class GesbandTokenAuthentication(TokenAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            return result
        # Keep development clients that used the documented DRF form working.
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if header.lower().startswith("token "):
            request.META["HTTP_AUTHORIZATION"] = "Bearer " + header.split(" ", 1)[1]
            return super().authenticate(request)
        return None
