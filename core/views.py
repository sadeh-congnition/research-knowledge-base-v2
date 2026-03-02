from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.urls import reverse
from .models import Project, Node, Question
from .chroma_client import collection

def project_list(request):
    projects = Project.objects.all().order_by('-created_at')
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Project.objects.create(name=name)
            if request.htmx:
                return render(request, 'core/partials/project_list_items.html', {'projects': Project.objects.all().order_by('-created_at')})
            return redirect('project_list')
    
    return render(request, 'core/project_list.html', {'projects': projects})

def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'DELETE' or (request.method == 'POST' and request.POST.get('_method') == 'DELETE'):
        project.soft_delete()
        if request.htmx:
            return HttpResponse('')
        return redirect('project_list')
    return HttpResponse(status=405)

def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    nodes = project.nodes.filter(is_deleted=False).order_by('-created_at')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content', '')
        if title:
            Node.objects.create(project=project, title=title, content=content)
            if request.htmx:
                return render(request, 'core/partials/node_list_items.html', {'nodes': project.nodes.filter(is_deleted=False).order_by('-created_at'), 'project': project})
            return redirect('project_detail', pk=pk)
            
    return render(request, 'core/project_detail.html', {'project': project, 'nodes': nodes})

def node_delete(request, pk):
    node = get_object_or_404(Node, pk=pk)
    if request.method == 'DELETE' or (request.method == 'POST' and request.POST.get('_method') == 'DELETE'):
        node.soft_delete()
        if request.htmx:
            return HttpResponse('')
        return redirect('project_detail', pk=node.project.pk)
    return HttpResponse(status=405)

def node_edit(request, pk):
    node = get_object_or_404(Node, pk=pk)
    if request.htmx:
        return render(request, 'core/partials/node_edit_form.html', {'node': node})
    return redirect('project_detail', pk=node.project.pk)

def node_cancel_edit(request, pk):
    node = get_object_or_404(Node, pk=pk)
    if request.htmx:
        return render(request, 'core/partials/node_list_items.html', {'nodes': [node]})
    return redirect('project_detail', pk=node.project.pk)

def node_update(request, pk):
    node = get_object_or_404(Node, pk=pk)
    if request.method == 'POST':
        node.title = request.POST.get('title', node.title)
        node.content = request.POST.get('content', node.content)
        node.save()
        if request.htmx:
            return render(request, 'core/partials/node_list_items.html', {'nodes': [node]})
        return redirect('project_detail', pk=node.project.pk)
    return HttpResponse(status=405)

def node_detail(request, pk):
    node = get_object_or_404(Node, pk=pk)
    url = reverse('project_detail', args=[node.project.pk])
    return redirect(f"{url}#node-{node.pk}")

def question_detail(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if question.source_node:
        url = reverse('project_detail', args=[question.source_node.project.pk])
        return redirect(f"{url}#question-{question.pk}")
    elif question.source_question:
        # For now, just climb one level up (or if we need a recursive function)
        # Assuming one level of nesting for simplicity in routing to the node
        current_q = question
        while current_q.source_question:
            current_q = current_q.source_question
        if current_q.source_node:
            url = reverse('project_detail', args=[current_q.source_node.project.pk])
            return redirect(f"{url}#question-{question.pk}")
    
    # Fallback to search if no source node is found
    return redirect('global_search')

def global_search(request):
    query = request.GET.get('q', '')
    project_id_str = request.GET.get('project_id', '')
    selected_project_id = int(project_id_str) if project_id_str.isdigit() else None
    search_projects = Project.objects.filter(is_deleted=False)
    
    if not query:
        if request.htmx:
            return HttpResponse('')
        return render(request, 'core/search.html', {'results': [], 'query': query, 'search_projects': search_projects, 'selected_project_id': selected_project_id})
        
    where = {}
    if selected_project_id:
        where["project_id"] = selected_project_id
        
    try:
        search_results = collection.query(
            query_texts=[query],
            n_results=10,
            where=where if where else None
        )
        
        results = []
        if search_results and search_results['metadatas'] and len(search_results['metadatas']) > 0:
            for idx, meta in enumerate(search_results['metadatas'][0]):
                doc = search_results['documents'][0][idx]
                results.append({
                    'title': doc.split('\n\n')[0] if '\n\n' in doc else 'Untitled',
                    'snippet': doc[:150] + '...',
                    'type': meta.get('type'),
                    'node_id': meta.get('node_id'),
                    'question_id': meta.get('question_id'),
                    'project_id': meta.get('project_id')
                })
    except Exception as e:
        results = []

    if request.htmx:
        return render(request, 'core/partials/search_results.html', {'results': results})
    
    return render(request, 'core/search.html', {'results': results, 'query': query, 'search_projects': search_projects, 'selected_project_id': selected_project_id})
