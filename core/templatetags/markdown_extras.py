from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
import json
import markdown as md

register = template.Library()


@register.filter(name="markdown")
@stringfilter
def markdown_format(text: str) -> str:
    return md.markdown(text, extensions=["fenced_code", "tables"])


@register.filter(name="to_json")
def to_json(value: object) -> str:
    """Serialize a Python value to a safe JSON string for use in <script> blocks."""
    return json.dumps(value)


@register.simple_tag
def node_questions_json(node: object) -> str:
    """Return a JSON array of {id, source_text, title} for questions with source_text."""
    from core.models import Node  # local import to avoid circular

    qs = (
        Node.objects.filter(source_node=node, type='question', is_deleted=False)  # type: ignore[attr-defined]
        .exclude(source_text="")
        .values("id", "source_text", "title")
    )
    data = [{
        "id": q["id"],
        "source_text": q["source_text"],
        "title": q["title"],
    } for q in qs]
    return mark_safe(json.dumps(data))
