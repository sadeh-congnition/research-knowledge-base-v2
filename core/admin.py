from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import Node, Project, Question


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "is_deleted", "created_at", "updated_at")
    list_filter = ("is_deleted",)
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")
    actions = ["soft_delete_selected", "restore_selected"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Project]:
        # Show all objects including soft-deleted in admin
        return Project.all_objects.all()

    @admin.action(description="Soft delete selected projects")
    def soft_delete_selected(
        self, request: HttpRequest, queryset: QuerySet[Project]
    ) -> None:
        for obj in queryset:
            obj.soft_delete()

    @admin.action(description="Restore selected projects")
    def restore_selected(
        self, request: HttpRequest, queryset: QuerySet[Project]
    ) -> None:
        queryset.update(is_deleted=False)


class QuestionInline(admin.TabularInline):  # type: ignore[type-arg]
    model = Question
    fk_name = "source_node"
    extra = 0
    fields = ("title", "answer", "is_deleted")
    readonly_fields = ("is_deleted",)
    show_change_link = True


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("title", "project", "is_deleted", "created_at", "updated_at")
    list_filter = ("is_deleted", "project")
    search_fields = ("title", "content", "project__name")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("project",)
    filter_horizontal = ("linked_nodes",)
    inlines = [QuestionInline]
    actions = ["soft_delete_selected", "restore_selected"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Node]:
        return Node.all_objects.select_related("project").all()

    @admin.action(description="Soft delete selected nodes")
    def soft_delete_selected(
        self, request: HttpRequest, queryset: QuerySet[Node]
    ) -> None:
        for obj in queryset:
            obj.soft_delete()

    @admin.action(description="Restore selected nodes")
    def restore_selected(self, request: HttpRequest, queryset: QuerySet[Node]) -> None:
        queryset.update(is_deleted=False)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "title",
        "source_node",
        "source_question",
        "is_deleted",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_deleted",)
    search_fields = ("title", "answer", "source_node__title", "source_question__title")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("source_node", "source_question")
    actions = ["soft_delete_selected", "restore_selected"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Question]:
        return Question.all_objects.select_related(
            "source_node", "source_question"
        ).all()

    @admin.action(description="Soft delete selected questions")
    def soft_delete_selected(
        self, request: HttpRequest, queryset: QuerySet[Question]
    ) -> None:
        for obj in queryset:
            obj.soft_delete()

    @admin.action(description="Restore selected questions")
    def restore_selected(
        self, request: HttpRequest, queryset: QuerySet[Question]
    ) -> None:
        queryset.update(is_deleted=False)
