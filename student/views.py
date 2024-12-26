from rest_framework import viewsets
from .serializer import StudentSerializer
from .models import Student

class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    queryset = Student.objects.all()