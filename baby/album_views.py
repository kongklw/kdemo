from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import BabyAlbum, AlbumPhoto
from fileUpload.models import MediaAsset
from .serializers import BabyAlbumSerializer
import json
import logging

logger = logging.getLogger(__name__)

class BabyAlbumListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        try:
            page_size = int(request.query_params.get('page_size', 20))
        except (TypeError, ValueError):
            page_size = 20
        try:
            page_num = int(request.query_params.get('page_num', 1))
        except (TypeError, ValueError):
            page_num = 1

        if page_size <= 0:
            page_size = 20
        if page_num <= 0:
            page_num = 1

        queryset = BabyAlbum.objects.filter(user=request.user).order_by('-happened_at', '-created_at')
        total = queryset.count()

        start = (page_num - 1) * page_size
        end = start + page_size
        page_data = queryset[start:end]

        serializer = BabyAlbumSerializer(page_data, many=True, context={'request': request})
        return Response({
            'code': 200,
            'msg': 'ok',
            'data': {
                'list': serializer.data,
                'total': total,
                'page_num': page_num,
                'page_size': page_size
            }
        })

    def post(self, request):
        try:
            # Avoid using copy() on QueryDict if it contains files to prevent pickling errors
            if hasattr(request.data, 'dict'):
                data = request.data.dict()
            else:
                data = request.data.copy()
                
            # Handle tags if they come as string (FormData)
            tags = data.get('tags')
            if tags and isinstance(tags, str):
                try:
                    # If tags are like "['tag1', 'tag2']" or just a string
                    # If it's just a comma separated string, split it
                    if tags.startswith('['):
                        data['tags'] = json.loads(tags)
                    else:
                         data['tags'] = [t.strip() for t in tags.split(',') if t.strip()]
                except:
                    data['tags'] = []
            
            media_asset_ids = data.get('media_asset_ids') if isinstance(data, dict) else None
            serializer = BabyAlbumSerializer(data=data, context={'request': request})
            if serializer.is_valid():
                album = serializer.save()
                
                # Handle images
                # FormData should append images with same key 'images' or 'file'
                images = request.FILES.getlist('images')
                if not images:
                    # Try 'file' as well just in case
                    images = request.FILES.getlist('file')

                if images:
                    for image in images:
                        is_video = False
                        if hasattr(image, 'content_type') and image.content_type.startswith('video/'):
                            is_video = True
                        elif hasattr(image, 'name') and image.name.lower().endswith(('.mp4', '.mov', '.avi', '.wmv', '.flv', '.mkv', '.webm')):
                            is_video = True
                        AlbumPhoto.objects.create(album=album, image=image, is_video=is_video)
                elif isinstance(media_asset_ids, list) and media_asset_ids:
                    assets = list(MediaAsset.objects.filter(user=request.user, id__in=media_asset_ids, status=MediaAsset.Status.UPLOADED))
                    by_id = {a.id: a for a in assets}
                    for aid in media_asset_ids:
                        asset = by_id.get(aid)
                        if not asset:
                            continue
                        AlbumPhoto.objects.create(album=album, image=asset.object_key, is_video=asset.is_video)
                        asset.ref_type = 'baby_album'
                        asset.ref_id = album.id
                        asset.status = MediaAsset.Status.BOUND
                        asset.save(update_fields=['ref_type', 'ref_id', 'status', 'updated_at'])
                
                # Refresh to include photos in response
                return Response({'code': 200, 'msg': 'ok', 'data': BabyAlbumSerializer(album).data})
            
            return Response({'code': 400, 'msg': str(serializer.errors), 'data': None})
        except Exception as e:
            logger.exception("BabyAlbum create error")
            return Response({'code': 500, 'msg': str(e), 'data': None})

class BabyAlbumDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            album = BabyAlbum.objects.get(pk=pk, user=request.user)
            album.delete()
            return Response({'code': 200, 'msg': 'ok', 'data': None})
        except BabyAlbum.DoesNotExist:
            return Response({'code': 404, 'msg': 'Not found', 'data': None})
