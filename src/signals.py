from datetime import datetime
import logging

from sqlalchemy import event

from .models import Media


logger = logging.getLogger()


@event.listens_for(Media, "before_update")
def on_media_before_update(mapper, connection, target):
    target.updated_at = datetime.utcnow()
