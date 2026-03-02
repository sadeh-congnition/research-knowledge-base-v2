import pytest
from core.models import Project, Node, Question
from model_bakery import baker
from django.urls import reverse
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
    return baker.make(Question, title="Test Question", answer="Question Answer", source_node=node)

@pytest.mark.django_db
def test_project_list_get(client, project):
    response = client.get(reverse('project_list'))
    assert response.status_code == 200
    assert "Test Project" in response.content.decode()

@pytest.mark.django_db
def test_project_create_post(client):
    response = client.post(reverse('project_list'), {'name': 'New Project'})
    assert response.status_code == 302
    assert Project.objects.filter(name='New Project').exists()

@pytest.mark.django_db
def test_project_delete(client, project):
    response = client.post(reverse('project_delete', kwargs={'pk': project.pk}), {'_method': 'DELETE'})
    assert response.status_code == 302
    project.refresh_from_db()
    assert project.is_deleted is True

@pytest.mark.django_db
def test_node_create_post(client, project):
    response = client.post(reverse('project_detail', kwargs={'pk': project.pk}), {'title': 'New Node', 'content': 'Content'})
    assert response.status_code == 302
    assert Node.objects.filter(title='New Node').exists()

@pytest.mark.django_db
def test_node_update(client, node):
    response = client.post(reverse('node_update', kwargs={'pk': node.pk}), {'title': 'Updated Node', 'content': 'Updated Content'})
    assert response.status_code == 302
    node.refresh_from_db()
    assert node.title == 'Updated Node'

@pytest.mark.django_db
def test_autocomplete_api(node, question):
    test_client = TestClient(router)
    response = test_client.get("/autocomplete?q=Test")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    titles = [item['title'] for item in data]
    assert "Test Node" in titles
    assert "Test Question" in titles

@pytest.mark.django_db
def test_global_search_view(client, node):
    response = client.get(reverse('global_search') + "?q=Test")
    assert response.status_code == 200
