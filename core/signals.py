from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Node, Question
from .chroma_client import collection


@receiver(post_save, sender=Node)
def update_node_embedding(sender, instance, **kwargs):
    if instance.is_deleted:
        try:
            collection.delete(ids=[f"node_{instance.id}"])
        except Exception:
            pass
    else:
        text = f"{instance.title}\n\n{instance.content}"
        collection.upsert(
            documents=[text],
            metadatas=[
                {
                    "type": "node",
                    "project_id": instance.project.id,
                    "node_id": instance.id,
                }
            ],
            ids=[f"node_{instance.id}"],
        )


@receiver(post_save, sender=Question)
def update_question_embedding(sender, instance, **kwargs):
    if instance.is_deleted:
        try:
            collection.delete(ids=[f"question_{instance.id}"])
        except Exception:
            pass
    else:
        project_id = instance.source_node.project.id if instance.source_node else 0
        text = f"{instance.title}\n\n{instance.answer}"
        collection.upsert(
            documents=[text],
            metadatas=[
                {
                    "type": "question",
                    "project_id": project_id,
                    "question_id": instance.id,
                }
            ],
            ids=[f"question_{instance.id}"],
        )
