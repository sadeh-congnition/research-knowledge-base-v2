from ninja import NinjaAPI, Router, Schema, Form
from typing import List
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
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

@router.post("/node/{node_pk}/question")
def create_question(request, node_pk: int, title: str = Form(""), answer: str = Form("")):
    node = get_object_or_404(Node, pk=node_pk, is_deleted=False)
    if title:
        Question.objects.create(title=title, answer=answer, source_node=node)
    
    questions = node.questions.filter(is_deleted=False).order_by('created_at')
    return render(request, 'core/partials/question_list_items.html', {'questions': questions, 'node': node})


@router.get("/question/{question_pk}/edit")
def edit_question(request, question_pk: int):
    question = get_object_or_404(Question, pk=question_pk, is_deleted=False)
    return render(request, 'core/partials/question_edit_form.html', {'question': question})


@router.get("/question/{question_pk}/cancel_edit")
def cancel_edit_question(request, question_pk: int):
    question = get_object_or_404(Question, pk=question_pk, is_deleted=False)
    return render(request, 'core/partials/question_list_items.html', {'questions': [question]})


@router.post("/question/{question_pk}")
def update_question(request, question_pk: int, title: str = Form(""), answer: str = Form("")):
    question = get_object_or_404(Question, pk=question_pk, is_deleted=False)
    
    if title:
        question.title = title
        question.answer = answer
        question.save()
        
    return render(request, 'core/partials/question_list_items.html', {'questions': [question]})


@router.delete("/question/{question_pk}")
def delete_question(request, question_pk: int):
    question = get_object_or_404(Question, pk=question_pk, is_deleted=False)
    question.soft_delete()
    return HttpResponse("")

api.add_router("", router)
