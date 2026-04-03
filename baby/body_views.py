import logging

from rest_framework import permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import GrowthRecord
from .serializers import GrowthRecordSerializer
from .album_views import process_image_variants_for_key

logger = logging.getLogger(__name__)


class GrowthRecordListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

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

        queryset = GrowthRecord.objects.filter(user=request.user).order_by('-measure_date', '-id')
        total = queryset.count()

        start = (page_num - 1) * page_size
        end = start + page_size
        page_data = queryset[start:end]

        serializer = GrowthRecordSerializer(page_data, many=True, context={'request': request})
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
        data = request.data

        payload = {
            'measure_date': data.get('measure_date'),
            'height_cm': data.get('height_cm') or None,
            'weight_kg': data.get('weight_kg') or None,
            'head_circumference_cm': data.get('head_circumference_cm') or None
        }

        serializer = GrowthRecordSerializer(data=payload)
        if not serializer.is_valid():
            return Response({'code': 400, 'msg': str(serializer.errors), 'data': None})

        if not (payload.get('height_cm') or payload.get('weight_kg') or payload.get('head_circumference_cm')):
            return Response({'code': 400, 'msg': 'height_cm/weight_kg/head_circumference_cm 至少填写一项', 'data': None})

        record = GrowthRecord.objects.create(
            user=request.user,
            measure_date=serializer.validated_data['measure_date'],
            height_cm=serializer.validated_data.get('height_cm'),
            weight_kg=serializer.validated_data.get('weight_kg'),
            head_circumference_cm=serializer.validated_data.get('head_circumference_cm'),
            photo=request.FILES.get('photo')
        )
        try:
            key = getattr(getattr(record, 'photo', None), 'name', None) or ''
            if key:
                process_image_variants_for_key(key=key, base_key=f'growth/thumbs/gr_{record.id}_w400', width=400)
        except Exception:
            logger.exception("growth photo post-process failed")

        return Response({'code': 200, 'msg': 'ok', 'data': GrowthRecordSerializer(record, context={'request': request}).data})


class GrowthRecordDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, pk):
        try:
            record = GrowthRecord.objects.get(pk=pk, user=request.user)
        except GrowthRecord.DoesNotExist:
            return Response({'code': 404, 'msg': 'Not found', 'data': None})

        return Response({'code': 200, 'msg': 'ok', 'data': GrowthRecordSerializer(record, context={'request': request}).data})

    def put(self, request, pk):
        try:
            record = GrowthRecord.objects.get(pk=pk, user=request.user)
        except GrowthRecord.DoesNotExist:
            return Response({'code': 404, 'msg': 'Not found', 'data': None})

        data = request.data
        update_data = {}

        if 'measure_date' in data:
            update_data['measure_date'] = data.get('measure_date')
        if 'height_cm' in data:
            update_data['height_cm'] = data.get('height_cm') or None
        if 'weight_kg' in data:
            update_data['weight_kg'] = data.get('weight_kg') or None
        if 'head_circumference_cm' in data:
            update_data['head_circumference_cm'] = data.get('head_circumference_cm') or None

        serializer = GrowthRecordSerializer(record, data=update_data, partial=True)
        if not serializer.is_valid():
            return Response({'code': 400, 'msg': str(serializer.errors), 'data': None})

        next_height = serializer.validated_data.get('height_cm', record.height_cm)
        next_weight = serializer.validated_data.get('weight_kg', record.weight_kg)
        next_head = serializer.validated_data.get('head_circumference_cm', record.head_circumference_cm)
        if not (next_height or next_weight or next_head):
            return Response({'code': 400, 'msg': 'height_cm/weight_kg/head_circumference_cm 至少填写一项', 'data': None})

        serializer.save()

        if request.FILES.get('photo'):
            record.photo = request.FILES.get('photo')
            record.save(update_fields=['photo', 'updated_at'])
            try:
                key = getattr(getattr(record, 'photo', None), 'name', None) or ''
                if key:
                    process_image_variants_for_key(key=key, base_key=f'growth/thumbs/gr_{record.id}_w400', width=400)
            except Exception:
                logger.exception("growth photo post-process failed")
        else:
            remove_photo = str(data.get('remove_photo', '')).lower() in ['1', 'true', 'yes']
            if remove_photo and record.photo:
                record.photo = None
                record.save(update_fields=['photo', 'updated_at'])

        return Response({'code': 200, 'msg': 'ok', 'data': GrowthRecordSerializer(record, context={'request': request}).data})

    def delete(self, request, pk):
        try:
            record = GrowthRecord.objects.get(pk=pk, user=request.user)
        except GrowthRecord.DoesNotExist:
            return Response({'code': 404, 'msg': 'Not found', 'data': None})

        record.delete()
        return Response({'code': 200, 'msg': 'ok', 'data': None})
