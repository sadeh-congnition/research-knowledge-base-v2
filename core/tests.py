import pytest
from core.models import Project, Node, Question
from model_bakery import baker
from django.urls import reverse
from ninja.testing import TestClient
from core.api import router
from core.chroma_client import collection


@pytest.fixture
def project(db):
    return baker.make(Project, name="Test Project")


@pytest.fixture
def node(db, project):
    return baker.make(Node, title="Test Node", content="Node Content", project=project)


@pytest.fixture
def question(db, node):
    return baker.make(
        Question,
        title="Test Question",
        answer="Question Answer",
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
    assert Question.objects.filter(title="New Test Question").exists()
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

    question = Question.objects.filter(title=test_title).first()
    assert question is not None

    # Fetch from Chroma
    result = collection.get(ids=[f"question_{question.id}"])

    assert result is not None
    assert len(result["ids"]) == 1
    assert result["metadatas"][0]["type"] == "question"
    assert result["metadatas"][0]["question_id"] == question.id
    assert result["documents"][0] == f"{test_title}\n\n{test_answer}"
