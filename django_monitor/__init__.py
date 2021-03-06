__author__ = "Rajeesh Nair"
__version__ = "0.2"
__copyright__ = "Copyright (c) 2011 Rajeesh"
__license__ = "BSD"

from django.db.models import signals
from django.db.models.loading import get_model
from django.dispatch import Signal
from django_monitor.conf import PENDING_STATUS
from django_monitor.models import MonitorEntry
from django_monitor.util import create_moderate_perms, add_fields, save_handler, \
    delete_handler
import datetime
    


def _default_long_desc(obj):
    return unicode(obj)

_queue = {}

def model_from_queue(model):
    """ Returns the model dict if model is enqueued, else None."""
    return _queue.get(model, None)

def queued_models():
    """ Return the models enqueued for moderation"""
    return _queue.keys()

def get_monitor_entry(obj):
    """
    Returns the monitor_entry for the given object.
    Deprecated.
    No one except the given object need access to the monitor_entry.
    """
    model_dict = model_from_queue(obj.__class__)
    return getattr(obj, model_dict['monitor_name']) if model_dict else None

def nq(
    model, rel_fields = [], import_unmoderated=False, can_delete_approved = True, long_desc=None,
    manager_name = 'objects', status_name = 'status',
    monitor_name = 'monitor_entry', base_manager = None, notify_moderators=None
):
    """ Register(enqueue) the model for moderation."""
    if not model_from_queue(model):
        signals.post_save.connect(save_handler, sender = model)
        signals.pre_delete.connect(delete_handler, sender = model)
        registered_model = get_model(
            model._meta.app_label, model._meta.object_name, only_installed=False
        )
        add_fields(
            registered_model, manager_name, status_name,
            monitor_name, base_manager
        )
        _queue[model] = {
            'rel_fields': rel_fields,
            'can_delete_approved': can_delete_approved,
            'manager_name': manager_name,
            'status_name': status_name,
            'monitor_name': monitor_name,
            'long_desc': long_desc or _default_long_desc,
            'notify_moderators': notify_moderators,
        }
        if import_unmoderated:
            try:
                mod_obj_ids = model.objects.all().values_list('pk', flat=True)
                unmod_objs = model._base_manager.exclude(pk__in=mod_obj_ids)
                print 'importing %s unmoderated objects...' % unmod_objs.count()
                for obj in unmod_objs:
                    me = MonitorEntry(
                        status=PENDING_STATUS,
                        content_object=obj,
                        status_date=datetime.datetime.now())
                    me.save()
            except:
                pass

post_moderation = Signal(providing_args = ["instance"])

signals.post_syncdb.connect(
    create_moderate_perms,
    dispatch_uid = "django-monitor.create_moderate_perms"
)

