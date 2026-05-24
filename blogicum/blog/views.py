from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from . import models
from .forms import CommentForm, PostForm, RegistrationForm, UserEditForm

User = get_user_model()

POSTS_PER_PAGE = 10


def _published_posts():
    return (
        models.Post.objects
        .select_related('category', 'author', 'location')
        .filter(
            pub_date__lte=timezone.now(),
            is_published=True,
            category__is_published=True,
        )
        .order_by('-pub_date')
        .annotate(comment_count=Count('comments'))
    )


def _paginate(request, queryset):
    paginator = Paginator(queryset, POSTS_PER_PAGE)
    return paginator.get_page(request.GET.get('page'))


def index(request):
    return render(request, 'blog/index.html', {
        'page_obj': _paginate(request, _published_posts()),
    })


def category_posts(request, category_slug):
    category = get_object_or_404(
        models.Category,
        slug=category_slug,
        is_published=True,
    )
    post_list = (
        _published_posts()
        .filter(category=category)
    )
    return render(request, 'blog/category.html', {
        'category': category,
        'page_obj': _paginate(request, post_list),
    })


def post_detail(request, post_id):
    post = get_object_or_404(models.Post, pk=post_id)
    if request.user != post.author:
        post = get_object_or_404(
            models.Post,
            pk=post_id,
            pub_date__lte=timezone.now(),
            is_published=True,
            category__is_published=True,
        )
    comments = post.comments.select_related('author')
    return render(request, 'blog/detail.html', {
        'post': post,
        'form': CommentForm(),
        'comments': comments,
    })


def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    if request.user == profile_user:
        post_list = (
            models.Post.objects
            .select_related('category', 'author', 'location')
            .filter(author=profile_user)
            .order_by('-pub_date')
            .annotate(comment_count=Count('comments'))
        )
    else:
        post_list = _published_posts().filter(author=profile_user)
    return render(request, 'blog/profile.html', {
        'profile': profile_user,
        'page_obj': _paginate(request, post_list),
    })


@login_required
def edit_profile(request):
    form = UserEditForm(request.POST or None, instance=request.user)
    if form.is_valid():
        form.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/user.html', {'form': form})


def register(request):
    form = RegistrationForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('blog:index')
    return render(request, 'registration/registration_form.html', {'form': form})


@login_required
def create_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(models.Post, pk=post_id)
    if request.user != post.author:
        return redirect('blog:post_detail', post_id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(models.Post, pk=post_id)
    if request.user != post.author:
        return redirect('blog:post_detail', post_id=post_id)
    form = PostForm(instance=post)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:index')
    return render(request, 'blog/create.html', {'form': form})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(models.Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(
        models.Comment, pk=comment_id, post_id=post_id
    )
    if request.user != comment.author:
        return redirect('blog:post_detail', post_id=post_id)
    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', {
        'form': form,
        'comment': comment,
    })


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(
        models.Comment, pk=comment_id, post_id=post_id
    )
    if request.user != comment.author:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', {'comment': comment})
