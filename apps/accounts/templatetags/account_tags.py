from django import template

register = template.Library()


@register.simple_tag
def user_display_name(user) -> str:
    """Return the best display name for a user.

    Prefers full name, falls back to first name, then email local part.
    """
    if user.get_full_name():
        return user.get_full_name()
    if user.first_name:
        return user.first_name
    return user.email.split('@')[0]
