import tempfile
import shutil

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from http import HTTPStatus

from ..models import Comment, Group, Post, User

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CreatinoFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='tester')
        cls.another_user = User.objects.create_user(username='tester2')
        cls.group = Group.objects.create(
            title='Test title',
            slug='test',
            description='Test description',
        )
        cls.group_edit = Group.objects.create(
            title='Test title edit',
            slug='test-edit',
            description='Test description edit',
        )
        cls.post = Post.objects.create(
            text='Test text',
            group=cls.group,
            author=cls.user,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.another_client = Client()
        self.another_client.force_login(self.another_user)

    def test_valid_form_creates_post(self):
        """Валидная форма создаёт пост"""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Text form',
            'group': self.group.id,
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        post_created = Post.objects.first()
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(post_created.text, form_data['text'])
        self.assertEqual(post_created.group, self.group)
        self.assertEqual(post_created.author, self.user)
        self.assertEqual(post_created.image, 'posts/small.gif')
        self.assertRedirects(response, reverse(
            'posts:profile', args=(post_created.author,)
        )
        )

    def test_valid_form_edit_post(self):
        """Валидная форма редактирует пост"""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Text edit',
            'group': self.group_edit.id,
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit', args=(self.post.pk,)
            ),
            data=form_data,
            follow=True
        )
        post_edit = Post.objects.first()
        self.assertRedirects(response, reverse(
            'posts:post_detail', args=(post_edit.pk,)
        )
        )
        self.assertEqual(post_edit.author, self.user)
        self.assertEqual(post_edit.text, form_data['text'])
        self.assertEqual(post_edit.group, self.group_edit)
        group_response = self.authorized_client.get(
            reverse(
                'posts:group_posts_page', args=(self.group.slug,)
            )
        )
        self.assertEqual(group_response.status_code, HTTPStatus.OK)
        self.assertEqual(
            group_response.context['page_obj'].object_list.count(),
            0
        )
        self.assertEqual(Post.objects.count(), post_count)

    def test_guest_cant_create_post(self):
        """Гости не могут создавать посты"""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Guest text',
            'group': self.group.id,
        }
        self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count)

    def test_only_auth_user_can_comment(self):
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Test comment'
        }
        self.client.post(
            reverse('posts:add_comment', args=(self.post.pk,)),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count)

    def test_valid_form_creates_comment(self):
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Test comment'
        }
        self.another_client.post(
            reverse('posts:add_comment', args=(self.post.pk,)),
            data=form_data,
            follow=True
        )
        comment = Comment.objects.first()
        self.assertEqual(
            Comment.objects.count(), comments_count + 1
        )
        self.assertEqual(comment.post, self.post)
        self.assertEqual(comment.author, self.another_user)
        self.assertEqual(comment.text, form_data['text'])
