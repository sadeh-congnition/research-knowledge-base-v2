from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Node
from .chroma_client import collection


@receiver(post_save, sender=Node)
def update_node_embedding(sender, instance, **kwargs):
    if instance.is_deleted:
        try:
            prefix = 'question' if instance.type == 'question' else 'node'
            collection.delete(ids=[f"{prefix}_{instance.id}"])
        except Exception:
            pass
    else:
        text = f"{instance.title}\n\n{instance.content}"
        prefix = 'question' if instance.type == 'question' else 'node'
        meta = {
            "type": instance.type,
            "project_id": instance.project.id,
            "node_id": instance.id,
        }
        if instance.type == 'question':
            meta["question_id"] = instance.id
            
        collection.upsert(
            documents=[text],
            metadatas=[meta],
            ids=[f"{prefix}_{instance.id}"],
        )
