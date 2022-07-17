from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='tester')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост' * 10,
        )

    def test_models_have_correct_objects_name(self):
        """Проверяем что у моделей корректно работает __str__"""
        model_expected = {
            self.group: self.group.title,
            self.post: self.post.text[:settings.TEXT_SIZE_NUMBER]
        }
        for model, exp in model_expected.items():
            with self.subTest(model=model):
                self.assertEqual(exp, str(model))

    def test_post_verbose_name(self):
        """Проверка verobse_name модели Post"""
        field_verbose = {
            'text': 'Текст',
            'group': 'Группа'
        }
        for field, verbose in field_verbose.items():
            with self.subTest(field=field):
                self.assertEqual(
                    self.post._meta.get_field(field).verbose_name, verbose
                )

    def test_post_help_text(self):
        """Проверка help_text модели Post"""
        field_help_text = {
            'text': 'Сюда текст',
            'group': 'Из предложенных :)'
        }
        for field, ht in field_help_text.items():
            with self.subTest(field=field):
                self.assertEqual(
                    self.post._meta.get_field(field).help_text, ht
                )
