from celery import shared_task

@shared_task
def send_test_email():
    print("Celery działa! Wysyłam maila... (tzn. printuję :)")