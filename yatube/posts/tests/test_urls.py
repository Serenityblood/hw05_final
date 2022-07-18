from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from http import HTTPStatus

from ..models import Group, Post, User

User = get_user_model()


class StaticURLTests(TestCase):
    def test_homepage(self):
        response = self.client.get('/')
        self.assertEqual(
            response.status_code, HTTPStatus.OK, 'Main page falls'
        )


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='tester')
        cls.user2 = User.objects.create_user(username='tester2')
        cls.user3 = User.objects.create_user(username='tester3')
        cls.group = Group.objects.create(
            title='Test title',
            slug='test',
            description='Test description'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Test text' * 10,
            group=cls.group,
        )

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.just_client = Client()
        self.just_client.force_login(self.user2)
        self.names_args = (
            ('posts:main_page', None),
            ('posts:group_posts_page', (self.group.slug,)),
            ('posts:profile', (self.user.username,)),
            ('posts:post_detail', (self.post.pk,)),
            ('posts:post_edit', (self.post.pk,)),
            ('posts:post_create', None),
            ('posts:add_comment', (self.post.pk,)),
            ('posts:follow_index', None),
            ('posts:profile_follow', (self.user3.username,)),
            ('posts:profile_unfollow', (self.user3.username,))
        )

    def test_hardcore_urls_names_match(self):
        """Сравниваем реверс нейм и хардкор URL"""
        name_args_urls = (
            (
                'posts:main_page',
                None,
                '/'
            ), (
                'posts:group_posts_page',
                (self.group.slug,),
                f'/group/{self.group.slug}/'
            ), (
                'posts:profile',
                (self.user.username,),
                f'/profile/{self.user.username}/'
            ), (
                'posts:post_detail',
                (self.post.pk,),
                f'/posts/{self.post.pk}/'
            ), (
                'posts:post_edit',
                (self.post.pk,),
                f'/posts/{self.post.pk}/edit/'
            ), (
                'post:post_create',
                None,
                '/create/'
            ), (
                'posts:follow_index',
                None,
                '/follow/'
            ), (
                'posts:profile_follow',
                (self.user3.username,),
                f'/profile/{self.user3.username}/follow/'
            ), (
                'posts:profile_unfollow',
                (self.user3.username,),
                f'/profile/{self.user3.username}/unfollow/'
            ), (
                'posts:add_comment',
                (self.post.pk,),
                f'/posts/{self.post.pk}/comment/'
            )
        )
        for name, arg, url in name_args_urls:
            with self.subTest(url=url):
                self.assertEqual(reverse(name, args=arg), url)

    def test_non_authorized_users_urls(self):
        """Доступ гостей к страницам"""
        for name, arg in self.names_args:
            with self.subTest(name=name):
                response = self.client.get(reverse(name, args=arg))
                if name in (
                    'posts:post_edit', 'posts:post_create',
                    'posts:add_comment', 'posts:follow_index',
                    'posts:profile_follow', 'posts:profile_unfollow'
                ):
                    login = reverse('users:login')
                    url_name = reverse(name, args=arg)
                    self.assertRedirects(response, f'{login}?next={url_name}')
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unexsting_page_check(self):
        """Доступ к несуществующей странице"""
        response = self.client.get('/unexisting_page/')
        self.assertEquals(response.status_code, HTTPStatus.NOT_FOUND)

    def test_author_user_urls(self):
        """Доступ автора к страницам"""
        for name, arg in self.names_args:
            with self.subTest(name=name):
                response = self.authorized_client.get(reverse(name, args=arg))
                if name == 'posts:add_comment':
                    self.assertRedirects(
                        response, reverse(
                            'posts:post_detail', args=arg
                        )
                    )
                elif name in (
                    'posts:profile_follow', 'posts:profile_unfollow'
                ):
                    self.assertRedirects(
                        response, reverse(
                            'posts:profile', args=arg
                        )
                    )
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_authorized_users_urls(self):
        """Доступ авторизванного пользователя к страницам"""
        for name, arg in self.names_args:
            with self.subTest(name=name):
                response = self.just_client.get(reverse(name, args=arg))
                if name == 'posts:post_edit':
                    self.assertRedirects(response, reverse(
                        'posts:post_detail', args=arg
                    )
                    )
                elif name == 'posts:add_comment':
                    self.assertRedirects(
                        response, reverse(
                            'posts:post_detail', args=arg
                        )
                    )
                elif name in (
                    'posts:profile_follow', 'posts:profile_unfollow'
                ):
                    self.assertRedirects(
                        response, reverse(
                            'posts:profile', args=arg
                        )
                    )
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_template_check(self):
        """Тест шаблонов и реверснеймов"""
        names_templates = (
            (
                'posts:main_page',
                None,
                'posts/index.html'
            ), (
                'posts:group_posts_page',
                (self.group.slug,),
                'posts/group_list.html'
            ), (
                'posts:profile',
                (self.user.username,),
                'posts/profile.html'
            ), (
                'posts:post_detail',
                (self.post.pk,),
                'posts/post_detail.html'
            ), (
                'posts:post_edit',
                (self.post.pk,),
                'posts/create_post.html'
            ), (
                'posts:post_create',
                None,
                'posts/create_post.html'
            ), (
                'posts:follow_index',
                None,
                'posts/follow.html'
            )
        )
        for name, arg, template in names_templates:
            with self.subTest(name=name):
                response = self.authorized_client.get(reverse(name, args=arg))
                self.assertTemplateUsed(response, template)
