import pytest
from ninja.testing import TestClient
from model_bakery import baker
from core.models import Project, Node, Question
from core.api import router
from core import services

@pytest.mark.django_db
class TestCrossProjectGraph:
    def test_project_graph_includes_external_links(self):
        # Setup: Project A and Project B
        project_a = baker.make(Project, name="Project A")
        project_b = baker.make(Project, name="Project B")
        
        # Node A in Project A
        node_a = services.create_node(project_a, "Node A", "Content A")
        # Node B in Project B
        node_b = services.create_node(project_b, "Node B", "Content B")
        
        # Link Node A -> Node B
        node_a.content = f"Link to [Node B](/node/{node_b.pk}/)"
        node_a.save()
        
        # Question on Node B
        q_b = services.create_question("Question B", "Answer B", node_b)
        
        test_client = TestClient(router)
        
        # 1. Test Graph for Project A
        response = test_client.get(f"/project/{project_a.pk}/graph")
        assert response.status_code == 200
        data = response.json()
        
        node_ids = [n["id"] for n in data["nodes"]]
        assert f"node_{node_a.pk}" in node_ids
        assert f"node_{node_b.pk}" in node_ids
        assert f"question_{q_b.pk}" in node_ids
        
        # Verify Node B label includes project name
        node_b_data = next(n for n in data["nodes"] if n["id"] == f"node_{node_b.pk}")
        assert "Project B" in node_b_data["label"]
        
        # Verify edge exists
        edge_exists = any(
            e["source"] == f"node_{node_a.pk}" and e["target"] == f"node_{node_b.pk}"
            for e in data["edges"]
        )
        assert edge_exists
        
        # Verify edge to question
        q_edge_exists = any(
            e["source"] == f"node_{node_b.pk}" and e["target"] == f"question_{q_b.pk}"
            for e in data["edges"]
        )
        assert q_edge_exists

    def test_project_graph_includes_incoming_external_links(self):
        # Setup: Project A and Project B
        project_a = baker.make(Project, name="Project A")
        project_b = baker.make(Project, name="Project B")
        
        # Node A in Project A
        node_a = services.create_node(project_a, "Node A", "Content A")
        # Node B in Project B
        node_b = services.create_node(project_b, "Node B", "Content B")
        
        # Link Node B -> Node A (Incoming to A)
        node_b.content = f"Link to [Node A](/node/{node_a.pk}/)"
        node_b.save()
        
        test_client = TestClient(router)
        
        # 1. Test Graph for Project A
        response = test_client.get(f"/project/{project_a.pk}/graph")
        assert response.status_code == 200
        data = response.json()
        
        node_ids = [n["id"] for n in data["nodes"]]
        assert f"node_{node_a.pk}" in node_ids
        assert f"node_{node_b.pk}" in node_ids
        
        # Verify edge exists B -> A
        edge_exists = any(
            e["source"] == f"node_{node_b.pk}" and e["target"] == f"node_{node_a.pk}"
            for e in data["edges"]
        )
        assert edge_exists
