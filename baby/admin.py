from django.contrib import admin
from .models import BabyAlbum, AlbumPhoto

# Register your models here.

class AlbumPhotoInline(admin.TabularInline):
    model = AlbumPhoto
    extra = 1

@admin.register(BabyAlbum)
class BabyAlbumAdmin(admin.ModelAdmin):
    list_display = ('user', 'content', 'happened_at', 'visibility', 'created_at')
    list_filter = ('visibility', 'created_at', 'happened_at')
    search_fields = ('content', 'tags')
    inlines = [AlbumPhotoInline]

@admin.register(AlbumPhoto)
class AlbumPhotoAdmin(admin.ModelAdmin):
    list_display = ('album', 'image', 'created_at')
