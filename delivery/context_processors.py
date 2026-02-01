import redis

def system_status_context(request):
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        redis_connected = True
    except:
        redis_connected = False
    
    try:
        from celery.task.control import inspect
        i = inspect()
        active_workers = i.active() or {}
        celery_running = len(active_workers) > 0
    except:
        celery_running = False
    
    return {
        'system_status': {
            'redis': redis_connected,
            'celery': celery_running,
            'running': redis_connected and celery_running,
        }
    }