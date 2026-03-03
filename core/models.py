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
    linked_questions = models.ManyToManyField(
        "Question", 
        blank=True, 
        related_name="incoming_node_links_via_content"
    )

    def __str__(self):
        return self.title

    @property
    def incoming_node_links(self):
        """Nodes that link TO this node."""
        return Node.objects.filter(linked_nodes=self, is_deleted=False)

    @property
    def outgoing_node_links(self):
        """Nodes that this node links TO."""
        return self.linked_nodes.filter(is_deleted=False)

    @property
    def incoming_question_links(self):
        """Questions that link TO this node."""
        return self.incoming_question_links_via_content.filter(is_deleted=False)

    @property
    def outgoing_question_links(self):
        """Questions that this node links TO."""
        return self.linked_questions.filter(is_deleted=False)

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        # Only update links if the node already exists (has a pk)
        # to avoid issues with M2M fields on unsaved objects.
        # Since we just called super().save(), it will have a pk.
        self.update_links_from_content()

    def update_links_from_content(self):
        if not self.content:
            self.linked_nodes.clear()
            self.linked_questions.clear()
            return

        # Match markdown links to nodes, e.g. [some text](/node/123/) or /project/1/#node-123
        node_pattern = r'\]\(/node/(\d+)/\)|\]\(/project/\d+/#node-(\d+)\)'
        q_pattern = r'\]\(/api/question/(\d+)/detail\)'

        try:
            # Re findall returns tuples if there are multiple groups
            node_matches = re.findall(node_pattern, self.content)
            node_ids = set()
            for match in node_matches:
                # match is a tuple like ('123', '') or ('', '123')
                for group in match:
                    if group:
                        node_ids.add(int(group))
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

        try:
            q_ids = set(int(pk) for pk in re.findall(q_pattern, self.content))
        except ValueError:
            q_ids = set()
            
        if q_ids:
            # Import Question locally to avoid circular dependencies if any
            from core.models import Question
            validated_questions = Question.objects.filter(pk__in=q_ids, is_deleted=False)
            self.linked_questions.set(validated_questions)
        else:
            self.linked_questions.clear()



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
    
    linked_nodes = models.ManyToManyField(
        Node, blank=True, related_name="incoming_question_links_via_content"
    )
    linked_questions = models.ManyToManyField(
        "self", blank=True, symmetrical=False, related_name="incoming_question_links_via_content"
    )

    def __str__(self) -> str:
        return self.title

    @property
    def project(self):
        """Helper to get the project this question belongs to."""
        if self.source_node:
            return self.source_node.project
        if self.source_question:
            # Recursive but usually only 1 level deep, could define a better way if depth increases
            return self.source_question.project
        return None

    @property
    def linked_from(self):
        """The source of this question (either a Node or a Question)."""
        if self.source_node:
            return self.source_node
        if self.source_question:
            return self.source_question
        return None

    @property
    def linked_to(self):
        """Nested questions under this question."""
        return self.nested_questions.filter(is_deleted=False)

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        self.update_links_from_content()

    def update_links_from_content(self):
        if not self.answer:
            self.linked_nodes.clear()
            self.linked_questions.clear()
            return

        node_pattern = r'\]\(/node/(\d+)/\)|\]\(/project/\d+/#node-(\d+)\)'
        q_pattern = r'\]\(/api/question/(\d+)/detail\)'

        # Parse Node Links
        try:
            node_matches = re.findall(node_pattern, self.answer)
            node_ids = set()
            for match in node_matches:
                for group in match:
                    if group:
                        node_ids.add(int(group))
        except ValueError:
            node_ids = set()
            
        if node_ids:
            validated_nodes = Node.objects.filter(pk__in=node_ids, is_deleted=False)
            self.linked_nodes.set(validated_nodes)
        else:
            self.linked_nodes.clear()

        # Parse Question Links
        try:
            q_ids = set(int(pk) for pk in re.findall(q_pattern, self.answer))
        except ValueError:
            q_ids = set()
            
        # Avoid linking to self
        if self.pk in q_ids:
            q_ids.remove(self.pk)

        if q_ids:
            validated_questions = Question.objects.filter(pk__in=q_ids, is_deleted=False)
            self.linked_questions.set(validated_questions)
        else:
            self.linked_questions.clear()
