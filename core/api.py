import json
from ninja import NinjaAPI, Router, Schema, Form, Query
from typing import List
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse
from .models import Project, Node, Question
from . import services


class GraphNode(Schema):
    id: str
    label: str
    group: str


class GraphEdge(Schema):
    source: str
    target: str


class GraphData(Schema):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


api = NinjaAPI()
router = Router()


class SearchResult(Schema):
    id: int
    title: str
    type: str


@router.get("/autocomplete", response=List[SearchResult])
def autocomplete(request, q: str = ""):
    if not q:
        return []

    words = q.split()

    node_query = Q(is_deleted=False)
    question_query = Q(is_deleted=False)

    for word in words:
        node_query &= Q(title__icontains=word)
        question_query &= Q(title__icontains=word)

    nodes = Node.objects.filter(node_query)[:10]
    questions = Question.objects.filter(question_query)[:10]

    results = []
    for n in nodes:
        results.append(SearchResult(id=n.id, title=n.title, type="node"))
    for qu in questions:
        results.append(SearchResult(id=qu.id, title=qu.title, type="question"))

    # Sort and limit
    results.sort(key=lambda x: x.title.lower())
    return results[:10]


@router.get("/search/")
def search(request, q: str = ""):
    if not q:
        return render(
            request, "core/partials/search_results.html", {"results": [], "query": q}
        )

    results = services.perform_vector_search(q)
    return render(
        request, "core/partials/search_results.html", {"results": results, "query": q}
    )


@router.post("/node/{node_pk}/question")
def create_question(
    request,
    node_pk: int,
    title: str = Form(""),
    answer: str = Form(""),
    source_text: str = Form(""),
) -> HttpResponse:
    node = get_object_or_404(Node, pk=node_pk, is_deleted=False)
    if title:
        services.create_question(title, answer, node, source_text=source_text)

    questions = node.questions.filter(is_deleted=False).order_by("created_at")
    return render(
        request,
        "core/partials/question_list_items.html",
        {"questions": questions, "node": node},
    )


@router.get("/question/{question_pk}/edit")
def edit_question(request: HttpRequest, question_pk: int) -> HttpResponse:
    question = get_object_or_404(Question, pk=question_pk, is_deleted=False)
    return render(
        request, "core/partials/question_edit_form.html", {"question": question}
    )


@router.get("/question/{question_pk}/detail")
def question_detail_partial(request: HttpRequest, question_pk: int) -> HttpResponse:
    """Return the question detail overlay partial for HTMX."""
    question = get_object_or_404(Question, pk=question_pk, is_deleted=False)
    return render(
        request,
        "core/partials/question_detail_overlay.html",
        {"question": question},
    )


@router.get("/question/{question_pk}/cancel_edit")
def cancel_edit_question(request, question_pk: int):
    question = get_object_or_404(Question, pk=question_pk, is_deleted=False)
    return render(
        request, "core/partials/question_list_items.html", {"questions": [question]}
    )


@router.post("/question/{question_pk}")
def update_question(
    request, question_pk: int, title: str = Form(""), answer: str = Form("")
):
    question = get_object_or_404(Question, pk=question_pk, is_deleted=False)

    if title:
        services.update_question(question, title, answer)

    return render(
        request, "core/partials/question_list_items.html", {"questions": [question]}
    )


@router.delete("/question/{question_pk}")
def delete_question(request, question_pk: int):
    question = get_object_or_404(Question, pk=question_pk, is_deleted=False)
    services.delete_question(question)
    return HttpResponse("")


api.add_router("", router)


@router.get("/chroma/collections/")
def chroma_list_collections(request: HttpRequest) -> HttpResponse:
    collections = services.list_chroma_collections()
    return render(
        request, "core/partials/chroma_collections.html", {"collections": collections}
    )


@router.get("/chroma/collections/{collection_name}/documents/")
def chroma_list_documents(request: HttpRequest, collection_name: str) -> HttpResponse:
    try:
        documents = services.list_chroma_documents(collection_name)
    except Exception:
        documents = []
    return render(
        request,
        "core/partials/chroma_documents.html",
        {"documents": documents, "collection_name": collection_name},
    )


@router.delete("/chroma/collections/")
def chroma_delete_collections(
    request: HttpRequest, names: List[str] = Query([])
) -> HttpResponse:
    # If names is empty, try to get from JSON body (legacy support)
    if not names:
        try:
            body = json.loads(request.body)
            names = body.get("names", [])
        except Exception:
            names = []

    if names:
        services.delete_chroma_collections(names)

    collections = services.list_chroma_collections()
    return render(
        request, "core/partials/chroma_collections.html", {"collections": collections}
    )


@router.delete("/chroma/collections/{collection_name}/documents/")
def chroma_delete_documents(
    request: HttpRequest, collection_name: str, ids: List[str] = Query([])
) -> HttpResponse:
    # If ids is empty, try to get from form data (HTMX sends as form parameters)
    if not ids:
        ids = request.POST.getlist("ids")

    # If still empty, try parsing URL-encoded body manually
    if not ids and request.body:
        try:
            from urllib.parse import parse_qs
            body_data = parse_qs(request.body.decode('utf-8'))
            ids = body_data.get('ids', [])
        except Exception:
            ids = []

    # If still empty, try JSON body (legacy support)
    if not ids:
        try:
            body = json.loads(request.body)
            ids = body.get("ids", [])
        except Exception:
            ids = []

    if ids:
        services.delete_chroma_documents(collection_name, ids)

    try:
        documents = services.list_chroma_documents(collection_name)
    except Exception:
        documents = []

    return render(
        request,
        "core/partials/chroma_documents.html",
        {"documents": documents, "collection_name": collection_name},
    )


@router.get("/project/{project_pk}/edit")
def edit_project(request, project_pk: int):
    project = get_object_or_404(Project, pk=project_pk, is_deleted=False)
    return render(
        request, "core/partials/project_title_edit_form.html", {"project": project}
    )


@router.get("/project/{project_pk}/cancel_edit")
def cancel_edit_project(request, project_pk: int):
    project = get_object_or_404(Project, pk=project_pk, is_deleted=False)
    return render(request, "core/partials/project_title.html", {"project": project})


@router.post("/project/{project_pk}")
def update_project(request, project_pk: int, name: str = Form("")):
    project = get_object_or_404(Project, pk=project_pk, is_deleted=False)

    if name:
        services.update_project(project, name)

    return render(request, "core/partials/project_title.html", {"project": project})


@router.get("/project/{project_pk}/graph", response=GraphData)
def project_graph(request, project_pk: int):
    project = get_object_or_404(Project, pk=project_pk, is_deleted=False)
    nodes_data = []
    edges_data = []

    # Get all nodes in the current project
    project_nodes = list(project.nodes.filter(is_deleted=False))
    project_node_pks = set(n.pk for n in project_nodes)

    # Track included nodes and edges
    included_node_pks = set(project_node_pks)
    all_included_nodes = {n.pk: n for n in project_nodes}
    added_edges = set()

    # 1. Outgoing links from project nodes to external nodes
    for node in project_nodes:
        for linked in node.linked_nodes.filter(is_deleted=False):
            if linked.pk not in included_node_pks:
                included_node_pks.add(linked.pk)
                all_included_nodes[linked.pk] = linked

            edge = (node.pk, linked.pk)
            if edge not in added_edges:
                edges_data.append(
                    {"source": f"node_{node.pk}", "target": f"node_{linked.pk}"}
                )
                added_edges.add(edge)

    # 2. Incoming links from external nodes to project nodes
    incoming_linking_nodes = (
        Node.objects.filter(linked_nodes__in=project_nodes, is_deleted=False)
        .exclude(pk__in=project_node_pks)
        .distinct()
    )

    for other_node in incoming_linking_nodes:
        if other_node.pk not in included_node_pks:
            included_node_pks.add(other_node.pk)
            all_included_nodes[other_node.pk] = other_node

        # Add edges for all links from this external node to our project nodes
        for target in other_node.linked_nodes.filter(
            pk__in=project_node_pks, is_deleted=False
        ):
            edge = (other_node.pk, target.pk)
            if edge not in added_edges:
                edges_data.append(
                    {"source": f"node_{other_node.pk}", "target": f"node_{target.pk}"}
                )
                added_edges.add(edge)

    # 3. Add all included nodes to nodes_data
    for pk, node in all_included_nodes.items():
        label = node.title
        if node.project_id != project_pk:
            label = f"{node.title} [{node.project.name}]"

        nodes_data.append({"id": f"node_{pk}", "label": label, "group": "node"})

    # 4. Add questions for all included nodes (project and external)
    def add_questions(source_id, questions_qs):
        for q in questions_qs:
            q_id = f"question_{q.pk}"
            nodes_data.append({"id": q_id, "label": q.title, "group": "question"})
            edges_data.append({"source": source_id, "target": q_id})
            add_questions(q_id, q.nested_questions.filter(is_deleted=False))

    for pk, node in all_included_nodes.items():
        node_id = f"node_{pk}"
        add_questions(node_id, node.questions.filter(is_deleted=False))

    return {"nodes": nodes_data, "edges": edges_data}
