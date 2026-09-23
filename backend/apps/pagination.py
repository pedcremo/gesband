from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from urllib.parse import parse_qs, urlparse


class GesbandCursorPagination(CursorPagination):
    ordering = "-created_at"
    page_size = 50
    page_size_query_param = "page[size]"
    cursor_query_param = "page[cursor]"
    max_page_size = 100

    def get_ordering(self, request, queryset, view):
        view_ordering = getattr(view, "ordering", None)
        if view_ordering:
            return (view_ordering,) if isinstance(view_ordering, str) else tuple(view_ordering)
        return super().get_ordering(request, queryset, view)

    def get_paginated_response(self, data):
        next_link = self.get_next_link()
        cursor = None
        if next_link:
            cursor = parse_qs(urlparse(next_link).query).get(self.cursor_query_param, [None])[0]
        return Response({"results": data, "next_cursor": cursor})
