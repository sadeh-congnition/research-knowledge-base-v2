from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import Node, Project


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


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("title", "type", "project", "is_deleted", "created_at", "updated_at")
    list_filter = ("type", "is_deleted", "project")
    search_fields = ("title", "content", "source_text", "project__name")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("project", "source_node")
    filter_horizontal = ("linked_nodes",)
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
