from django import template

register = template.Library()

@register.filter
def es_admin(user):
    return user.groups.filter(name='admins').exists()