from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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
        return Friendship.objects.filter(user=self.request.user).select_related('friend')


class UserSearchView(APIView):
    """POST /api/friends/search/ - 搜尋用戶"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        query = request.data.get('query', '').strip()

        if len(query) < 2:
            return Response(
                {'error': 'Search query must be at least 2 characters'},
                status=status.HTTP_400_BAD_REQUEST,
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
            return Response(
                {'error': 'to_user_id is required'}, status=status.HTTP_400_BAD_REQUEST
            )

        # 檢查目標用戶是否存在
        try:
            to_user = User.objects.get(id=to_user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # 不能發給自己
        if to_user == request.user:
            return Response(
                {'error': 'Cannot send friend request to yourself'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            friend_request = send_friend_request(request.user, to_user, message)
            serializer = FriendRequestSerializer(friend_request)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RejectFriendRequestView(APIView):
    """POST /api/friends/requests/{id}/reject/ - 拒絕好友請求"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            friend_request = reject_friend_request(pk, request.user)
            serializer = FriendRequestSerializer(friend_request)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RemoveFriendView(APIView):
    """DELETE /api/friends/{friend_id}/ - 解除好友關係"""

    permission_classes = [IsAuthenticated]

    def delete(self, request, friend_id):
        try:
            friend = User.objects.get(id=friend_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # 檢查是否為好友
        if not Friendship.objects.filter(user=request.user, friend=friend).exists():
            return Response(
                {'error': 'Not friends with this user'}, status=status.HTTP_400_BAD_REQUEST
            )

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
            return Response(
                {'error': 'note_id is required'}, status=status.HTTP_400_BAD_REQUEST
            )

        if not friend_ids or not isinstance(friend_ids, list):
            return Response(
                {'error': 'friend_ids must be a non-empty list'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 檢查日記是否存在且屬於當前用戶
        try:
            note = MoodNote.objects.get(id=note_id, user=request.user, is_deleted=False)
        except MoodNote.DoesNotExist:
            return Response({'error': 'Note not found'}, status=status.HTTP_404_NOT_FOUND)

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
            return Response({'error': 'Share not found'}, status=status.HTTP_404_NOT_FOUND)


class SharedWithMeView(generics.ListAPIView):
    """GET /api/friends/shared-with-me/ - 好友分享給我的日記"""

    serializer_class = SharedWithFriendSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            SharedWithFriend.objects.filter(shared_with=self.request.user)
            .select_related('note', 'shared_by')
            .prefetch_related('comments')
        )


class SharedByMeView(generics.ListAPIView):
    """GET /api/friends/shared-by-me/ - 我分享的日記"""

    serializer_class = SharedWithFriendSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            SharedWithFriend.objects.filter(shared_by=self.request.user)
            .select_related('note', 'shared_with')
            .prefetch_related('comments')
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
            return Response(
                {'error': 'Comment content is required'}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            share = SharedWithFriend.objects.get(id=share_id)
        except SharedWithFriend.DoesNotExist:
            return Response({'error': 'Share not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            comment = add_comment_to_share(share, request.user, content)
            serializer = FriendCommentSerializer(comment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)


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
            return Response({'error': 'Comment not found'}, status=status.HTTP_404_NOT_FOUND)


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
