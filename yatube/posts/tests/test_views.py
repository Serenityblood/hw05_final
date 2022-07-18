import tempfile
import shutil

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms

from ..models import Follow, Group, Post, User
from ..forms import PostForm

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='tester')
        cls.group = Group.objects.create(
            title='Test title',
            slug='test',
            description='Test description',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Test text',
            group=cls.group,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def pages_tests(self, response, some_bool=False):
        """Проверка контекста"""
        if not some_bool:
            context_data = response.context['page_obj'][0]
        if some_bool:
            context_data = response.context['post']
        value_exp = {
            context_data.text: self.post.text,
            context_data.group: self.post.group,
            context_data.pub_date: self.post.pub_date,
            context_data.author: self.user,
            context_data.image: self.post.image
        }
        self.assertContains(response, '<img')
        for value, expected in value_exp.items():
            with self.subTest(value=value):
                self.assertEqual(value, expected)

    def test_index_context(self):
        """Проверка контекста главной страницы"""
        response = (
            self.authorized_client.get(reverse('posts:main_page'))
        )
        self.pages_tests(response)

    def test_group_list_context(self):
        """Проверка контекста страницы группы"""
        response = (
            self.authorized_client.
            get(reverse('posts:group_posts_page', args=(self.group.slug,)))
        )
        self.pages_tests(response)
        self.assertEqual(response.context['group'], self.group)

    def test_profile_contex(self):
        """Проверка контекста страницы профиля"""
        response = (
            self.authorized_client.
            get(reverse('posts:profile', args=(self.user.username,)))
        )
        self.pages_tests(response)
        self.assertEqual(
            response.context['author'], self.user
        )

    def test_post_detail_context(self):
        """Проверка контекста страницы поста"""
        response = (
            self.authorized_client.
            get(reverse(
                'posts:post_detail', args=(self.post.pk,)
            )
            )
        )
        self.pages_tests(response, True)

    def test_right_group_with_post(self):
        """Пост попадает в нужную группу"""
        new_group = Group.objects.create(
            title='Test title 2',
            slug='testing',
            description='Test description 2',
        )
        new_post = Post.objects.create(
            author=self.user,
            text='Test text 2',
            group=self.group
        )
        self.assertIsNotNone(new_post.group)
        self.assertEqual(new_group.posts.count(), 0)
        response_1 = self.authorized_client.get(
            reverse('posts:group_posts_page', args=(new_group.slug,))
        )
        self.assertEqual(
            len(response_1.context['page_obj'].object_list), 0
        )
        response_2 = self.authorized_client.get(
            reverse('posts:group_posts_page', args=(self.group.slug,))
        )
        self.assertEqual(
            len(response_2.context['page_obj'].object_list), 2
        )

    def test_post_create_edit_context(self):
        """Контекст страницы создания/редактирования поста"""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        names_args = (
            ('posts:post_create', None),
            ('posts:post_edit', (self.post.pk,))
        )
        for name, arg in names_args:
            with self.subTest(name=name):
                response = self.authorized_client.get(
                    reverse(name, args=arg)
                )
                self.assertIn('form', response.context)
                self.assertIsInstance(response.context['form'], PostForm)
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = response.context['form'].fields[value]
                        self.assertIsInstance(form_field, expected)

    def test_index_cache_works(self):
        new_post = Post.objects.create(
            text='text',
            author=self.user
        )
        response = self.authorized_client.get(reverse('posts:main_page'))
        content_before = response.content
        new_post.delete()
        response_2 = self.authorized_client.get(reverse('post:main_page'))
        content_after_delete = response_2.content
        self.assertEqual(content_before, content_after_delete)
        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:main_page'))
        content_after_clear = response_3.content
        self.assertNotEqual(content_before, content_after_clear)

    def test_auth_user_can_follow(self):
        """Работают ли подписки"""
        user1 = User.objects.create_user(username='test1')
        follow_count = Follow.objects.count()
        self.authorized_client.get(
            reverse('posts:profile_follow', args=(user1.username,))
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        self.assertEqual(Follow.objects.first().user, self.user)
        self.assertEqual(Follow.objects.first().author, user1)

    def test_auth_user_can_unfollow(self):
        user2 = User.objects.create_user(username='test2')
        Follow.objects.create(
            user=self.user,
            author=user2
        )
        follow_count = Follow.objects.count()
        self.authorized_client.get(
            reverse('posts:profile_unfollow', args=(user2.username,))
        )
        self.assertEqual(Follow.objects.count(), follow_count - 1)

    def test_new_post_appears_on_right_user(self):
        """Новый пост на нужной странице"""
        user1 = User.objects.create(username='test1')
        user2 = User.objects.create(username='test2')
        just_client = Client()
        just_client.force_login(user2)
        Follow.objects.create(
            user=self.user,
            author=user1
        )
        clients_posts = ((just_client, 0), (self.authorized_client, 0))
        for man, num in clients_posts:
            with self.subTest(man=man):
                response = man.get(
                    reverse('posts:follow_index')
                )
                self.assertEqual(
                    len(response.context['page_obj'].object_list), num
                )
        Post.objects.create(
            text='test',
            author=user1
        )
        clients_posts = ((just_client, 0), (self.authorized_client, 1))
        for man, num in clients_posts:
            with self.subTest(man=man):
                response = man.get(
                    reverse('posts:follow_index')
                )
                self.assertEqual(
                    len(response.context['page_obj'].object_list), num
                )


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='tester')
        cls.user2 = User.objects.create_user(username='tester2')
        cls.group = Group.objects.create(
            title='Test title',
            slug='test',
            description='Test description'
        )
        Follow.objects.create(
            user=cls.user,
            author=cls.user2
        )
        for post_number in range(settings.POSTS_NUMBER):
            Post.objects.create(
                author=cls.user2,
                text=(f'Test title {post_number}'),
                group=cls.group,
            )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_records_on_pages(self):
        """Проверка пагинатора"""
        names_args = (
            ('posts:main_page', None),
            ('posts:group_posts_page', (self.group.slug,)),
            ('posts:profile', (self.user2.username,)),
            ('posts:follow_index', None)
        )
        pages_posts = (
            ('?page=1', settings.PAGE_NUMBER),
            ('?page=2', (settings.POSTS_NUMBER - settings.PAGE_NUMBER))
        )
        for name, arg in names_args:
            with self.subTest(name=name):
                for page, posts in pages_posts:
                    with self.subTest(page=page):
                        response = self.authorized_client.get(
                            reverse(name, args=arg) + page
                        )
                        self.assertEqual(
                            len(response.context['page_obj']), posts
                        )
