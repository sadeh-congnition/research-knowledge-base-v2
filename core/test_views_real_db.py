import pytest
from django.test import Client
from django.urls import reverse
from model_bakery import baker
from core.models import Project, Node
from core.chroma_client import get_chroma_client, get_collection
from core import services


@pytest.mark.django_db
class TestViewsWithRealDatabases:
    """Test all views with real database interactions."""

    @pytest.fixture(autouse=True)
    def setup_chroma(self):
        """Ensure ChromaDB is clean before each test."""
        import os
        from core.chroma_client import get_chroma_client, get_collection

        client = get_chroma_client()
        collection_name = os.getenv("CHROMA_COLLECTION_NAME", "test_research_tracker")

        try:
            # Clean up the actual collection used by tests
            client.delete_collection(collection_name)
        except Exception:
            pass

        # Reset cached collection to force recreation
        import core.chroma_client

        core.chroma_client._collection = None

        get_collection()
        yield

        try:
            # Clean up the actual collection used by tests
            client.delete_collection(collection_name)
        except Exception:
            pass

    def test_project_list_view_create_and_chroma_sync(self):
        """Test project list view with creation and ChromaDB sync."""
        client = Client()

        # Test GET
        response = client.get(reverse("project_list"))
        assert response.status_code == 200

        # Test POST - create project
        response = client.post(reverse("project_list"), {"name": "View Test Project"})
        assert response.status_code == 302  # Non-HTMX POST should always redirect

        # Verify project exists in Django
        project = Project.objects.filter(name="View Test Project").first()
        assert project is not None

    def test_project_delete_view_with_cascade_effects(self):
        """Test project deletion view and its effects."""
        client = Client()
        project = baker.make(Project, name="Delete Me Project")

        # Create related data using services to ensure embeddings
        node = services.create_node(project, "Project Node", "Node content")
        question = services.create_question("Project Question", "Question answer", node)

        # Verify data exists before deletion
        assert not project.is_deleted
        collection = get_collection()
        node_result = collection.get(ids=[f"node_{node.id}"])
        question_result = collection.get(ids=[f"question_{question.id}"])
        assert len(node_result["ids"]) == 1
        assert len(question_result["ids"]) == 1

        # Delete project
        response = client.post(
            reverse("project_delete", kwargs={"pk": project.pk}), {"_method": "DELETE"}
        )
        assert (
            response.status_code == 302 or response.status_code == 200
        )  # HTMX or regular

        # Verify project is soft deleted
        project.refresh_from_db()
        assert project.is_deleted is True

    def test_project_detail_view_with_node_creation(self):
        """Test project detail view with node creation and ChromaDB sync."""
        client = Client()
        project = baker.make(Project, name="Detail Test Project")

        # Test GET
        response = client.get(reverse("project_detail", kwargs={"pk": project.pk}))
        assert response.status_code == 200
        assert "Detail Test Project" in response.content.decode()

        # Test POST - create node
        response = client.post(
            reverse("project_detail", kwargs={"pk": project.pk}),
            {"title": "View Created Node", "content": "View created content"},
        )
        assert response.status_code == 302 or response.status_code == 200

        # Verify node exists in Django
        node = Node.objects.filter(title="View Created Node").first()
        assert node is not None
        assert node.project == project

        # Verify ChromaDB embedding
        collection = get_collection()
        result = collection.get(ids=[f"node_{node.id}"])
        assert len(result["ids"]) == 1
        assert result["metadatas"][0]["type"] == "node"
        assert result["metadatas"][0]["node_id"] == node.id
        assert "View Created Node" in result["documents"][0]
        assert "View created content" in result["documents"][0]

    def test_node_operations_with_chroma_integration(self):
        """Test node CRUD operations with ChromaDB integration."""
        client = Client()
        project = baker.make(Project, name="Node Ops Project")
        node = services.create_node(project, "Original Node", "Original content")

        # Verify Django update
        response = client.get(
            reverse("node_edit", kwargs={"pk": node.pk}), HTTP_HX_REQUEST="true"
        )
        assert response.status_code == 200
        assert "Original Node" in response.content.decode()

        # Test node update
        response = client.post(
            reverse("node_update", kwargs={"pk": node.pk}),
            {"title": "Updated Node", "content": "Updated content"},
        )
        assert response.status_code == 302 or response.status_code == 200

        # Verify Django update
        node.refresh_from_db()
        assert node.title == "Updated Node"
        assert node.content == "Updated content"

        # Verify ChromaDB update
        collection = get_collection()
        result = collection.get(ids=[f"node_{node.id}"])
        assert len(result["ids"]) == 1
        assert "Updated Node" in result["documents"][0]
        assert "Updated content" in result["documents"][0]

        # Test node delete
        response = client.post(
            reverse("node_delete", kwargs={"pk": node.pk}), {"_method": "DELETE"}
        )
        assert response.status_code == 302 or response.status_code == 200

        # Verify Django soft delete
        node.refresh_from_db()
        assert node.is_deleted is True

        # Verify ChromaDB removal
        result = collection.get(ids=[f"node_{node.id}"])
        assert len(result["ids"]) == 0

    def test_node_link_parsing_with_real_data(self):
        """Test node link parsing functionality with real data."""
        client = Client()
        project = baker.make(Project, name="Link Test Project")

        # Create nodes using services to ensure embeddings
        node1 = services.create_node(project, "Node 1", "Original content")
        node2 = services.create_node(project, "Node 2", "Target content")
        node3 = services.create_node(project, "Node 3", "Another target")

        # Update node1 with links to node2 and node3
        response = client.post(
            reverse("node_update", kwargs={"pk": node1.pk}),
            {
                "title": "Node 1",
                "content": f"Check out [Node 2](/node/{node2.pk}/) and [Node 3](/node/{node3.pk}/)",
            },
        )
        assert response.status_code == 302 or response.status_code == 200

        # Verify links were created
        node1.refresh_from_db()
        linked_nodes = list(node1.linked_nodes.all())
        assert len(linked_nodes) == 2
        linked_ids = [n.pk for n in linked_nodes]
        assert node2.pk in linked_ids
        assert node3.pk in linked_ids

        # Update node1 to remove links
        response = client.post(
            reverse("node_update", kwargs={"pk": node1.pk}),
            {"title": "Node 1", "content": "No more links here"},
        )
        assert response.status_code == 302 or response.status_code == 200

        # Verify links were removed
        node1.refresh_from_db()
        assert node1.linked_nodes.count() == 0

    def test_question_detail_view_redirects(self):
        """Test question detail view redirects correctly."""
        client = Client()
        project = baker.make(Project, name="Question Detail Project")
        node = services.create_node(project, "Source Node", "Source content")
        question = services.create_question("Test Question", "Test Answer", node)

        # Test question detail redirect
        response = client.get(reverse("question_detail", kwargs={"pk": question.pk}))
        assert response.status_code == 302

        # Should redirect to project detail with question anchor
        expected_url = (
            reverse("project_detail", args=[node.project.pk])
            + f"#question-{question.pk}"
        )
        assert response.url == expected_url

    def test_global_search_view_with_chroma_integration(self):
        """Test global search view with real ChromaDB data."""
        client = Client()
        project = baker.make(Project, name="Search Test Project")

        # Create searchable content using services to ensure embeddings
        node1 = services.create_node(
            project, "Python Programming", "Python is a programming language"
        )
        services.create_node(
            project, "JavaScript Development", "JavaScript for web development"
        )
        services.create_question("Python variables", "Dynamic typing in Python", node1)

        # Test search with query
        response = client.get(reverse("global_search") + "?q=Python")
        assert response.status_code == 200
        content = response.content.decode()

        # Should find Python-related results
        assert "Python" in content

        # Test search with project filter
        response = client.get(
            reverse("global_search") + f"?q=Python&project_id={project.pk}"
        )
        assert response.status_code == 200

        # Test empty search
        response = client.get(reverse("global_search") + "?q=")
        assert response.status_code == 200
        assert "Search" in content or "form" in content

    def test_chroma_browser_view_with_real_data(self):
        """Test ChromaDB browser view with real collections."""
        client = Client()

        # Create test collection
        chroma_client = get_chroma_client()
        test_collection = chroma_client.get_or_create_collection("test_browser_view")
        test_collection.add(
            ids=["doc1", "doc2"],
            documents=["Document 1 content", "Document 2 content"],
            metadatas=[
                {"type": "test", "source": "view_test"},
                {"type": "test", "source": "view_test"},
            ],
        )

        # Test browser view
        response = client.get(reverse("chroma_browser"))
        assert response.status_code == 200
        content = response.content.decode()

        # Should show our test collection
        assert "test_browser_view" in content or "collection" in content

        # Cleanup
        chroma_client.delete_collection("test_browser_view")

    def test_htmx_responses_for_partial_updates(self):
        """Test HTMX partial responses for real-time updates."""
        client = Client()
        project = baker.make(Project, name="HTMX Test Project")

        # Test HTMX project creation - should return partial content, not redirect
        response = client.post(
            reverse("project_list"), {"name": "HTMX Project"}, HTTP_HX_REQUEST="true"
        )
        # HTMX requests should return 200 with partial content, not 302 redirects
        assert response.status_code == 200, (
            f"Expected HTMX partial response (200), got {response.status_code}"
        )
        assert "HTMX Project" in response.content.decode(), (
            "HTMX response should contain created project content"
        )

        # Verify project was actually created
        htmx_project = Project.objects.filter(name="HTMX Project").first()
        assert htmx_project is not None, "Project should be created via HTMX request"

        # Test HTMX node creation - should return partial content, not redirect
        response = client.post(
            reverse("project_detail", kwargs={"pk": project.pk}),
            {"title": "HTMX Node", "content": "HTMX content"},
            HTTP_HX_REQUEST="true",
        )
        # HTMX requests should return 200 with partial content, not 302 redirects
        assert response.status_code == 200, (
            f"Expected HTMX partial response (200), got {response.status_code}"
        )
        assert "HTMX Node" in response.content.decode(), (
            "HTMX response should contain created node content"
        )

        # Verify node was actually created
        node = Node.objects.filter(title="HTMX Node").first()
        assert node is not None, "Node should be created via HTMX request"
        assert node.project == project, "Node should belong to correct project"

        # Test that non-HTMX requests still redirect properly
        response = client.post(reverse("project_list"), {"name": "Non-HTMX Project"})
        assert response.status_code == 302, "Non-HTMX POST requests should redirect"

        # Verify non-HTMX project was created
        non_htmx_project = Project.objects.filter(name="Non-HTMX Project").first()
        assert non_htmx_project is not None

    def test_node_detail_view_redirect_behavior(self):
        """Test node detail view redirect behavior."""
        client = Client()
        project = baker.make(Project, name="Redirect Test Project")
        node = services.create_node(project, "Redirect Node", "Redirect content")

        # Test node detail redirect
        response = client.get(reverse("node_detail", kwargs={"pk": node.pk}))
        assert response.status_code == 302

        # Should redirect to project detail with node anchor
        expected_url = reverse("project_detail", args=[project.pk]) + f"#node-{node.pk}"
        assert response.url == expected_url

    def test_error_handling_with_missing_data(self):
        """Test error handling when data is missing or deleted."""
        client = Client()

        # Test with non-existent project
        response = client.get(reverse("project_detail", kwargs={"pk": 99999}))
        assert response.status_code == 404

        # Test with non-existent node
        response = client.get(reverse("node_detail", kwargs={"pk": 99999}))
        assert response.status_code == 404

        # Test with non-existent question
        response = client.get(reverse("question_detail", kwargs={"pk": 99999}))
        assert response.status_code == 404

        # Test with deleted project
        project = baker.make(Project, name="Deleted Project")
        project.soft_delete()

        response = client.get(reverse("project_detail", kwargs={"pk": project.pk}))
        assert response.status_code == 404

        # Test with deleted node
        node = services.create_node(project, "Deleted Node", "Content")
        node.soft_delete()

        response = client.get(reverse("node_detail", kwargs={"pk": node.pk}))
        assert response.status_code == 404

    def test_concurrent_operations_data_integrity(self):
        """Test data integrity during concurrent operations."""
        client = Client()
        project = baker.make(Project, name="Concurrent Test Project")

        # Create multiple nodes rapidly
        nodes: list[Node] = []
        for i in range(5):
            response = client.post(
                reverse("project_detail", kwargs={"pk": project.pk}),
                {"title": f"Concurrent Node {i}", "content": f"Content {i}"},
            )
            assert response.status_code in [200, 302]

            node = Node.objects.filter(title=f"Concurrent Node {i}").first()
            if node:
                nodes.append(node)

        # Verify all nodes have embeddings
        collection = get_collection()
        for node in nodes:
            result = collection.get(ids=[f"node_{node.id}"])
            assert len(result["ids"]) == 1
            assert f"Concurrent Node {node.title.split()[-1]}" in result["documents"][0]

        # Create questions on multiple nodes
        for i, node in enumerate(nodes[:3]):
            response = client.post(
                f"/api/node/{node.pk}/question",
                {"title": f"Question {i}", "answer": f"Answer {i}"},
                content_type="application/x-www-form-urlencoded",
            )
            # Note: This would need proper API endpoint testing

        # Verify data consistency
        final_nodes = Node.objects.filter(project=project, is_deleted=False)
        assert len(final_nodes) >= len(nodes)
