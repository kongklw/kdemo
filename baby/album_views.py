from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from .models import BabyAlbum, AlbumPhoto
from .serializers import BabyAlbumSerializer
import json
import logging

logger = logging.getLogger(__name__)

class BabyAlbumListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        # Simple list for now, pagination can be added later if needed
        albums = BabyAlbum.objects.filter(user=request.user)
        serializer = BabyAlbumSerializer(albums, many=True)
        return Response({'code': 200, 'msg': 'ok', 'data': serializer.data})

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
            
            serializer = BabyAlbumSerializer(data=data, context={'request': request})
            if serializer.is_valid():
                album = serializer.save()
                
                # Handle images
                # FormData should append images with same key 'images' or 'file'
                images = request.FILES.getlist('images')
                if not images:
                    # Try 'file' as well just in case
                    images = request.FILES.getlist('file')

                for image in images:
                    AlbumPhoto.objects.create(album=album, image=image)
                
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
