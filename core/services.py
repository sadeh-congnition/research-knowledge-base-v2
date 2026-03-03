from typing import List, Dict, Any, Optional
from core.models import Project, Node, Question
from core.chroma_client import collection, get_chroma_client
from loguru import logger


def sync_all_to_chroma() -> None:
    """Sync all non-deleted nodes and questions to ChromaDB.

    Intended to be called once on application startup (in a background thread)
    to ensure ChromaDB stays in sync even after restarts or migrations that
    occurred while the server was down.
    """
    logger.info("ChromaDB startup sync: beginning sync of all nodes and questions")

    nodes = Node.objects.select_related("project").all()
    synced_nodes = 0
    for node in nodes:
        try:
            embed_node(node)
            synced_nodes += 1
        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"ChromaDB startup sync: failed to embed node {node.id}: {exc}"
            )

    questions = Question.objects.select_related("source_node__project").all()
    synced_questions = 0
    for question in questions:
        try:
            embed_question(question)
            synced_questions += 1
        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"ChromaDB startup sync: failed to embed question {question.id}: {exc}"
            )

    logger.info(
        f"ChromaDB startup sync: done — {synced_nodes} node(s), "
        f"{synced_questions} question(s) synced"
    )


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
    node = Node.objects.create(project=project, title=title, content=content)
    embed_node(node)
    return node


def update_node(node: Node, title: str, content: str) -> Node:
    """Update title and content of a node."""
    node.title = title
    node.content = content
    node.save()
    embed_node(node)
    return node


def delete_node(node: Node) -> None:
    """Soft delete a research node."""
    node.soft_delete()
    remove_node_embedding(node)


def embed_node(node: Node) -> None:
    """Embed a node in ChromaDB."""
    if node.is_deleted:
        remove_node_embedding(node)
        return

    try:
        text = f"{node.title}\n\n{node.content}"
        collection.upsert(
            documents=[text],
            metadatas=[
                {
                    "type": "node",
                    "project_id": node.project.id,
                    "node_id": node.id,
                }
            ],
            ids=[f"node_{node.id}"],
        )
        logger.info(f"Embedded node {node.id} in ChromaDB")
    except Exception as e:
        logger.error(f"Failed to embed node {node.id}: {e}")


def remove_node_embedding(node: Node) -> None:
    """Remove a node embedding from ChromaDB."""
    try:
        collection.delete(ids=[f"node_{node.id}"])
        logger.info(f"Removed node {node.id} embedding from ChromaDB")
    except Exception as e:
        logger.error(f"Failed to remove node {node.id} embedding: {e}")


def embed_question(question: Question) -> None:
    """Embed a question in ChromaDB."""
    if question.is_deleted:
        remove_question_embedding(question)
        return

    try:
        project_id = question.source_node.project.id if question.source_node else 0
        text = f"{question.title}\n\n{question.answer}"
        collection.upsert(
            documents=[text],
            metadatas=[
                {
                    "type": "question",
                    "project_id": project_id,
                    "question_id": question.id,
                }
            ],
            ids=[f"question_{question.id}"],
        )
        logger.info(f"Embedded question {question.id} in ChromaDB")
    except Exception as e:
        logger.error(f"Failed to embed question {question.id}: {e}")


def remove_question_embedding(question: Question) -> None:
    """Remove a question embedding from ChromaDB."""
    try:
        collection.delete(ids=[f"question_{question.id}"])
        logger.info(f"Removed question {question.id} embedding from ChromaDB")
    except Exception as e:
        logger.error(f"Failed to remove question {question.id} embedding: {e}")


def create_question(
    title: str, answer: str, source_node: Node, source_text: str = ""
) -> Question:
    """Create a new question, optionally anchored to a block of text in the source node."""
    question = Question.objects.create(
        title=title, answer=answer, source_node=source_node, source_text=source_text
    )
    embed_question(question)
    return question


def update_question(
    question: Question,
    title: str,
    answer: str,
    source_text: Optional[str] = None,
) -> Question:
    """Update a question. source_text is only updated when explicitly passed."""
    question.title = title
    question.answer = answer
    if source_text is not None:
        question.source_text = source_text
    question.save()
    embed_question(question)
    return question


def delete_question(question: Question) -> None:
    """Soft delete a question."""
    question.soft_delete()
    remove_question_embedding(question)


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
