import pytest
from django.test import Client
from django.urls import reverse
from model_bakery import baker
from core.models import Project, Node, Question
from core import services

@pytest.mark.django_db
def test_node_link_properties():
    project = baker.make(Project)
    node1 = services.create_node(project, "Node 1", "Content 1")
    node2 = services.create_node(project, "Node 2", f"Link to [Node 1](/node/{node1.pk}/)")
    
    # Refresh to trigger update_links_from_content
    node2.refresh_from_db()
    
    # Test outgoing links
    assert node2.outgoing_node_links.count() == 1
    assert node1 in node2.outgoing_node_links.all()
    
    # Test incoming links
    assert node1.incoming_node_links.count() == 1
    assert node2 in node1.incoming_node_links.all()

@pytest.mark.django_db
def test_question_link_properties():
    project = baker.make(Project)
    node = services.create_node(project, "Node", "Content")
    q1 = services.create_question("Q1", "A1", node)
    
    # Create nested question
    q2 = Question.objects.create(title="Q2", answer="A2", source_question=q1)
    
    assert q2.linked_from == q1
    assert q2 in q1.linked_to.all()

@pytest.mark.django_db
def test_link_rendering_in_node_list(client):
    project = baker.make(Project)
    node1 = services.create_node(project, "Source Node", "Content 1")
    node2 = services.create_node(project, "Target Node", f"Check [Source Node](/node/{node1.pk}/)")
    
    response = client.get(reverse('project_detail', args=[project.pk]))
    content = response.content.decode()
    
    # Check if "References" section exists
    assert "References" in content
    assert "Linked from:" in content
    assert "Links to:" in content
    assert "Source Node" in content
    assert "Target Node" in content

@pytest.mark.django_db
def test_question_overlay_links(client):
    project = baker.make(Project)
    node = services.create_node(project, "Node", "Content")
    q1 = services.create_question("Parent Q", "A1", node)
    q2 = Question.objects.create(title="Child Q", answer="A2", source_question=q1)
    
    # Get question detail partial for q2
    response = client.get(f"/api/question/{q2.pk}/detail", HTTP_HX_REQUEST="true")
    content = response.content.decode()
    
    assert "Parent Question:" in content
    assert "Parent Q" in content
    
    # Get question detail partial for q1
    q1.refresh_from_db()
    response = client.get(f"/api/question/{q1.pk}/detail", HTTP_HX_REQUEST="true")
    content = response.content.decode()
    assert "Follow-up" in content and "Questions:" in content
    assert "Child Q" in content
