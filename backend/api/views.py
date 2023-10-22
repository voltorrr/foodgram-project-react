from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework import mixins
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        SAFE_METHODS)
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from recipes.models import (Recipe, Tag, Ingredient,
                            Favorite, ShoppingCart, User, Follow)
from api.serializers import (RecipeListSerializer, TagSerializer,
                             IngredientSerializer, FavoriteSerializer,
                             ShoppingCartSerializer, RecipeWriteSerializer,
                             FollowSerializer, UserSerializer)
from api.services import shopping_cart
from api.permissions import (IsOwnerOrAdminOrReadOnly,
                             IsCurrentUserOrAdminOrReadOnly)
from api.filters import IngredientSearchFilter, RecipeFilter
from api.paginations import ApiPagination
from djoser.serializers import SetPasswordSerializer


class TagViewSet(mixins.ListModelMixin,
                 mixins.RetrieveModelMixin,
                 viewsets.GenericViewSet):
    """Функция для модели тегов."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny, )


class IngredientViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """Функция для модели ингредиентов."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny, )
    filter_backends = (IngredientSearchFilter, )
    search_fields = ('^name',)


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет модели Recipe: [GET, POST, DELETE, PATCH]."""
    queryset = Recipe.objects.all()
    permission_classes = (IsOwnerOrAdminOrReadOnly, )
    filter_backends = (DjangoFilterBackend, )
    pagination_class = ApiPagination
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeListSerializer
        return RecipeWriteSerializer

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, *args, **kwargs):
        """
        Получить / Добавить / Удалить  рецепт
        из избранного у текущего пользоватля.
        """
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('pk'))
        user = self.request.user
        if request.method == 'POST':
            if Favorite.objects.filter(author=user,
                                       recipe=recipe).exists():
                return Response({'errors': 'Рецепт уже добавлен!'},
                                status=status.HTTP_400_BAD_REQUEST)
            serializer = FavoriteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(author=user, recipe=recipe)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        if not Favorite.objects.filter(author=user,
                                       recipe=recipe).exists():
            return Response({'errors': 'Объект не найден'},
                            status=status.HTTP_404_NOT_FOUND)
        Favorite.objects.get(recipe=recipe).delete()
        return Response('Рецепт успешно удалён из избранного.',
                        status=status.HTTP_204_NO_CONTENT)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, **kwargs):
        """
        Получить / Добавить / Удалить  рецепт
        из списка покупок у текущего пользоватля.
        """
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('pk'))
        user = self.request.user
        if request.method == 'POST':
            if ShoppingCart.objects.filter(author=user,
                                           recipe=recipe).exists():
                return Response({'errors': 'Рецепт уже добавлен!'},
                                status=status.HTTP_400_BAD_REQUEST)
            serializer = ShoppingCartSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(author=user, recipe=recipe)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        if not ShoppingCart.objects.filter(author=user,
                                           recipe=recipe).exists():
            return Response({'errors': 'Объект не найден'},
                            status=status.HTTP_404_NOT_FOUND)
        ShoppingCart.objects.get(recipe=recipe).delete()
        return Response('Рецепт успешно удалён из списка покупок.',
                        status=status.HTTP_204_NO_CONTENT)

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        """
        Скачать список покупок для выбранных рецептов,
        данные суммируются.
        """
        author = User.objects.get(id=self.request.user.pk)
        if author.shopping_cart.exists():
            return shopping_cart(self, request, author)
        return Response('Список покупок пуст.',
                        status=status.HTTP_404_NOT_FOUND)


class UserViewSet(viewsets.ModelViewSet):
    """Viewset для пользователя / подписок."""
    queryset = User.objects.all()
    permission_classes = (IsCurrentUserOrAdminOrReadOnly, )
    pagination_class = ApiPagination
    serializer_class = UserSerializer

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def me(self, request):
        """Кастомное получение профиля пользователя."""
        user = self.request.user
        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data)

    @action(["post"],
            detail=False,
            permission_classes=[IsAuthenticated])
    def set_password(self, request, *args, **kwargs):
        """
        Кастомное изменение пароля с помощью cериализатора
        из пакета djoser SetPasswordSerializer.
        """
        serializer = SetPasswordSerializer(
            data=request.data,
            context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.request.user.set_password(serializer.data["new_password"])
        self.request.user.save()
        return Response('Пароль успешно изменен',
                        status=status.HTTP_204_NO_CONTENT)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, *args, **kwargs):
        """Создание и удаление подписки."""
        author = get_object_or_404(User, id=self.kwargs.get('pk'))
        user = self.request.user
        if request.method == 'POST':
            serializer = FollowSerializer(
                data=request.data,
                context={'request': request, 'author': author})
            serializer.is_valid(raise_exception=True)
            serializer.save(author=author, user=user)
            return Response({'Подписка успешно создана': serializer.data},
                            status=status.HTTP_201_CREATED)
        if Follow.objects.filter(author=author, user=user).exists():
            Follow.objects.get(author=author).delete()
            return Response('Успешная отписка',
                            status=status.HTTP_204_NO_CONTENT)
        return Response({'errors': 'Объект не найден'},
                        status=status.HTTP_404_NOT_FOUND)

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        """Отображает все подписки пользователя."""
        follows = Follow.objects.filter(user=self.request.user)
        pages = self.paginate_queryset(follows)
        serializer = FollowSerializer(pages,
                                      many=True,
                                      context={'request': request})
        return self.get_paginated_response(serializer.data)
