import pytest
from django.test import Client
from django.urls import reverse
from model_bakery import baker
from core.models import Project, Node
from core import services

@pytest.mark.django_db
def test_graph_visibility():
    client = Client()
    
    # Create Project 1 and Project 2
    p1 = baker.make(Project, name="Global Project 1")
    p2 = baker.make(Project, name="Global Project 2")
    
    # Create Node A in P1
    node_a = services.create_node(p1, "Node A", "Content A")
    
    # Create Node B in P2
    node_b = services.create_node(p2, "Node B", "Content B")
    
    # Create Node C in P2, linked from Node B
    node_c = services.create_node(p2, "Node C", f"Link to [Node B](/node/{node_b.pk}/)")
    
    # Link Node A to Node B (Cross-project link)
    node_a.content = f"Link to [Node B](/node/{node_b.pk}/)"
    node_a.save()
    
    # Link Node B to Node C (Internal to P2)
    node_b.content = f"Link to [Node C](/node/{node_c.pk}/)"
    node_b.save()
    
    # Verify links
    node_a.refresh_from_db()
    node_b.refresh_from_db()
    assert node_b in node_a.linked_nodes.all()
    assert node_c in node_b.linked_nodes.all()
    
    # Fetch graph for Project 1
    response = client.get(f"/api/project/{p1.pk}/graph")
    assert response.status_code == 200
    data = response.json()
    
    node_ids = [n["id"] for n in data["nodes"]]
    print(f"\nNodes in P1 graph: {node_ids}")
    
    # We expect Node A (P1) and Node B (P2, immediate neighbor)
    assert f"node_{node_a.pk}" in node_ids
    assert f"node_{node_b.pk}" in node_ids
    
    # Transitive link check
    if f"node_{node_c.pk}" in node_ids:
        print("PASS: Node C is present (transitive link works)")
    else:
        print("FAIL: Node C is MISSING (transitive link doesn't work)")

    # Unlinked node check
    node_d = services.create_node(p2, "Node D", "Unlinked Node")
    if f"node_{node_d.pk}" in node_ids:
        print("Note: Node D is present (unlinked cross-project node visible)")
    else:
        print("Note: Node D is MISSING (unlinked cross-project node NOT visible - expected behavior)")

@pytest.mark.django_db
def test_global_graph_data():
    client = Client()
    
    p1 = baker.make(Project, name="P1")
    p2 = baker.make(Project, name="P2")
    
    n1 = services.create_node(p1, "Node 1", "Content 1")
    n2 = services.create_node(p2, "Node 2", "Content 2")
    
    response = client.get("/api/graph")
    assert response.status_code == 200
    data = response.json()
    
    node_ids = [n["id"] for n in data["nodes"]]
    assert f"node_{n1.pk}" in node_ids
    assert f"node_{n2.pk}" in node_ids
    
    # Check labels include project names
    labels = [n["label"] for n in data["nodes"]]
    assert f"Node 1 [P1]" in labels
    assert f"Node 2 [P2]" in labels
    
    print("\nGlobal graph verified: nodes from both projects present with correct labels.")
