from django.db import models
from django.utils import timezone


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


class Question(SoftDeleteModel):
    title = models.CharField(max_length=255)
    answer = models.TextField(blank=True)
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

    def __str__(self):
        return self.title
