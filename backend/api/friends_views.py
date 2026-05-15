from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .views import error_response
from .models import (
    FriendComment,
    FriendRequest,
    Friendship,
    MoodNote,
    SharedWithFriend,
)
from .serializers import (
    FriendCommentSerializer,
    FriendRequestSerializer,
    FriendshipSerializer,
    SharedWithFriendDetailSerializer,
    SharedWithFriendSerializer,
    UserSearchSerializer,
)
from .services.friends_service import (
    accept_friend_request,
    cancel_friend_request,
    add_comment_to_share,
    get_friend_activity,
    reject_friend_request,
    remove_friendship,
    send_friend_request,
    share_note_with_friends,
)

User = get_user_model()


# ============ Friend Management Views ============


class FriendListView(generics.ListAPIView):
    """GET /api/friends/ - 取得好友列表"""

    serializer_class = FriendshipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Count, Q, Subquery, OuterRef, IntegerField
        from django.db.models.functions import Coalesce
        from .models import JournalStreak, MoodNote
        # Annotate per-friend streak + total entries to kill the per-row
        # queries in FriendshipSerializer (audit 2026-05-15 N+1 fix).
        streak_subq = JournalStreak.objects.filter(user=OuterRef('friend')).values('current_streak')[:1]
        return (
            Friendship.objects.filter(user=self.request.user)
            .select_related('friend')
            .annotate(
                _friend_streak=Coalesce(Subquery(streak_subq, output_field=IntegerField()), 0),
                _friend_total_entries=Count(
                    'friend__notes',
                    filter=Q(friend__notes__is_deleted=False),
                    distinct=True,
                ),
            )
        )


class UserSearchView(APIView):
    """POST /api/friends/search/ - 搜尋用戶"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        query = request.data.get('query', '').strip()

        if len(query) < 2:
            return error_response(
                'friends.query_too_short',
                'Search query must be at least 2 characters',
                400,
            )

        # 搜尋用戶（排除自己）
        users = User.objects.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        ).exclude(id=request.user.id)[:20]

        serializer = UserSearchSerializer(users, many=True, context={'request': request})
        return Response({'users': serializer.data})


class FriendRequestCreateView(APIView):
    """POST /api/friends/requests/ - 發送好友請求"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        to_user_id = request.data.get('to_user_id')
        message = request.data.get('message', '')

        if not to_user_id:
            return error_response(
                'friends.to_user_id_required', 'to_user_id is required', 400,
            )

        # 檢查目標用戶是否存在
        try:
            to_user = User.objects.get(id=to_user_id)
        except User.DoesNotExist:
            return error_response('friends.user_not_found', 'User not found', 404)

        # 不能發給自己
        if to_user == request.user:
            return error_response('friends.cannot_self_request', 'Cannot send friend request to yourself', 400)

        try:
            friend_request = send_friend_request(request.user, to_user, message)
            serializer = FriendRequestSerializer(friend_request)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return error_response('friends.action_failed', str(e), 400)


class ReceivedFriendRequestsView(generics.ListAPIView):
    """GET /api/friends/requests/received/ - 收到的好友請求"""

    serializer_class = FriendRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FriendRequest.objects.filter(
            to_user=self.request.user, status='pending'
        ).select_related('from_user')


class SentFriendRequestsView(generics.ListAPIView):
    """GET /api/friends/requests/sent/ - 發送的好友請求"""

    serializer_class = FriendRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FriendRequest.objects.filter(from_user=self.request.user).select_related(
            'to_user'
        )


class AcceptFriendRequestView(APIView):
    """POST /api/friends/requests/{id}/accept/ - 接受好友請求"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            friend_request = accept_friend_request(pk, request.user)
            serializer = FriendRequestSerializer(friend_request)
            return Response(serializer.data)
        except ValueError as e:
            return error_response('friends.action_failed', str(e), 400)


class RejectFriendRequestView(APIView):
    """POST /api/friends/requests/{id}/reject/ - 拒絕好友請求"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            friend_request = reject_friend_request(pk, request.user)
            serializer = FriendRequestSerializer(friend_request)
            return Response(serializer.data)
        except ValueError as e:
            return error_response('friends.action_failed', str(e), 400)


class CancelFriendRequestView(APIView):
    """DELETE /api/friends/requests/{id}/ - 撤回自己發出的好友請求"""

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            cancel_friend_request(pk, request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return error_response('friends.action_failed', str(e), 400)


class RemoveFriendView(APIView):
    """DELETE /api/friends/{friend_id}/ - 解除好友關係"""

    permission_classes = [IsAuthenticated]

    def delete(self, request, friend_id):
        try:
            friend = User.objects.get(id=friend_id)
        except User.DoesNotExist:
            return error_response('friends.user_not_found', 'User not found', 404)

        # 檢查是否為好友
        if not Friendship.objects.filter(user=request.user, friend=friend).exists():
            return error_response('friends.not_friends', 'Not friends with this user', 400)

        remove_friendship(request.user, friend)
        return Response({'message': 'Friend removed successfully'}, status=status.HTTP_200_OK)


# ============ Note Sharing Views ============


class ShareNoteWithFriendsView(APIView):
    """POST /api/friends/share-note/ - 分享日記給好友"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        note_id = request.data.get('note_id')
        friend_ids = request.data.get('friend_ids', [])

        if not note_id:
            return error_response('friends.note_id_required', 'note_id is required', 400)

        if not friend_ids or not isinstance(friend_ids, list):
            return error_response('friends.friend_ids_required', 'friend_ids must be a non-empty list', 400)

        # 檢查日記是否存在且屬於當前用戶
        try:
            note = MoodNote.objects.get(id=note_id, user=request.user, is_deleted=False)
        except MoodNote.DoesNotExist:
            return error_response('friends.note_not_found', 'Note not found', 404)

        # 分享給好友
        shares_created = share_note_with_friends(note, friend_ids)

        return Response(
            {
                'message': f'Note shared with {len(shares_created)} friend(s)',
                'shares_created': len(shares_created),
            },
            status=status.HTTP_201_CREATED,
        )


class UnshareNoteView(APIView):
    """DELETE /api/friends/share/{share_id}/ - 撤銷分享"""

    permission_classes = [IsAuthenticated]

    def delete(self, request, share_id):
        try:
            share = SharedWithFriend.objects.get(id=share_id, shared_by=request.user)
            share.delete()
            return Response(
                {'message': 'Share removed successfully'}, status=status.HTTP_200_OK
            )
        except SharedWithFriend.DoesNotExist:
            return error_response('friends.share_not_found', 'Share not found', 404)


class SharedWithMeView(generics.ListAPIView):
    """GET /api/friends/shared-with-me/ - 好友分享給我的日記"""

    serializer_class = SharedWithFriendSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Count
        return (
            SharedWithFriend.objects.filter(shared_with=self.request.user)
            .select_related('note', 'shared_by')
            .annotate(_comment_count=Count('comments'))
        )


class SharedByMeView(generics.ListAPIView):
    """GET /api/friends/shared-by-me/ - 我分享的日記"""

    serializer_class = SharedWithFriendSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Count
        return (
            SharedWithFriend.objects.filter(shared_by=self.request.user)
            .select_related('note', 'shared_with')
            .annotate(_comment_count=Count('comments'))
        )


class SharedNoteDetailView(generics.RetrieveAPIView):
    """GET /api/friends/share/{share_id}/detail/ - 查看分享日記詳情"""

    serializer_class = SharedWithFriendDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 只能查看分享給自己的或自己分享的日記
        return SharedWithFriend.objects.filter(
            Q(shared_with=self.request.user) | Q(shared_by=self.request.user)
        ).select_related('note', 'shared_by', 'shared_with')


# ============ Comment Views ============


class AddCommentView(APIView):
    """POST /api/friends/share/{share_id}/comment/ - 對分享日記留言"""

    permission_classes = [IsAuthenticated]

    def post(self, request, share_id):
        content = request.data.get('content', '').strip()

        if not content:
            return error_response(
                'friends.comment_required', 'Comment content is required', 400,
            )

        try:
            share = SharedWithFriend.objects.get(id=share_id)
        except SharedWithFriend.DoesNotExist:
            return error_response('friends.share_not_found', 'Share not found', 404)

        try:
            comment = add_comment_to_share(share, request.user, content)
            serializer = FriendCommentSerializer(comment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return error_response('friends.forbidden', str(e), 403)


class CommentListView(generics.ListAPIView):
    """GET /api/friends/share/{share_id}/comments/ - 取得留言列表"""

    serializer_class = FriendCommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        share_id = self.kwargs.get('share_id')

        # 檢查是否有權限查看（必須是分享者或被分享者）
        try:
            share = SharedWithFriend.objects.get(id=share_id)
            if share.shared_by != self.request.user and share.shared_with != self.request.user:
                return FriendComment.objects.none()
        except SharedWithFriend.DoesNotExist:
            return FriendComment.objects.none()

        return FriendComment.objects.filter(share_id=share_id).select_related('commenter')


class DeleteCommentView(APIView):
    """DELETE /api/friends/comment/{comment_id}/ - 刪除自己的留言"""

    permission_classes = [IsAuthenticated]

    def delete(self, request, comment_id):
        try:
            comment = FriendComment.objects.get(id=comment_id, commenter=request.user)
            comment.delete()
            return Response(
                {'message': 'Comment deleted successfully'}, status=status.HTTP_200_OK
            )
        except FriendComment.DoesNotExist:
            return error_response('friends.comment_not_found', 'Comment not found', 404)


# ============ Activity Views ============


class FriendActivityView(APIView):
    """GET /api/friends/activity/ - 好友動態"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        hours = request.query_params.get('hours', 24)
        try:
            hours = int(hours)
        except ValueError:
            hours = 24

        activities = get_friend_activity(request.user, hours=hours)
        return Response({'activities': activities})


class LeaderboardView(APIView):
    """GET /api/friends/leaderboard/ — current_streak ranking of self + friends.

    Returns a list sorted by current_streak (desc) so the frontend can render
    a comparison bar. The response includes ``is_self`` so the user's row can
    be highlighted, and ``total_entries`` for a richer comparison.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import Friendship, JournalStreak, MoodNote

        # Collect (user, is_self) pairs.
        rows = [(request.user, True)]
        for fs in Friendship.objects.filter(user=request.user).select_related('friend'):
            rows.append((fs.friend, False))

        user_ids = [u.id for u, _ in rows]

        # Bulk-fetch streak rows + entry counts to keep this O(1) queries.
        streaks = {
            s.user_id: s for s in JournalStreak.objects.filter(user_id__in=user_ids)
        }
        from django.db.models import Count
        entry_counts = dict(
            MoodNote.objects.filter(user_id__in=user_ids, is_deleted=False)
                            .values('user_id')
                            .annotate(c=Count('id'))
                            .values_list('user_id', 'c')
        )

        results = []
        for user, is_self in rows:
            streak = streaks.get(user.id)
            results.append({
                'user_id': user.id,
                'username': user.username,
                'avatar': user.avatar.url if getattr(user, 'avatar', None) else None,
                'is_self': is_self,
                'current_streak': streak.current_streak if streak else 0,
                'longest_streak': streak.longest_streak if streak else 0,
                'total_entries': entry_counts.get(user.id, 0),
                'last_entry_date': streak.last_entry_date.isoformat() if streak and streak.last_entry_date else None,
            })

        results.sort(key=lambda r: (-r['current_streak'], -r['total_entries'], r['username']))
        for i, r in enumerate(results, start=1):
            r['rank'] = i

        return Response({'leaderboard': results, 'count': len(results)})


# drf_spectacular schema policy — see backend/api/views.py for rationale.
_UNDOCUMENTED_VIEWS = [
    'AcceptFriendRequestView', 'AddCommentView', 'DeleteCommentView',
    'FriendActivityView', 'FriendRequestCreateView', 'LeaderboardView',
    'RejectFriendRequestView', 'RemoveFriendView', 'ShareNoteWithFriendsView',
    'UnshareNoteView', 'UserSearchView',
]
for _name in _UNDOCUMENTED_VIEWS:
    _cls = globals().get(_name)
    if _cls is not None:
        _cls.schema = None
