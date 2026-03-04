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
    NODE_TYPE_CHOICES = (
        ('node', 'Node'),
        ('question', 'Question'),
    )
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=NODE_TYPE_CHOICES, default='node')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="nodes")
    linked_nodes = models.ManyToManyField("self", blank=True, symmetrical=False)
    
    # Specific to questions
    source_text = models.TextField(blank=True, default="")
    source_node = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="questions"
    )

    def __str__(self):
        return self.title

    @property
    def answer(self):
        # Alias for templates that might still use question.answer before they update
        return self.content
        
    @answer.setter
    def answer(self, value):
        self.content = value

    @property
    def incoming_node_links(self):
        """Nodes that link TO this node."""
        return Node.objects.filter(linked_nodes=self, type='node', is_deleted=False)

    @property
    def outgoing_node_links(self):
        """Nodes that this node links TO."""
        return self.linked_nodes.filter(type='node', is_deleted=False)

    @property
    def incoming_question_links(self):
        """Questions that link TO this node."""
        return Node.objects.filter(linked_nodes=self, type='question', is_deleted=False)

    @property
    def outgoing_question_links(self):
        """Questions that this node links TO."""
        return self.linked_nodes.filter(type='question', is_deleted=False)

    @property
    def linked_from(self):
        """The source of this question (either a Node or a Question)."""
        return self.source_node

    @property
    def nested_questions(self):
        return self.questions.filter(type='question', is_deleted=False)

    @property
    def linked_to(self):
        """Nested questions under this question."""
        return self.nested_questions

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        # Only update links if the node already exists (has a pk)
        self.update_links_from_content()

    def update_links_from_content(self):
        if not self.content:
            self.linked_nodes.clear()
            return

        # Match markdown links to nodes, e.g. [some text](/node/123/) or /project/1/#node-123
        node_pattern = r'\]\(/node/(\d+)/\)|\]\(/project/\d+/#node-(\d+)\)'
        q_pattern = r'\]\(/api/question/(\d+)/detail\)'

        try:
            node_matches = re.findall(node_pattern, self.content)
            node_ids = set()
            for match in node_matches:
                for group in match:
                    if group:
                        node_ids.add(int(group))
        except ValueError:
            node_ids = set()

        try:
            q_ids = set(int(pk) for pk in re.findall(q_pattern, self.content))
        except ValueError:
            q_ids = set()

        all_ids = node_ids.union(q_ids)

        # Avoid linking to self
        if self.pk in all_ids:
            all_ids.remove(self.pk)

        if all_ids:
            validated_nodes = Node.objects.filter(pk__in=all_ids, is_deleted=False)
            self.linked_nodes.set(validated_nodes)
        else:
            self.linked_nodes.clear()




