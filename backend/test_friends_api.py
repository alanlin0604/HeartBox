"""
測試好友系統 API 的腳本

使用方法：
python manage.py shell < test_friends_api.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from api.models import (
    FriendComment,
    FriendRequest,
    Friendship,
    MoodNote,
    SharedWithFriend,
)
from api.services.friends_service import (
    accept_friend_request,
    add_comment_to_share,
    create_friendship,
    get_friend_activity,
    remove_friendship,
    send_friend_request,
    share_note_with_friends,
)

User = get_user_model()

print('=== 好友系統 API 測試 ===\n')

# 1. 建立測試用戶
print('1. 建立測試用戶...')
user1, created = User.objects.get_or_create(
    username='testuser1', defaults={'email': 'test1@example.com'}
)
if created:
    user1.set_password('testpass123')
    user1.save()
    print('   ✓ 建立 testuser1')
else:
    print('   → testuser1 已存在')

user2, created = User.objects.get_or_create(
    username='testuser2', defaults={'email': 'test2@example.com'}
)
if created:
    user2.set_password('testpass123')
    user2.save()
    print('   ✓ 建立 testuser2')
else:
    print('   → testuser2 已存在')

# 2. 測試發送好友請求
print('\n2. 測試發送好友請求...')
try:
    friend_request = send_friend_request(user1, user2, '我們一起記錄生活吧！')
    print(f'   ✓ 好友請求已發送: {friend_request}')
except ValueError as e:
    print(f'   → 好友請求已存在或發生錯誤: {e}')

# 3. 測試接受好友請求
print('\n3. 測試接受好友請求...')
pending_requests = FriendRequest.objects.filter(to_user=user2, status='pending')
if pending_requests.exists():
    request = pending_requests.first()
    accepted = accept_friend_request(request.id, user2)
    print(f'   ✓ 好友請求已接受: {accepted}')
else:
    print('   → 沒有待處理的好友請求')

# 4. 檢查好友關係
print('\n4. 檢查好友關係...')
friendship_count = Friendship.objects.filter(user=user1, friend=user2).count()
reverse_count = Friendship.objects.filter(user=user2, friend=user1).count()
print(f'   User1 → User2: {friendship_count} 筆')
print(f'   User2 → User1: {reverse_count} 筆')
if friendship_count > 0 and reverse_count > 0:
    print('   ✓ 雙向好友關係已建立')

# 5. 建立測試日記
print('\n5. 建立測試日記...')
note, created = MoodNote.objects.get_or_create(
    user=user1,
    defaults={
        'sentiment_score': 0.8,
        'stress_index': 3,
    },
)
if created:
    note.set_content('今天心情很好，學會了很多新東西！')
    note.save()
    print(f'   ✓ 建立日記: {note}')
else:
    print(f'   → 日記已存在: {note}')

# 6. 測試分享日記給好友
print('\n6. 測試分享日記給好友...')
shares = share_note_with_friends(note, [user2.id])
if shares:
    print(f'   ✓ 分享成功: {len(shares)} 筆分享記錄')
else:
    print('   → 日記已分享或發生錯誤')

# 7. 測試好友留言
print('\n7. 測試好友留言...')
share = SharedWithFriend.objects.filter(note=note, shared_with=user2).first()
if share:
    try:
        comment = add_comment_to_share(share, user2, '加油！繼續保持！')
        print(f'   ✓ 留言成功: {comment}')
    except ValueError as e:
        print(f'   → 留言失敗: {e}')
else:
    print('   → 找不到分享記錄')

# 8. 測試好友動態
print('\n8. 測試好友動態...')
activities = get_friend_activity(user2, hours=24)
print(f'   ✓ 找到 {len(activities)} 筆好友動態')
for activity in activities[:3]:  # 只顯示前 3 筆
    print(f'   - {activity["friend_username"]} 寫了新日記 (連續 {activity["streak_days"]} 天)')

# 9. 統計資訊
print('\n9. 統計資訊...')
print(f'   總用戶數: {User.objects.count()}')
print(f'   總好友關係: {Friendship.objects.count()} 筆（雙向）')
print(f'   待處理請求: {FriendRequest.objects.filter(status="pending").count()} 筆')
print(f'   分享記錄: {SharedWithFriend.objects.count()} 筆')
print(f'   留言數: {FriendComment.objects.count()} 筆')

print('\n=== 測試完成 ===')
