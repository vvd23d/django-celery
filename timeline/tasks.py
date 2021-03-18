from datetime import timedelta

from elk.celery import app as celery
from market.models import Class
from timeline.signals import class_starting_student, class_starting_teacher

from market.models import Subscription
from django.utils import timezone
from timeline.signals import class_skipping_student


@celery.task
def notify_15min_to_class():
    for i in Class.objects.starting_soon(timedelta(minutes=30)).filter(pre_start_notifications_sent_to_teacher=False).distinct('timeline'):
        for other_class_with_the_same_timeline in Class.objects.starting_soon(timedelta(minutes=30)).filter(timeline=i.timeline):
            """
            Set all other starting classes as notified either.
            """
            other_class_with_the_same_timeline.pre_start_notifications_sent_to_teacher = True
            other_class_with_the_same_timeline.save()
        class_starting_teacher.send(sender=notify_15min_to_class, instance=i)

    for i in Class.objects.starting_soon(timedelta(minutes=30)).filter(pre_start_notifications_sent_to_student=False):
        i.pre_start_notifications_sent_to_student = True
        i.save()
        class_starting_student.send(sender=notify_15min_to_class, instance=i)


@celery.task
def reminder_7days_not_take_lessons():
    for i in Subscription.objects.filter(is_fully_used=False):
        cs = i.classes \
            .filter(timeline__isnull=False) \
            .filter(timeline__is_finished__exact=True) \
            .filter(timeline__end__lte=timezone.now() - timedelta(days=7))
        if cs:
            c = cs.last()
            class_skipping_student.send(sender=reminder_7days_not_take_lessons, instance=c)
