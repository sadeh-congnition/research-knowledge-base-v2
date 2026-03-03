from django.db import models
import re


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_deleted = True
        self.save()


class Project(SoftDeleteModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Node(SoftDeleteModel):
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="nodes")
    linked_nodes = models.ManyToManyField("self", blank=True, symmetrical=False)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        # Only update links if the node already exists (has a pk)
        # to avoid issues with M2M fields on unsaved objects.
        # Since we just called super().save(), it will have a pk.
        self.update_links_from_content()

    def update_links_from_content(self):
        if not self.content:
            self.linked_nodes.clear()
            return

        # Match markdown links to nodes, e.g. [some text](/node/123/)
        pattern = r'\]\(/node/(\d+)/\)'

        try:
            node_ids = set(int(pk_str) for pk_str in re.findall(pattern, self.content))
        except ValueError:
            node_ids = set()

        # Avoid linking to self
        if self.pk in node_ids:
            node_ids.remove(self.pk)

        if node_ids:
            validated_nodes = Node.objects.filter(pk__in=node_ids, is_deleted=False)
            self.linked_nodes.set(validated_nodes)
        else:
            self.linked_nodes.clear()


class Question(SoftDeleteModel):
    title = models.CharField(max_length=255)
    answer = models.TextField(blank=True)
    # Optional: the exact block of text in the source node that prompted this question
    source_text = models.TextField(blank=True, default="")
    source_node = models.ForeignKey(
        Node, on_delete=models.SET_NULL, null=True, blank=True, related_name="questions"
    )
    source_question = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nested_questions",
    )

    def __str__(self) -> str:
        return self.title
