from django.contrib import admin
from .models import Celebrity


@admin.register(Celebrity)
class CelebrityAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'epstein_mentions', 'description')
    search_fields = ('full_name',)
    ordering = ('-epstein_mentions',)
