from ninja import NinjaAPI, Router, Schema
from typing import List
from django.db.models import Q
from .models import Node, Question

api = NinjaAPI()
router = Router()

class SearchResult(Schema):
    id: int
    title: str
    type: str

@router.get("/autocomplete", response=List[SearchResult])
def autocomplete(request, q: str = ""):
    if not q:
        return []
    
    words = q.split()
    
    node_query = Q(is_deleted=False)
    question_query = Q(is_deleted=False)
    
    for word in words:
        node_query &= Q(title__icontains=word)
        question_query &= Q(title__icontains=word)
        
    nodes = Node.objects.filter(node_query)[:10]
    questions = Question.objects.filter(question_query)[:10]
    
    results = []
    for n in nodes:
        results.append(SearchResult(id=n.id, title=n.title, type="node"))
    for qu in questions:
        results.append(SearchResult(id=qu.id, title=qu.title, type="question"))
        
    # Sort and limit
    results.sort(key=lambda x: x.title.lower())
    return results[:10]

api.add_router("", router)
