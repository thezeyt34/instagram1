from django.urls import path
from . import views

urlpatterns = [
    # auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # home
    path('', views.home_view, name='home'),
    path('search-users/', views.search_users_view, name='search_users'),

    # profile
    path('user/<str:username>/', views.profile_user_view, name='user_profile'),
    path('profile/', views.profile_view, name='profile'),
    path('follow/<str:username>/', views.follow_toggle, name='follow_toggle'),

    # ajax follow
    path('ajax/follow/<int:user_id>/', views.follow_toggle_ajax, name='follow_toggle_ajax'),

    # post
    path('edit_profile/', views.edit_profile_view, name='edit_profile'),
    path('add_post/', views.add_post_view, name='add_post'),
    path('add_story/', views.add_story_view, name='add_story'),
    path('story/<int:story_id>/', views.view_story, name='view_story'),
    path('post/<int:post_id>/', views.post_detail_view, name='post_detail'),
    path('send_post_dm/', views.send_post_dm, name='send_post_dm'),

    # explore / reels
    path('explore/', views.explore_view, name='explore'),
    path('reels/', views.reels_view, name='reels'),

    # ajax like / comment / save
    path('like/<int:post_id>/', views.like_toggle_ajax, name='like_toggle_ajax'),
    path('comment/<int:post_id>/', views.add_comment_ajax, name='add_comment_ajax'),
    path('save/<int:post_id>/', views.save_toggle_ajax, name='save_toggle_ajax'),

    # chat
    path("chat/<int:user_id>/", views.chat_view, name="chat"),
    path("chats/", views.chat_list_view, name="chat_list"),
    path('saved/', views.saved_posts_view, name='saved_posts'),
]