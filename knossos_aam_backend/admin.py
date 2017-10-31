from django.contrib import admin

from models import Employee
from models import Project
from models import Submission
from models import Task
from models import TaskCategory
from models import Work


class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        '__unicode__',
        'project',)
    list_editable = (
        'project',
    )


admin.site.register(Project)
admin.site.register(TaskCategory)
admin.site.register(Employee, EmployeeAdmin)
admin.site.register(Task)
admin.site.register(Work)
admin.site.register(Submission)
