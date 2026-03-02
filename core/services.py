from typing import List, Dict, Any, Optional
from core.models import Project, Node
from core.chroma_client import collection, get_chroma_client


def create_project(name: str) -> Project:
    """Create a new research project."""
    return Project.objects.create(name=name)


def delete_project(project: Project) -> None:
    """Soft delete a research project."""
    project.soft_delete()


def update_project(project: Project, name: str) -> Project:
    """Update name of a project."""
    project.name = name
    project.save()
    return project


def create_node(project: Project, title: str, content: str) -> Node:
    """Create a new research node in a project."""
    return Node.objects.create(project=project, title=title, content=content)


def update_node(node: Node, title: str, content: str) -> Node:
    """Update title and content of a node."""
    node.title = title
    node.content = content
    node.save()
    return node


def delete_node(node: Node) -> None:
    """Soft delete a research node."""
    node.soft_delete()


def perform_vector_search(
    query: str, project_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Perform a semantic vector search across projects."""
    where = {}
    if project_id:
        where["project_id"] = project_id

    try:
        search_results = collection.query(
            query_texts=[query], n_results=10, where=where if where else None
        )

        results = []
        if (
            search_results
            and search_results.get("metadatas")
            and len(search_results["metadatas"]) > 0
        ):
            for idx, meta in enumerate(search_results["metadatas"][0]):
                doc_texts = search_results.get("documents")
                if doc_texts and doc_texts[0] and len(doc_texts[0]) > idx:
                    doc = doc_texts[0][idx]
                    results.append(
                        {
                            "title": doc.split("\n\n")[0]
                            if "\n\n" in doc
                            else "Untitled",
                            "snippet": doc[:150] + "...",
                            "type": meta.get("type"),
                            "node_id": meta.get("node_id"),
                            "question_id": meta.get("question_id"),
                            "project_id": meta.get("project_id"),
                        }
                    )
        return results
    except Exception:
        return []


def list_chroma_collections() -> List[Dict[str, Any]]:
    """Return a list of all ChromaDB collections with their document counts."""
    client = get_chroma_client()
    collections = client.list_collections()
    result = []
    for col in collections:
        c = client.get_collection(col.name)
        result.append({"name": col.name, "count": c.count()})
    return result


def list_chroma_documents(collection_name: str) -> List[Dict[str, Any]]:
    """Return all documents in the named ChromaDB collection."""
    client = get_chroma_client()
    col = client.get_collection(collection_name)
    data = col.get()
    result = []
    ids: List[str] = data.get("ids") or []
    documents: List[Optional[str]] = data.get("documents") or []
    metadatas: List[Optional[Dict[str, Any]]] = data.get("metadatas") or []
    for i, doc_id in enumerate(ids):
        doc_text = documents[i] if i < len(documents) else ""
        meta = metadatas[i] if i < len(metadatas) else {}
        result.append(
            {
                "id": doc_id,
                "document": doc_text or "",
                "metadata": meta or {},
            }
        )
    return result


def delete_chroma_collections(names: List[str]) -> None:
    """Delete the named ChromaDB collections."""
    client = get_chroma_client()
    for name in names:
        client.delete_collection(name)


def delete_chroma_documents(collection_name: str, ids: List[str]) -> None:
    """Delete documents by ID from the named ChromaDB collection."""
    client = get_chroma_client()
    col = client.get_collection(collection_name)
    col.delete(ids=ids)
