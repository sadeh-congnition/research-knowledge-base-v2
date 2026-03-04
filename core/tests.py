import json
import pytest
from core.chroma_client import collection, get_chroma_client
from core.models import Project, Node
from django.urls import reverse
from model_bakery import baker
from ninja.testing import TestClient
from core.api import router


@pytest.fixture
def project(db):
    return baker.make(Project, name="Test Project")


@pytest.fixture
def node(db, project):
    return baker.make(Node, title="Test Node", content="Node Content", project=project)


@pytest.fixture
def question(db, node):
    return baker.make(Node, type='question', title="Test Question", content="Question Answer",
        source_node=node,
    )


@pytest.mark.django_db
def test_project_list_get(client, project):
    response = client.get(reverse("project_list"))
    assert response.status_code == 200
    assert "Test Project" in response.content.decode()


@pytest.mark.django_db
def test_project_create_post(client):
    response = client.post(reverse("project_list"), {"name": "New Project"})
    assert response.status_code == 302
    assert Project.objects.filter(name="New Project").exists()


@pytest.mark.django_db
def test_project_delete(client, project):
    response = client.post(
        reverse("project_delete", kwargs={"pk": project.pk}),
        {"_method": "DELETE"},
    )
    assert response.status_code == 302
    project.refresh_from_db()
    assert project.is_deleted is True


@pytest.mark.django_db
def test_node_create_post(client, project):
    response = client.post(
        reverse("project_detail", kwargs={"pk": project.pk}),
        {"title": "New Node", "content": "Content"},
    )
    assert response.status_code == 302
    assert Node.objects.filter(title="New Node").exists()


@pytest.mark.django_db
def test_node_update(client, node):
    response = client.post(
        reverse("node_update", kwargs={"pk": node.pk}),
        {"title": "Updated Node", "content": "Updated Content"},
    )
    assert response.status_code == 302
    node.refresh_from_db()
    assert node.title == "Updated Node"


@pytest.mark.django_db
def test_autocomplete_api(node, question):
    test_client = TestClient(router)
    response = test_client.get("/autocomplete?q=Test")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    titles = [item["title"] for item in data]
    assert "Test Node" in titles
    assert "Test Question" in titles


@pytest.mark.django_db
def test_global_search_view(client, node):
    response = client.get(reverse("global_search") + "?q=Test")
    assert response.status_code == 200


@pytest.mark.django_db
def test_question_create_post(node):
    test_client = TestClient(router)
    # Using POST with form data (Ninja automatically parses dict into Form)
    response = test_client.post(
        f"/node/{node.pk}/question",
        data={"title": "New Test Question", "answer": "123"},
    )
    assert response.status_code == 200
    assert Node.objects.filter(type='question', title="New Test Question").exists()
    assert "New Test Question" in response.content.decode()


@pytest.mark.django_db
def test_question_edit_get(question):
    test_client = TestClient(router)
    response = test_client.get(f"/question/{question.pk}/edit")
    assert response.status_code == 200
    assert "form hx-post" in response.content.decode()
    assert question.title in response.content.decode()


@pytest.mark.django_db
def test_question_cancel_edit(question):
    test_client = TestClient(router)
    response = test_client.get(f"/question/{question.pk}/cancel_edit")
    assert response.status_code == 200
    assert "hx-get=" in response.content.decode()
    assert question.title in response.content.decode()


@pytest.mark.django_db
def test_question_update(question):
    test_client = TestClient(router)
    response = test_client.post(
        f"/question/{question.pk}",
        data={"title": "Updated Question Title", "answer": "Updated Answer"},
    )
    assert response.status_code == 200
    question.refresh_from_db()
    assert question.title == "Updated Question Title"
    assert question.answer == "Updated Answer"
    assert "Updated Question Title" in response.content.decode()


@pytest.mark.django_db
def test_question_delete(question):
    test_client = TestClient(router)
    response = test_client.delete(f"/question/{question.pk}")
    assert response.status_code == 200
    question.refresh_from_db()
    assert question.is_deleted is True


@pytest.mark.django_db
def test_node_creation_chroma_integration(client, project):
    test_title = "Chroma Node Title"
    test_content = "Chroma Node Content"

    response = client.post(
        reverse("project_detail", kwargs={"pk": project.pk}),
        {"title": test_title, "content": test_content},
    )
    assert response.status_code == 302

    node = Node.objects.filter(title=test_title).first()
    assert node is not None

    # Fetch from Chroma manually to ensure created during POST
    result = collection.get(ids=[f"node_{node.id}"])

    assert result is not None
    assert len(result["ids"]) == 1
    assert result["metadatas"][0]["type"] == "node"
    assert result["metadatas"][0]["node_id"] == node.id
    assert result["documents"][0] == f"{test_title}\n\n{test_content}"


@pytest.mark.django_db
def test_question_creation_chroma_integration(node):
    test_client = TestClient(router)
    test_title = "Chroma Question Title"
    test_answer = "Chroma Question Answer"

    # Ninja TestClient uses data kwarg for form submissions
    response = test_client.post(
        f"/node/{node.pk}/question",
        data={"title": test_title, "answer": test_answer},
    )
    assert response.status_code == 200

    question = Node.objects.filter(type='question', title=test_title).first()
    assert question is not None

    # Fetch from Chroma
    result = collection.get(ids=[f"question_{question.id}"])

    assert result is not None
    assert len(result["ids"]) == 1
    assert result["metadatas"][0]["type"] == "question"
    assert result["metadatas"][0]["question_id"] == question.id
    assert result["documents"][0] == f"{test_title}\n\n{test_answer}"


@pytest.mark.django_db
def test_node_detail_view(client, node):
    response = client.get(reverse("node_detail", kwargs={"pk": node.pk}))
    assert response.status_code == 302
    assert (
        response.url
        == reverse("project_detail", args=[node.project.pk]) + f"#node-{node.pk}"
    )


@pytest.mark.django_db
def test_question_detail_view(client, question):
    response = client.get(reverse("question_detail", kwargs={"pk": question.pk}))
    assert response.status_code == 302
    assert (
        response.url
        == reverse("project_detail", args=[question.source_node.project.pk])
        + f"#question-{question.pk}"
    )


@pytest.mark.django_db
def test_project_edit_get(project):
    test_client = TestClient(router)
    response = test_client.get(f"/project/{project.pk}/edit")
    assert response.status_code == 200
    assert 'class="card"' in response.content.decode()
    assert project.name in response.content.decode()


@pytest.mark.django_db
def test_project_cancel_edit(project):
    test_client = TestClient(router)
    response = test_client.get(f"/project/{project.pk}/cancel_edit")
    assert response.status_code == 200
    assert "hx-get=" in response.content.decode()
    assert project.name in response.content.decode()


@pytest.mark.django_db
def test_project_update(project):
    test_client = TestClient(router)
    response = test_client.post(
        f"/project/{project.pk}",
        data={"name": "Renamed Project Title"},
    )
    assert response.status_code == 200
    project.refresh_from_db()
    assert project.name == "Renamed Project Title"
    assert "Renamed Project Title" in response.content.decode()


@pytest.mark.django_db
def test_search_api(node, question):
    test_client = TestClient(router)
    # Test empty query
    response_empty = test_client.get("/search/?q=")
    assert response_empty.status_code == 200
    assert "No results found." in response_empty.content.decode()

    # Test with query
    response = test_client.get("/search/?q=Test")
    assert response.status_code == 200
    # Depending on chroma sync, it might or might not have results instantly, but we at least check it doesn't 500
    # We can check that the response is valid HTML
    assert "div" in response.content.decode()


@pytest.mark.django_db
def test_project_graph_api(project, node, question):
    # Add a linked node
    second_node = baker.make(Node, title="Second Node", project=project)
    node.linked_nodes.add(second_node)

    # Add a nested question
    nested_question = baker.make(Node, type='question', title="Nested Question", source_node=question, project=question.project)

    test_client = TestClient(router)
    response = test_client.get(f"/project/{project.pk}/graph")

    assert response.status_code == 200
    data = response.json()

    assert "nodes" in data
    assert "edges" in data

    nodes = data["nodes"]
    edges = data["edges"]

    assert len(nodes) == 4  # node, second_node, question, nested_question

    node_ids = [n["id"] for n in nodes]
    assert f"node_{node.pk}" in node_ids
    assert f"node_{second_node.pk}" in node_ids
    assert f"question_{question.pk}" in node_ids
    assert f"question_{nested_question.pk}" in node_ids

    assert len(edges) >= 3


@pytest.mark.django_db
def test_node_content_link_parsing(project):
    node1 = baker.make(Node, title="Node 1", project=project)
    baker.make(Node, title="Node 2", project=project)

    # Update node1 with a link to node 2
    node1.content = "Check out [Node 2](/node/2/)"
    node1.save()

    # Should have 1 linked node
    assert node1.linked_nodes.count() == 1
    assert node1.linked_nodes.first().id == 2

    # Update node1, remove the link
    node1.content = "No links here."
    node1.save()

    # Should have 0 linked nodes
    assert node1.linked_nodes.count() == 0


# ── ChromaDB Browser endpoint tests ─────────────────────────────────────────


@pytest.fixture
def chroma_test_collection():
    """Create a temporary ChromaDB collection seeded with one document, then clean up."""
    client = get_chroma_client()
    col_name = "test_browser_col"
    col = client.get_or_create_collection(col_name)
    col.add(ids=["doc_1"], documents=["Hello world"], metadatas=[{"type": "test"}])
    yield col_name
    try:
        client.delete_collection(col_name)
    except Exception:
        pass


def test_chroma_list_collections(chroma_test_collection):
    test_client = TestClient(router)
    response = test_client.get("/chroma/collections/")
    assert response.status_code == 200
    assert chroma_test_collection in response.content.decode()


def test_chroma_list_documents(chroma_test_collection):
    test_client = TestClient(router)
    response = test_client.get(
        f"/chroma/collections/{chroma_test_collection}/documents/"
    )
    assert response.status_code == 200
    body = response.content.decode()
    assert "doc_1" in body
    assert "Hello world" in body


def test_chroma_delete_documents(chroma_test_collection):
    test_client = TestClient(router)
    payload = json.dumps({"ids": ["doc_1"]}).encode()
    response = test_client.delete(
        f"/chroma/collections/{chroma_test_collection}/documents/",
        body=payload,
        content_type="application/json",
    )
    assert response.status_code == 200
    # The document should be gone — empty state shown
    client = get_chroma_client()
    col = client.get_collection(chroma_test_collection)
    assert col.count() == 0


def test_chroma_delete_collections(chroma_test_collection):
    test_client = TestClient(router)
    payload = json.dumps({"names": [chroma_test_collection]}).encode()
    response = test_client.delete(
        "/chroma/collections/",
        body=payload,
        content_type="application/json",
    )
    assert response.status_code == 200
    # Collection should no longer exist
    client = get_chroma_client()
    existing = [c.name for c in client.list_collections()]
    assert chroma_test_collection not in existing


# ── Text-anchored question (source_text) tests ──────────────────────────────


@pytest.mark.django_db
def test_question_source_text_default(node: Node) -> None:
    """Question.source_text defaults to empty string."""
    q = Node.objects.create(type='question', title="Test Q Default", source_node=node, project=node.project)
    assert q.source_text == ""


@pytest.mark.django_db
def test_create_question_service_with_source_text(node: Node) -> None:
    """services.create_question persists source_text correctly."""
    from core import services

    q = services.create_question(
        title="Anchored Question", content="Some answer", source_node=node,
        source_text="a specific block of text",, project=node,
        source_text="a specific block of text",.project)
    q.refresh_from_db()
    assert q.source_text == "a specific block of text"
    assert q.source_node == node


@pytest.mark.django_db
def test_create_question_api_with_source_text(node: Node) -> None:
    """POST /node/{pk}/question with source_text stores the field."""
    test_client = TestClient(router)
    response = test_client.post(
        f"/node/{node.pk}/question",
        data={
            "title": "Selection Question",
            "answer": "Answer here",
            "source_text": "some selected text",
        },
    )
    assert response.status_code == 200
    q = Node.objects.filter(type='question', title="Selection Question").first()
    assert q is not None
    assert q.source_text == "some selected text"
    assert q.source_node == node


@pytest.mark.django_db
def test_create_question_api_without_source_text(node: Node) -> None:
    """POST /node/{pk}/question without source_text stores empty string."""
    test_client = TestClient(router)
    response = test_client.post(
        f"/node/{node.pk}/question",
        data={"title": "Plain Question", "answer": ""},
    )
    assert response.status_code == 200
    q = Node.objects.filter(type='question', title="Plain Question").first()
    assert q is not None
    assert q.source_text == ""


@pytest.mark.django_db
def test_question_detail_endpoint(question: Node) -> None:
    """GET /question/{pk}/detail returns HTML with the question title and answer."""
    test_client = TestClient(router)
    response = test_client.get(f"/question/{question.pk}/detail")
    assert response.status_code == 200
    body = response.content.decode()
    assert question.title in body
    assert question.answer in body


@pytest.mark.django_db
def test_question_detail_endpoint_shows_source_text(node: Node) -> None:
    """GET /question/{pk}/detail shows source_text when present."""
    q = baker.make(Node, type='question', title="Fox Question", content="Yes it is", source_node=node,
        source_text="The quick brown fox",, project=node,
        source_text="The quick brown fox",.project)
    test_client = TestClient(router)
    response = test_client.get(f"/question/{q.pk}/detail")
    assert response.status_code == 200
    body = response.content.decode()
    assert "The quick brown fox" in body
    assert "Fox Question" in body
