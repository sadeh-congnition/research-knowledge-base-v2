import pytest
from core.models import Project, Node, Question
from core.services import create_question, create_node

@pytest.mark.django_db
def test_cross_project_links_tracking():
    # Create two projects
    p1 = Project.objects.create(name="Project A")
    p2 = Project.objects.create(name="Project B")

    # Create Node A in Project A
    # No linking first.
    node_a = create_node(p1, "Node A", "Content A")

    # Create Node B in Project B which links to Node A 
    # and also links to a future Question B (which we'll add after)
    node_b = create_node(p2, "Node B", f"Content linking to Node A: [Node A](/project/{p1.pk}/#node-{node_a.pk}) and question [Q B](/api/question/999/detail)")

    # For node_b's question link to work, we'd need the real ID, let's create a question first.
    q_b = create_question("Question B", f"What about [Node A](/project/{p1.pk}/#node-{node_a.pk})?", source_node=node_b)
    
    # Re-save node_b with valid Q ID
    node_b.content = f"Content linking to Node A: [Node A](/project/{p1.pk}/#node-{node_a.pk}) and question [Q B](/api/question/{q_b.pk}/detail)"
    node_b.save()

    # Now verify relationships
    node_a.refresh_from_db()
    node_b.refresh_from_db()
    q_b.refresh_from_db()

    # Node B outlinks: 1 node (Node A), 1 question (Q B)
    assert node_a in node_b.outgoing_node_links.all()
    assert q_b in node_b.outgoing_question_links.all()

    # Node A inlinks from Node B
    assert node_b in node_a.incoming_node_links.all()
    
    # Node A inlinks from Question B (via question answer content)
    assert q_b in node_a.incoming_question_links.all()

    # Question B outlinks to Node A
    assert node_a in q_b.linked_nodes.all()
    
    # Question B linked_from should be Node B
    assert q_b.linked_from == node_b
    assert q_b.project == p2

    # Check question-to-question links
    q_a = create_question("Question A", f"Answer relies on [Q B](/api/question/{q_b.pk}/detail)", source_node=node_a)
    q_a.refresh_from_db()
    
    assert q_b in q_a.linked_questions.all()
    assert q_a in q_b.incoming_question_links_via_content.all()
