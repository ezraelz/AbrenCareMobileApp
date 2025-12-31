from django.db import models


class Role(models.Model):
    role_name = models.CharField(("Role Name"), max_length=50)
    description = models.TextField(("Description"), blank=True, null=True)
    created_at = models.DateTimeField(("Created at"), auto_now=False, auto_now_add=True)

    def __str__(self):
        return self.role_name
