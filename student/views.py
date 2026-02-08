from rest_framework import viewsets
from .serializer import StudentSerializer
from .models import Student

class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    queryset = Student.objects.all() # 移除默认 queryset，改用 get_queryset

    def get_queryset(self):
        # 只返回当前用户的学生数据
        return Student.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # 创建时自动关联当前用户
        serializer.save(user=self.request.user)