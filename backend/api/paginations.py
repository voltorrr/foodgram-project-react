from rest_framework.pagination import PageNumberPagination
from django.conf import settings


class ApiPagination(PageNumberPagination):
    page_size_query_param = "limit"
    pages = settings.PAGE_SIZE
