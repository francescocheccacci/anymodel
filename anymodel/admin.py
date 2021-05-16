from flask import current_app as app, request, flash, url_for, redirect
from flask_login import current_user
from flask_admin import Admin, AdminIndexView as BaseAdminIndexView, expose
from flask_admin.actions import action
from flask_admin.contrib.sqla import ModelView as BaseModelView
from . import db, models

# Customize admin views
class AnyModelView(BaseModelView):

    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_staff

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('users.login', next=request.url))

admin = Admin(app, name='AnyModel admin', template_mode='bootstrap3')

admin.add_view(AnyModelView(models.User, db.session))
