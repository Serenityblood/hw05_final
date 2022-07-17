from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page

from .forms import PostForm, CommentForm
from .models import Comment, Follow, Group, Post, User
from .utils import paginator_func


@cache_page(20, key_prefix='index_page')
def index(request):
    posts_list = Post.objects.select_related('author', 'group').all()
    page_obj = paginator_func(request, posts_list)
    context = {
        'page_obj': page_obj
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts_list = group.posts.select_related('author').all()
    page_obj = paginator_func(request, posts_list)
    context = {
        'group': group,
        'page_obj': page_obj
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    author_posts = author.posts.select_related('group')
    page_obj = paginator_func(request, author_posts)
    context = {
        'author': author,
        'page_obj': page_obj
    }
    if request.user.is_authenticated:
        if Follow.objects.filter(
            user=request.user
        ).filter(
            author=author
        ).exists():
            context['following'] = True
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    comments = Comment.objects.select_related('post').filter(post=post)
    form = CommentForm()
    context = {
        'post': post,
        'form': form,
        'comments': comments
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if not form.is_valid():
        return render(request, 'posts/create_post.html', {'form': form})
    post = form.save(False)
    post.author = request.user
    post.save()
    return redirect('posts:profile', username=request.user.username)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id=post.pk)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if not form.is_valid():
        return render(request, 'posts/create_post.html', {'form': form})
    form.save()
    return redirect('posts:post_detail', post_id=post.pk)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    following = Follow.objects.filter(user=request.user)
    authors = []
    for author in following:
        authors.append(author.author)
    posts_list = Post.objects.filter(
        author__in=authors
    )
    page_obj = paginator_func(request, posts_list)
    context = {
        'page_obj': page_obj
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    user = request.user
    author = User.objects.get(username=username)
    if user != author and not Follow.objects.filter(
        user=user,
        author=author
    ):
        Follow.objects.create(
            user=request.user,
            author=User.objects.get(username=username)
        )
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    Follow.objects.get(
        user=request.user,
        author=User.objects.get(username=username)
    ).delete()
    return redirect('posts:profile', username=username)
