from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from api.models import (
    FriendComment,
    FriendRequest,
    Friendship,
    JournalStreak,
    MoodNote,
    Notification,
    SharedWithFriend,
)


@transaction.atomic
def create_friendship(from_user, to_user):
    """建立雙向好友關係 — 原子操作避免單向半成品"""
    Friendship.objects.get_or_create(user=from_user, friend=to_user)
    Friendship.objects.get_or_create(user=to_user, friend=from_user)


@transaction.atomic
def remove_friendship(user, friend):
    """刪除雙向好友關係 + 相關分享 — 原子操作"""
    Friendship.objects.filter(user=user, friend=friend).delete()
    Friendship.objects.filter(user=friend, friend=user).delete()

    SharedWithFriend.objects.filter(
        Q(shared_by=user, shared_with=friend) | Q(shared_by=friend, shared_with=user)
    ).delete()


def get_friend_activity(user, hours=24):
    """取得好友動態（最近 N 小時內的新日記）。

    Bulk-fetches every friend's current_streak in one query instead of
    one-per-note (was N+1 — 100 notes from active friends → 100 streak
    lookups).
    """
    friends = list(Friendship.objects.filter(user=user).values_list('friend_id', flat=True))
    if not friends:
        return []

    cutoff_time = timezone.now() - timedelta(hours=hours)
    recent_notes = MoodNote.objects.filter(
        user_id__in=friends, created_at__gte=cutoff_time, is_deleted=False
    ).select_related('user')

    streak_by_user = dict(
        JournalStreak.objects.filter(user_id__in=friends).values_list('user_id', 'current_streak')
    )

    return [
        {
            'friend_id': note.user.id,
            'friend_username': note.user.username,
            'activity_type': 'new_entry',
            'streak_days': streak_by_user.get(note.user_id, 0),
            'timestamp': note.created_at,
            'note_id': note.id,
        }
        for note in recent_notes
    ]


def send_friend_request(from_user, to_user, message=''):
    """發送好友請求"""
    # 檢查是否已經是好友
    if Friendship.objects.filter(user=from_user, friend=to_user).exists():
        raise ValueError('Already friends')

    # 檢查是否已發送過請求
    if FriendRequest.objects.filter(from_user=from_user, to_user=to_user).exists():
        raise ValueError('Request already sent')

    # 建立好友請求
    request = FriendRequest.objects.create(
        from_user=from_user, to_user=to_user, message=message
    )

    # 發送通知
    Notification.objects.create(
        user=to_user,
        type='friend_request',
        title='新好友請求',
        message=f'{from_user.username} 想要加你為好友',
        data={'friend_request_id': request.id, 'from_user_id': from_user.id},
    )

    return request


def accept_friend_request(request_id, user):
    """接受好友請求"""
    try:
        friend_request = FriendRequest.objects.get(id=request_id, to_user=user, status='pending')
    except FriendRequest.DoesNotExist:
        raise ValueError('Friend request not found or already processed')

    # 更新請求狀態
    friend_request.status = 'accepted'
    friend_request.save()

    # 建立好友關係
    create_friendship(friend_request.from_user, friend_request.to_user)

    # 發送通知給發送者
    Notification.objects.create(
        user=friend_request.from_user,
        type='friend_accepted',
        title='好友請求已接受',
        message=f'{user.username} 接受了你的好友請求',
        data={'friend_id': user.id},
    )

    return friend_request


def reject_friend_request(request_id, user):
    """拒絕好友請求"""
    try:
        friend_request = FriendRequest.objects.get(id=request_id, to_user=user, status='pending')
    except FriendRequest.DoesNotExist:
        raise ValueError('Friend request not found or already processed')

    # 更新請求狀態
    friend_request.status = 'rejected'
    friend_request.save()

    return friend_request


def share_note_with_friends(note, friend_ids):
    """分享日記給多個好友"""
    shares_created = []

    for friend_id in friend_ids:
        # 檢查是否為好友關係
        if not Friendship.objects.filter(user=note.user, friend_id=friend_id).exists():
            continue

        # 建立分享記錄（使用 get_or_create 避免重複）
        share, created = SharedWithFriend.objects.get_or_create(
            note=note, shared_by=note.user, shared_with_id=friend_id
        )

        if created:
            shares_created.append(share)

            # 發送通知
            Notification.objects.create(
                user_id=friend_id,
                type='friend_share',
                title='好友分享日記',
                message=f'{note.user.username} 與你分享了一篇日記',
                data={'share_id': share.id, 'note_id': note.id},
            )

    return shares_created


def add_comment_to_share(share, commenter, content):
    """對分享的日記留言"""
    # 檢查是否有權限留言（必須是被分享的對象）
    if share.shared_with != commenter:
        raise ValueError('Not authorized to comment on this share')

    # 建立留言
    comment = FriendComment.objects.create(share=share, commenter=commenter, content=content)

    # 通知日記作者
    Notification.objects.create(
        user=share.shared_by,
        type='friend_comment',
        title='好友留言',
        message=f'{commenter.username} 在你分享的日記上留言了',
        data={'share_id': share.id, 'comment_id': comment.id},
    )

    return comment
