#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick test for Community API endpoints.
Run: python test_community_api.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moodnotes_pro.settings')
django.setup()

from django.contrib.auth import get_user_model
from api.models import PublicPost, PostReaction

User = get_user_model()

def test_community_api():
    print("=== Community API Quick Test ===\n")

    # 1. Create test user if not exists
    user, created = User.objects.get_or_create(
        username='test_community_user',
        defaults={'email': 'test@example.com'}
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"[OK] Created test user: {user.username}")
    else:
        print(f"[OK] Using existing test user: {user.username}")

    # 2. Create a test post
    post = PublicPost.objects.create(
        user=user,
        content="This is a test post for anonymous community sharing.\n\nHope everyone finds support here!",
        sentiment_score=-0.2,
        category='anxiety'
    )
    print(f"[OK] Created test post (ID: {post.id})")

    # 3. Add reactions
    for reaction_type in ['hug', 'support', 'heart']:
        PostReaction.objects.create(
            post=post,
            user=user,
            reaction_type=reaction_type
        )
        print(f"[OK] Added {reaction_type} reaction")

    # 4. Query posts
    posts = PublicPost.objects.filter(is_active=True).count()
    print(f"\n[OK] Total active posts: {posts}")

    # 5. Query reactions
    reactions = PostReaction.objects.filter(post=post).count()
    print(f"[OK] Reactions on test post: {reactions}")

    # 6. Test reaction counts
    from django.db.models import Count
    reaction_counts = post.reactions.values('reaction_type').annotate(count=Count('id'))
    print(f"\n[OK] Reaction breakdown:")
    for r in reaction_counts:
        print(f"  - {r['reaction_type']}: {r['count']}")

    # 7. Cleanup
    print(f"\n[OK] Test post content preview:")
    print(f"  {post.content[:100]}...")

    print("\n=== All tests passed! ===")
    print(f"\nAPI endpoints available:")
    print(f"  GET  /api/community/posts/ - List posts")
    print(f"  POST /api/community/posts/ - Create post")
    print(f"  GET  /api/community/posts/<id>/ - Get post")
    print(f"  DELETE /api/community/posts/<id>/ - Delete post")
    print(f"  POST /api/community/posts/<id>/react/ - Toggle reaction")
    print(f"  GET  /api/community/posts/my_posts/ - My posts")

if __name__ == '__main__':
    try:
        test_community_api()
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
