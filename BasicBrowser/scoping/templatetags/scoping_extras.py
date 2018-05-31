from django import template

register = template.Library()

@register.filter
def keyvalue(dict, key):
    return dict[key]


@register.filter(name='field_type')
def field_type(field):
    return field.field.widget.__class__.__name__
