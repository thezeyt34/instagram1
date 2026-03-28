import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

from .forms import (
    CustomUserRegisterForm,
    CustomLoginForm,
    ProfileUpdateForm,
    PostForm
)

from .models import (
    Post, CustomUser, Conversation, Message,
    Follow, Like, Comment, Story, Saved
)


@login_required
def home_view(request):
    followed_user_ids = Follow.objects.filter(
        follower=request.user
    ).values_list('following_id', flat=True)

    followed_users = CustomUser.objects.filter(id__in=followed_user_ids)

    active_stories = Story.objects.filter(
        user__in=followed_users,
        expires_at__gt=timezone.now()
    )

    user_active_stories = Story.objects.filter(
        user=request.user,
        expires_at__gt=timezone.now()
    )

    all_active_stories = (active_stories | user_active_stories).order_by('-created_at')

    posts = Post.objects.all().order_by('-created_at')

    return render(request, "home.html", {
        "stories": all_active_stories,
        "posts": posts
    })


@login_required
def add_story_view(request):
    if request.method == "POST":
        image = request.FILES.get("image")
        video = request.FILES.get("video")

        if not image and not video:
            return render(request, "add_story.html", {
                "error": "Загрузи фото или видео для сторис."
            })

        Story.objects.create(
            user=request.user,
            image=image if image else None,
            video=video if video else None,
            expires_at=timezone.now() + timezone.timedelta(hours=24)
        )
        return redirect("home")

    return render(request, "add_story.html")


@login_required
def view_story(request, story_id):
    story = get_object_or_404(
        Story,
        id=story_id,
        expires_at__gt=timezone.now()
    )

    return render(request, "view_story.html", {
        "story": story
    })


def post_detail_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    post.views += 1
    post.save()

    if request.user.is_authenticated:
        followed_user_ids = request.user.following_rel.all().values_list('following_id', flat=True)
        user_followings = CustomUser.objects.filter(id__in=followed_user_ids)
    else:
        user_followings = CustomUser.objects.none()

    return render(request, 'post_detail.html', {
        'post': post,
        'user_followings': user_followings
    })


def search_users_view(request):
    query = request.GET.get('q', '').strip()
    users_data = []

    if query:
        users = CustomUser.objects.filter(username__icontains=query)[:8]

        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'bio': user.bio if user.bio else '',
                'avatar': user.avatar.url if user.avatar else '',
                'profile_url': f'/user/{user.username}/'
            })

    return JsonResponse({'users': users_data})


def register_view(request):
    if request.method == 'POST':
        form = CustomUserRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('profile')
    else:
        form = CustomUserRegisterForm()

    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('profile')
    else:
        form = CustomLoginForm()

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def profile_user_view(request, username):
    profile_user = get_object_or_404(CustomUser, username=username)
    user_posts = Post.objects.filter(author=profile_user).order_by('-created_at')

    is_following = Follow.objects.filter(
        follower=request.user,
        following=profile_user
    ).exists()

    followers = Follow.objects.filter(following=profile_user).select_related('follower')
    following = Follow.objects.filter(follower=profile_user).select_related('following')

    followers_count = followers.count()
    following_count = following.count()

    return render(request, 'user_profile.html', {
        'user_profile': profile_user,
        'user_posts': user_posts,
        'is_following': is_following,
        'followers_count': followers_count,
        'following_count': following_count,
        'followers': followers,
        'following': following,
    })


@login_required
def profile_view(request):
    user_posts = Post.objects.filter(author=request.user).order_by('-created_at')

    followers_count = Follow.objects.filter(following=request.user).count()
    following_count = Follow.objects.filter(follower=request.user).count()

    return render(request, 'profile.html', {
        'user_obj': request.user,
        'user_posts': user_posts,
        'followers_count': followers_count,
        'following_count': following_count,
    })


@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'edit_profile.html', {'form': form})


@login_required
def add_post_view(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('home')
    else:
        form = PostForm()

    return render(request, 'add_post.html', {'form': form})


@login_required
def chat_view(request, user_id):
    other_user = get_object_or_404(CustomUser, id=user_id)

    conversation = Conversation.objects.filter(users=request.user).filter(users=other_user).first()

    if not conversation:
        conversation = Conversation.objects.create()
        conversation.users.add(request.user, other_user)

    if request.method == "POST":
        text = request.POST.get("text")
        if text:
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                text=text
            )
            return redirect("chat", user_id=user_id)

    conversation.messages.filter(
        is_read=False
    ).exclude(sender=request.user).update(is_read=True)

    messages = conversation.messages.all().order_by("created_at")

    conversations = Conversation.objects.filter(users=request.user)

    chats = []
    for conv in conversations:
        user = conv.users.exclude(id=request.user.id).first()

        unread = conv.messages.filter(
            is_read=False
        ).exclude(sender=request.user).count()

        chats.append({
            "user": user,
            "unread": unread
        })

    return render(request, "chat.html", {
        "messages": messages,
        "receiver": other_user,
        "chats": chats
    })


@login_required
def chat_list_view(request):
    conversations = Conversation.objects.filter(users=request.user)

    chats = []
    for conv in conversations:
        user = conv.users.exclude(id=request.user.id).first()
        unread = conv.messages.filter(is_read=False).exclude(sender=request.user).count()

        chats.append({
            "user": user,
            "unread": unread
        })

    return render(request, "chat_list.html", {
        "chats": chats
    })


@login_required
def follow_toggle(request, username):
    target_user = get_object_or_404(CustomUser, username=username)

    if target_user == request.user:
        return redirect("profile")

    follow = Follow.objects.filter(
        follower=request.user,
        following=target_user
    ).first()

    if follow:
        follow.delete()
    else:
        Follow.objects.create(
            follower=request.user,
            following=target_user
        )

    return redirect("user_profile", username=username)


@login_required
def follow_toggle_ajax(request, user_id):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)

    target_user = get_object_or_404(CustomUser, id=user_id)

    if target_user == request.user:
        return JsonResponse({"success": False, "error": "Нельзя подписаться на себя"}, status=400)

    follow = Follow.objects.filter(
        follower=request.user,
        following=target_user
    ).first()

    if follow:
        follow.delete()
        following = False
    else:
        Follow.objects.create(
            follower=request.user,
            following=target_user
        )
        following = True

    return JsonResponse({
        "success": True,
        "following": following
    })


@login_required
def like_toggle_ajax(request, post_id):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)

    post = get_object_or_404(Post, id=post_id)
    like = Like.objects.filter(user=request.user, post=post).first()

    if like:
        like.delete()
        liked = False
    else:
        Like.objects.create(user=request.user, post=post)
        liked = True

    likes_count = Like.objects.filter(post=post).count()

    return JsonResponse({
        "success": True,
        "liked": liked,
        "likes_count": likes_count
    })


@login_required
def add_comment_ajax(request, post_id):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)

    try:
        data = json.loads(request.body)
        text = data.get("text", "").strip()
    except Exception:
        return JsonResponse({"success": False, "error": "Неверный JSON"}, status=400)

    if not text:
        return JsonResponse({"success": False, "error": "Пустой комментарий"}, status=400)

    post = get_object_or_404(Post, id=post_id)
    comment = Comment.objects.create(
        user=request.user,
        post=post,
        text=text
    )

    comments_count = Comment.objects.filter(post=post).count()

    return JsonResponse({
        "success": True,
        "comment_id": comment.id,
        "text": comment.text,
        "username": request.user.username,
        "comments_count": comments_count
    })


@login_required
def save_toggle_ajax(request, post_id):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)

    post = get_object_or_404(Post, id=post_id)
    saved_obj = Saved.objects.filter(user=request.user, post=post).first()

    if saved_obj:
        saved_obj.delete()
        saved = False
    else:
        Saved.objects.create(user=request.user, post=post)
        saved = True

    return JsonResponse({
        "success": True,
        "saved": saved
    })


@login_required
def send_post_dm(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        post_id = data.get('post_id')
        users_ids = data.get('users', [])

        post = Post.objects.get(id=post_id)

        for uid in users_ids:
            recipient = CustomUser.objects.get(id=uid)

            conv = Conversation.objects.filter(users=request.user).filter(users=recipient).first()
            if not conv:
                conv = Conversation.objects.create()
                conv.users.add(request.user, recipient)

            if post.image:
                Message.objects.create(
                    conversation=conv,
                    sender=request.user,
                    image=post.image,
                    text=post.title or ""
                )
            elif post.video:
                Message.objects.create(
                    conversation=conv,
                    sender=request.user,
                    video=post.video,
                    text=post.title or ""
                )
            else:
                post_url = request.build_absolute_uri(post.get_absolute_url()) if hasattr(post, 'get_absolute_url') else f"/post/{post.id}/"
                Message.objects.create(
                    conversation=conv,
                    sender=request.user,
                    text=f"{post.title} - {post_url}"
                )

        return JsonResponse({'success': True})

    return JsonResponse({'success': False})


@login_required
def explore_view(request):
    posts = (
        Post.objects
        .select_related('author')
        .filter(video__isnull=False)
        .exclude(video='')
        .order_by('-created_at')
    )

    active_stories = Story.objects.filter(
        expires_at__gt=timezone.now()
    ).select_related('user').order_by('-created_at')

    liked_post_ids = set(
        Like.objects.filter(user=request.user).values_list('post_id', flat=True)
    )
    saved_post_ids = set(
        Saved.objects.filter(user=request.user).values_list('post_id', flat=True)
    )
    following_user_ids = set(
        Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    )

    context = {
        'posts': posts,
        'stories': active_stories,
        'liked_post_ids': liked_post_ids,
        'saved_post_ids': saved_post_ids,
        'following_user_ids': following_user_ids,
    }
    return render(request, 'explore.html', context)


@login_required
def reels_view(request):
    posts = (
        Post.objects
        .select_related('author')
        .filter(video__isnull=False)
        .exclude(video='')
        .order_by('-created_at')
    )

    liked_post_ids = set(
        Like.objects.filter(user=request.user).values_list('post_id', flat=True)
    )
    saved_post_ids = set(
        Saved.objects.filter(user=request.user).values_list('post_id', flat=True)
    )
    following_user_ids = set(
        Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    )

    context = {
        'posts': posts,
        'liked_post_ids': liked_post_ids,
        'saved_post_ids': saved_post_ids,
        'following_user_ids': following_user_ids,
    }
    return render(request, 'reels.html', context)

@login_required
def saved_posts_view(request):
    saved_posts = Post.objects.filter(saved__user=request.user).order_by('-saved__created_at')
    return render(request, 'saved.html', {'posts': saved_posts})