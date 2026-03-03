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

            body_data = parse_qs(request.body.decode("utf-8"))
            ids = body_data.get("ids", [])
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


def _generate_graph_data(project_pk: int | None = None) -> dict:
    edges = set()  # set of tuples: (source_id, target_id)
    nodes_graph_data = set()  # set of tuples: (id, label, group)

    if not project_pk:
        # Global graph: all nodes, all questions, all edges
        for node in Node.objects.filter(is_deleted=False):
            nodes_graph_data.add((f"node_{node.pk}", node.title, "node"))
            for linked in node.linked_nodes.filter(is_deleted=False):
                edges.add((f"node_{node.pk}", f"node_{linked.pk}"))
            for linked in node.linked_questions.filter(is_deleted=False):
                edges.add((f"node_{node.pk}", f"question_{linked.pk}"))
            for q in node.questions.filter(is_deleted=False):
                edges.add((f"node_{node.pk}", f"question_{q.pk}"))
                
        for q in Question.objects.filter(is_deleted=False):
            nodes_graph_data.add((f"question_{q.pk}", q.title, "question"))
            for linked in q.linked_nodes.filter(is_deleted=False):
                edges.add((f"question_{q.pk}", f"node_{linked.pk}"))
            for linked in q.linked_questions.filter(is_deleted=False):
                edges.add((f"question_{q.pk}", f"question_{linked.pk}"))
            for n_q in q.nested_questions.filter(is_deleted=False):
                edges.add((f"question_{q.pk}", f"question_{n_q.pk}"))

    else:
        # Single project graph
        project = get_object_or_404(Project, pk=project_pk, is_deleted=False)
        core_nodes = set(project.nodes.filter(is_deleted=False))
        
        all_included_nodes = set(core_nodes)
        all_included_questions = set()

        for node in core_nodes:
            # Outgoing node edges
            for linked in node.linked_nodes.filter(is_deleted=False):
                all_included_nodes.add(linked)
                edges.add((f"node_{node.pk}", f"node_{linked.pk}"))

            # Incoming node edges (tests want this)
            for linked in node.incoming_node_links:
                all_included_nodes.add(linked)
                edges.add((f"node_{linked.pk}", f"node_{node.pk}"))
                
            # Outgoing question links from content
            for linked in node.linked_questions.filter(is_deleted=False):
                all_included_questions.add(linked)
                edges.add((f"node_{node.pk}", f"question_{linked.pk}"))
                
            # Questions belonging to core nodes
            for q in node.questions.filter(is_deleted=False):
                all_included_questions.add(q)
                edges.add((f"node_{node.pk}", f"question_{q.pk}"))

        # Process all_included_nodes (including peripheral nodes)
        for node in all_included_nodes:
            title = node.title
            if node not in core_nodes and node.project:
                # Show source project for external nodes
                title = f"{node.title} ({node.project.name})"
            nodes_graph_data.add((f"node_{node.pk}", title, "node"))
            
            # Edges to their questions
            for q in node.questions.filter(is_deleted=False):
                all_included_questions.add(q)
                edges.add((f"node_{node.pk}", f"question_{q.pk}"))

        # Process all_included_questions to capture nested questions
        questions_to_process = list(all_included_questions)
        processed_questions = set()
        while questions_to_process:
            q = questions_to_process.pop()
            if q in processed_questions:
                continue
            processed_questions.add(q)
            
            nodes_graph_data.add((f"question_{q.pk}", q.title, "question"))
            
            for n_q in q.nested_questions.filter(is_deleted=False):
                questions_to_process.append(n_q)
                edges.add((f"question_{q.pk}", f"question_{n_q.pk}"))
                
            for linked in q.linked_questions.filter(is_deleted=False):
                questions_to_process.append(linked)
                edges.add((f"question_{q.pk}", f"question_{linked.pk}"))
                
            for linked in q.linked_nodes.filter(is_deleted=False):
                # Don't explore external nodes arbitrarily, but show the edge if node is already present
                edges.add((f"question_{q.pk}", f"node_{linked.pk}"))

    return {
        "nodes": [
            {"id": id_, "label": label, "group": group}
            for id_, label, group in nodes_graph_data
        ],
        "edges": [
            {"source": source_id, "target": target_id}
            for source_id, target_id in edges
        ],
    }


@router.get("/project/{project_pk}/graph", response=GraphData)
def project_graph(request, project_pk: int):
    return _generate_graph_data(project_pk=project_pk)


@router.get("/graph", response=GraphData)
def global_graph(request):
    return _generate_graph_data()
