from django.shortcuts import get_object_or_404
from datetime import date, timedelta
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from tasks.utils.apply_routines import apply_routines
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..models import Tasks
from ..utils import tasks_managements_utils
from django.views.decorators.csrf import csrf_exempt

#the user today_tasks function
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def today_tasks(request):
    today = date.today()
    apply_routines(request, today)

    user_tasks_qs = Tasks.objects.filter(
        created_by=request.user
    ).filter(
        Q(due_date__date=today) |
        Q(due_date__date__lt=today, status=False)
    ).order_by('status', 'due_date').all()

    paginator = Paginator(user_tasks_qs, 20)
    page_num = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    tasks_list = [tasks_managements_utils.serialize_task(t) for t in page_obj.object_list]
    completed_tasks_count = user_tasks_qs.filter(status=True).count()
    total_number_tasks = user_tasks_qs.count()

    response_data = {
        'success': True,
        "username": request.user.username,
        "user_tasks": tasks_list,
        "pagination": {
            "page": page_obj.number,
            "num_pages": paginator.num_pages,
            "per_page": paginator.per_page,
            "total": paginator.count,
        },
        "total_number_tasks": total_number_tasks,
        "completed_tasks_count": completed_tasks_count,
        "pending_tasks": total_number_tasks - completed_tasks_count,
    }
    return Response(response_data, status=status.HTTP_200_OK)

#the user all_tasks function
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_tasks(request):
    user_tasks_qs = Tasks.objects.filter(created_by=request.user).order_by('status', 'due_date').all()

    paginator = Paginator(user_tasks_qs, 20)
    page_num = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    tasks_list = [tasks_managements_utils.serialize_task(t) for t in page_obj.object_list]
    completed_tasks_count = user_tasks_qs.filter(status=True).count()
    total_number_tasks = user_tasks_qs.count()

    response_data = {
        "success": True,
        "username": request.user.username,
        "user_tasks": tasks_list,
        "pagination": {
            "page": page_obj.number,
            "num_pages": paginator.num_pages,
            "per_page": paginator.per_page,
            "total": paginator.count,
        },
        "total_number_tasks": total_number_tasks,
        "completed_tasks_count": completed_tasks_count,
        "pending_tasks": total_number_tasks - completed_tasks_count,
    }
    return Response(response_data, status=status.HTTP_200_OK)

#the next_week_tasks function
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def next_week_tasks(request):
    today = date.today()
    apply_routines(request, today)
    week_later = today + timedelta(days=7)

    user_tasks_qs = Tasks.objects.filter(
        created_by=request.user,
        due_date__date__gte=today,
        due_date__date__lte=week_later
    ).order_by('status', 'due_date').all()

    paginator = Paginator(user_tasks_qs, 20)
    page_num = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    tasks_list = [tasks_managements_utils.serialize_task(t) for t in page_obj.object_list]
    completed_tasks_count = user_tasks_qs.filter(status=True).count()
    total_number_tasks = user_tasks_qs.count()

    response_data = {
        "success": True,
        "username": request.user.username,
        "user_tasks": tasks_list,
        "pagination": {
            "page": page_obj.number,
            "num_pages": paginator.num_pages,
            "per_page": paginator.per_page,
            "total": paginator.count,
        },
        "total_number_tasks": total_number_tasks,
        "completed_tasks_count": completed_tasks_count,
        "pending_tasks": total_number_tasks - completed_tasks_count,
    }
    return Response(response_data, status=status.HTTP_200_OK)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_task(request):
    try:
        today = timezone.now().date()

        url_call = request.data.get("url_call", "all")
        task_title = request.data.get("task_title")
        task_details = request.data.get("task_details")
        due_date_raw = request.data.get("due_date")
        due_date = tasks_managements_utils._parse_date_input(due_date_raw) or today

        task = Tasks.objects.create(
            task_title=task_title,
            task_details=task_details,
            due_date=due_date,
            created_by=request.user,
        )

        task_data = tasks_managements_utils.serialize_task(task)

        total, completed, pending = tasks_managements_utils.tasks_count(url_call, request)

        return Response({
            "success": True,
            "task": task_data,
            "total_number_tasks": total,
            "completed_tasks_count": completed,
            "pending_tasks": pending
        }, status=status.HTTP_201_CREATED)
    
    except Exception:
        return Response(
            {
                'error': 'An error occurred',
                'success': False
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_task(request, task_id):
    try:
        url_call = request.data.get("url_call", "all")
        task = get_object_or_404(Tasks, id=task_id, created_by=request.user)

        task_title = request.data.get("task_title", task.task_title)
        task_details = request.data.get("task_details", task.task_details)
        due_date_raw = request.data.get("due_date", None)
    
        task.task_title = task_title
        task.task_details = task_details
        if due_date_raw is not None:
            parsed = tasks_managements_utils._parse_date_input(due_date_raw)
            task.due_date = parsed

        task.save()

        task_data = tasks_managements_utils.serialize_task(task)

        total, completed, pending = tasks_managements_utils.tasks_count(url_call, request)

        return Response({
            "success": True,
            "task": task_data,
            "total_number_tasks": total,
            "completed_tasks_count": completed,
            "pending_tasks": pending
        }, status=status.HTTP_200_OK)
    
    except Exception:
        return Response(
            {
                'error': 'An error occurred',
                'success': False
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def multiple_update_task_dates(request):
    try:
        url_call = request.data.get("url_call", "all")
        task_ids = request.data.get("task_ids", [])

        if not isinstance(task_ids, list):
            return Response({"error": "task_ids should be a list of IDs", "success": False},
                            status=status.HTTP_400_BAD_REQUEST)
        if not task_ids:
            return Response({"error": "task_ids list is empty", "success": False},
                            status=status.HTTP_400_BAD_REQUEST)

        tasks_qs = Tasks.objects.filter(id__in=task_ids, created_by=request.user)
        if not tasks_qs.exists():
            return Response({"error": "No tasks found", "success": False},
                            status=status.HTTP_404_NOT_FOUND)

        due_date_raw = request.data.get("due_date", None)
        if due_date_raw is not None:
            parsed = tasks_managements_utils._parse_date_input(due_date_raw)
            for t in tasks_qs:
                t.due_date = parsed
            Tasks.objects.bulk_update(tasks_qs, ['due_date'])

        tasks_data = [tasks_managements_utils.serialize_task(t) for t in tasks_qs]
        total, completed, pending = tasks_managements_utils.tasks_count(url_call, request)

        return Response({
            "success": True,
            "tasks": tasks_data,
            "total_number_tasks": total,
            "completed_tasks_count": completed,
            "pending_tasks": pending
        }, status=status.HTTP_200_OK)
    except Exception:
        return Response({"error": "An error occurred", "success": False},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_task(request, task_id):
    try:
        task = get_object_or_404(Tasks, id=task_id, created_by=request.user)
        url_call = request.data.get("url_call", "all")

        task.delete()
        total, completed, pending = tasks_managements_utils.tasks_count(url_call, request)
        return Response({
            "success": True,
            "message": "Task deleted",
            "total_number_tasks": total,
            "completed_tasks_count": completed,
            "pending_tasks": pending,
        }, status=status.HTTP_200_OK)
    except Exception:
        return Response({"error": "An error occurred", "success": False},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def multiple_delete_task(request):
    try:
        task_ids = request.data.get("task_ids", [])
        url_call = request.data.get("url_call", "all")
        if not isinstance(task_ids, list):
            return Response({"error": "task_ids should be a list of IDs", "success": False},
                            status=status.HTTP_400_BAD_REQUEST)
        if not task_ids:
            return Response({"error": "task_ids list is empty", "success": False},
                            status=status.HTTP_400_BAD_REQUEST)
        tasks_qs = Tasks.objects.filter(id__in=task_ids, created_by=request.user)

        tasks_qs.delete()
        total, completed, pending = tasks_managements_utils.tasks_count(url_call, request)
        return Response({
            "success": True,
            "message": "Tasks deleted",
            "total_number_tasks": total,
            "completed_tasks_count": completed,
            "pending_tasks": pending,
        }, status=status.HTTP_200_OK)
    except Exception:
        return Response({"error": "An error occurred", "success": False},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def task_complete(request, task_id):
    try:
        url_call = request.data.get("url_call", "all")
        task = get_object_or_404(Tasks, id=task_id, created_by=request.user)
        task.status = not task.status  # simplified toggle
        task.done_date = timezone.now().date() if task.status else None
        task.save()

        task_data = tasks_managements_utils.serialize_task(task)
        total, completed, pending = tasks_managements_utils.tasks_count(url_call, request)
        return Response({
            "success": True,
            "task": task_data,
            "total_number_tasks": total,
            "completed_tasks_count": completed,
            "pending_tasks": pending,
        }, status=status.HTTP_200_OK)
    except Exception:
        return Response({"error": "An error occurred", "success": False},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def multiple_task_complete(request):
    try:
        url_call = request.data.get("url_call", "all")
        task_ids = request.data.get("task_ids", [])
        if not isinstance(task_ids, list):
            return Response({"error": "task_ids should be a list of IDs", "success": False},
                            status=status.HTTP_400_BAD_REQUEST)
        tasks_qs = Tasks.objects.filter(id__in=task_ids, created_by=request.user)
        
        for t in tasks_qs:
            t.status = not t.status
            t.done_date = timezone.now().date() if t.status else None
        
        Tasks.objects.bulk_update(tasks_qs, ['status', 'done_date'])
        tasks_data = [tasks_managements_utils.serialize_task(t) for t in tasks_qs]
        total, completed, pending = tasks_managements_utils.tasks_count(url_call, request)
        return Response({
            "success": True,
            "tasks": tasks_data,
            "total_number_tasks": total,
            "completed_tasks_count": completed,
            "pending_tasks": pending,
        }, status=status.HTTP_200_OK)
    except Exception:
        return Response({"error": "An error occurred", "success": False},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
