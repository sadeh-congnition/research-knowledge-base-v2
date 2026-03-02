from django.urls import path
from . import views

urlpatterns = [
    path("", views.project_list, name="project_list"),
    path("project/<int:pk>/", views.project_detail, name="project_detail"),
    path("project/<int:pk>/delete/", views.project_delete, name="project_delete"),
    path("node/<int:pk>/", views.node_detail, name="node_detail"),
    path(
        "node/<int:pk>/delete/", views.node_delete, name="node_delete"
    ),
    path("node/<int:pk>/edit/", views.node_edit, name="node_edit"),
    path("node/<int:pk>/cancel/", views.node_cancel_edit, name="node_cancel_edit"),
    path("node/<int:pk>/update/", views.node_update, name="node_update"),
    path("question/<int:pk>/", views.question_detail, name="question_detail"),
    path("search/", views.global_search, name="global_search"),
    path("chroma/", views.chroma_browser, name="chroma_browser"),
]
