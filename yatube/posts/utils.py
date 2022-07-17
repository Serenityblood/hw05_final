from django.conf import settings
from django.core.paginator import Paginator


def paginator_func(request, posts_list):
    paginator = Paginator(posts_list, settings.PAGE_NUMBER)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
