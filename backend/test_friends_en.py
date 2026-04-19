"""Test friends system"""
from django.contrib.auth import get_user_model
from api.models import Friendship, FriendRequest, SharedWithFriend, FriendComment

User = get_user_model()

print('\n=== Friends System Database Check ===\n')

print('Models loaded:')
print('  - Friendship model: OK')
print('  - FriendRequest model: OK')
print('  - SharedWithFriend model: OK')
print('  - FriendComment model: OK')

print(f'\nCurrent statistics:')
print(f'  - Total users: {User.objects.count()}')
print(f'  - Friendships: {Friendship.objects.count()}')
print(f'  - Friend requests: {FriendRequest.objects.count()}')
print(f'  - Shares: {SharedWithFriend.objects.count()}')
print(f'  - Comments: {FriendComment.objects.count()}')

print('\n=== Check Complete ===\n')
