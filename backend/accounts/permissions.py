from rest_framework.permissions import BasePermission


class HasRole(BasePermission):
    message = "Seu perfil não tem permissão para esta ação."

    def __init__(self, *roles):
        self.roles = roles

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in self.roles)


class IsOwnerOrAdmin(BasePermission):
    message = "Apenas o autor ou um administrador pode realizar esta ação."

    def __init__(self, owner_id=lambda obj: obj.autor_id):
        self.owner_id = owner_id

    def has_object_permission(self, request, view, obj):
        return request.user.role == "admin" or self.owner_id(obj) == request.user.id
