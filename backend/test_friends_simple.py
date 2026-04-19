"""
簡單測試好友系統功能
使用: python manage.py shell < test_friends_simple.py
"""
from django.contrib.auth import get_user_model
from api.models import Friendship, FriendRequest, SharedWithFriend, FriendComment

User = get_user_model()

print('\n=== 好友系統資料庫檢查 ===\n')

# 檢查 Models 是否正確建立
print('✓ Friendship model 已載入')
print('✓ FriendRequest model 已載入')
print('✓ SharedWithFriend model 已載入')
print('✓ FriendComment model 已載入')

# 檢查現有資料
print(f'\n目前統計：')
print(f'  - 用戶總數: {User.objects.count()}')
print(f'  - 好友關係: {Friendship.objects.count()}')
print(f'  - 好友請求: {FriendRequest.objects.count()}')
print(f'  - 分享記錄: {SharedWithFriend.objects.count()}')
print(f'  - 留言數: {FriendComment.objects.count()}')

print('\n=== Models 檢查完成 ===\n')
