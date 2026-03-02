from django import template
from django.template.defaultfilters import stringfilter
import markdown as md

register = template.Library()


@register.filter(name="markdown")
@stringfilter
def markdown_format(text):
    return md.markdown(text, extensions=["fenced_code", "tables"])
