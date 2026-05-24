from django.utils import timezone

from api.models import (
    AIChatSession, Booking, Conversation,
    DailySleep, DashboardLayout, Feedback, Friendship, FriendComment,
    Habit, HabitLog, HealthMetric, Message, MoodNote, Notification,
    NoteAttachment, PostReaction, PublicPost, SelfAssessment, SharedNote,
    SharedWithFriend, UserAchievement, WellnessSession,
)

ACHIEVEMENT_DEFINITIONS = {
    # ===== Writing =====
    'first_note': {
        'category': 'writing',
        'icon': 'pencil',
        'threshold': 1,
        'name_key': 'achievement.first_note',
        'desc_key': 'achievement.first_note_desc',
    },
    'notes_10': {
        'category': 'writing',
        'icon': 'notebook',
        'threshold': 10,
        'name_key': 'achievement.notes_10',
        'desc_key': 'achievement.notes_10_desc',
    },
    'notes_50': {
        'category': 'writing',
        'icon': 'books',
        'threshold': 50,
        'name_key': 'achievement.notes_50',
        'desc_key': 'achievement.notes_50_desc',
    },
    'notes_100': {
        'category': 'writing',
        'icon': 'trophy',
        'threshold': 100,
        'name_key': 'achievement.notes_100',
        'desc_key': 'achievement.notes_100_desc',
    },
    'long_writer': {
        'category': 'writing',
        'icon': 'scroll',
        'threshold': 500,
        'name_key': 'achievement.long_writer',
        'desc_key': 'achievement.long_writer_desc',
    },
    # ===== Consistency =====
    'streak_3': {
        'category': 'consistency',
        'icon': 'fire',
        'threshold': 3,
        'name_key': 'achievement.streak_3',
        'desc_key': 'achievement.streak_3_desc',
    },
    'streak_7': {
        'category': 'consistency',
        'icon': 'flame',
        'threshold': 7,
        'name_key': 'achievement.streak_7',
        'desc_key': 'achievement.streak_7_desc',
    },
    'streak_30': {
        'category': 'consistency',
        'icon': 'calendar',
        'threshold': 30,
        'name_key': 'achievement.streak_30',
        'desc_key': 'achievement.streak_30_desc',
    },
    # ===== Mood =====
    'mood_explorer': {
        'category': 'mood',
        'icon': 'compass',
        'threshold': 5,
        'name_key': 'achievement.mood_explorer',
        'desc_key': 'achievement.mood_explorer_desc',
    },
    'positive_streak': {
        'category': 'mood',
        'icon': 'sun',
        'threshold': 3,
        'name_key': 'achievement.positive_streak',
        'desc_key': 'achievement.positive_streak_desc',
    },
    'mood_improver': {
        'category': 'mood',
        'icon': 'trending_up',
        'threshold': 3,
        'name_key': 'achievement.mood_improver',
        'desc_key': 'achievement.mood_improver_desc',
    },
    'self_aware': {
        'category': 'mood',
        'icon': 'brain',
        'threshold': 10,
        'name_key': 'achievement.self_aware',
        'desc_key': 'achievement.self_aware_desc',
    },
    # ===== Social =====
    # Counselor-coupled achievements are marked hidden=True pre-launch — the
    # /counselors UI is hidden so users can't unlock them, and we don't want
    # un-unlockable cards cluttering the Achievements page. Flip hidden off
    # (or remove the flag) when /counselors ships.
    'first_share': {
        'category': 'social',
        'icon': 'share',
        'threshold': 1,
        'name_key': 'achievement.first_share',
        'desc_key': 'achievement.first_share_desc',
        'hidden': True,
    },
    'first_booking': {
        'category': 'social',
        'icon': 'calendar_check',
        'threshold': 1,
        'name_key': 'achievement.first_booking',
        'desc_key': 'achievement.first_booking_desc',
        'hidden': True,
    },
    'first_ai_chat': {
        'category': 'social',
        'icon': 'robot',
        'threshold': 1,
        'name_key': 'achievement.first_ai_chat',
        'desc_key': 'achievement.first_ai_chat_desc',
    },
    'ai_chat_10': {
        'category': 'social',
        'icon': 'chat_dots',
        'threshold': 10,
        'name_key': 'achievement.ai_chat_10',
        'desc_key': 'achievement.ai_chat_10_desc',
    },
    # ===== Explore =====
    'night_owl': {
        'category': 'explore',
        'icon': 'moon',
        'threshold': 1,
        'name_key': 'achievement.night_owl',
        'desc_key': 'achievement.night_owl_desc',
    },
    'early_bird': {
        'category': 'explore',
        'icon': 'sunrise',
        'threshold': 1,
        'name_key': 'achievement.early_bird',
        'desc_key': 'achievement.early_bird_desc',
    },
    'pin_master': {
        'category': 'explore',
        'icon': 'pin',
        'threshold': 5,
        'name_key': 'achievement.pin_master',
        'desc_key': 'achievement.pin_master_desc',
    },
    # ===== New Achievements =====
    'notes_200': {
        'category': 'writing',
        'icon': 'medal',
        'threshold': 200,
        'name_key': 'achievement.notes_200',
        'desc_key': 'achievement.notes_200_desc',
    },
    'first_image': {
        'category': 'writing',
        'icon': 'camera',
        'threshold': 1,
        'name_key': 'achievement.first_image',
        'desc_key': 'achievement.first_image_desc',
    },
    'weekend_warrior': {
        'category': 'consistency',
        'icon': 'sparkles',
        'threshold': 1,
        'name_key': 'achievement.weekend_warrior',
        'desc_key': 'achievement.weekend_warrior_desc',
    },
    'dedicated_months_3': {
        'category': 'consistency',
        'icon': 'calendar_star',
        'threshold': 3,
        'name_key': 'achievement.dedicated_months_3',
        'desc_key': 'achievement.dedicated_months_3_desc',
    },
    'stress_manager': {
        'category': 'mood',
        'icon': 'leaf',
        'threshold': 5,
        'name_key': 'achievement.stress_manager',
        'desc_key': 'achievement.stress_manager_desc',
    },
    'emotional_range': {
        'category': 'mood',
        'icon': 'rainbow',
        'threshold': 2,
        'name_key': 'achievement.emotional_range',
        'desc_key': 'achievement.emotional_range_desc',
    },
    'conversation_starter': {
        'category': 'social',
        'icon': 'handshake',
        'threshold': 1,
        'name_key': 'achievement.conversation_starter',
        'desc_key': 'achievement.conversation_starter_desc',
        'hidden': True,
    },
    'messages_50': {
        'category': 'social',
        'icon': 'mailbox',
        'threshold': 50,
        'name_key': 'achievement.messages_50',
        'desc_key': 'achievement.messages_50_desc',
        'hidden': True,
    },
    'tag_collector': {
        'category': 'explore',
        'icon': 'tags',
        'threshold': 10,
        'name_key': 'achievement.tag_collector',
        'desc_key': 'achievement.tag_collector_desc',
    },
    'weather_logger': {
        'category': 'explore',
        'icon': 'cloud_sun',
        'threshold': 5,
        'name_key': 'achievement.weather_logger',
        'desc_key': 'achievement.weather_logger_desc',
    },
    'feedback_giver': {
        'category': 'wellness',
        'icon': 'heart',
        'threshold': 1,
        'name_key': 'achievement.feedback_giver',
        'desc_key': 'achievement.feedback_giver_desc',
    },

    # ===== NEW: Friends Category =====
    'first_friend': {
        'category': 'friends',
        'icon': 'user_plus',
        'threshold': 1,
        'name_key': 'achievement.first_friend',
        'desc_key': 'achievement.first_friend_desc',
    },
    'friends_5': {
        'category': 'friends',
        'icon': 'users',
        'threshold': 5,
        'name_key': 'achievement.friends_5',
        'desc_key': 'achievement.friends_5_desc',
    },
    'first_friend_share': {
        'category': 'friends',
        'icon': 'gift',
        'threshold': 1,
        'name_key': 'achievement.first_friend_share',
        'desc_key': 'achievement.first_friend_share_desc',
    },
    'friend_supporter': {
        'category': 'friends',
        'icon': 'message_heart',
        'threshold': 5,
        'name_key': 'achievement.friend_supporter',
        'desc_key': 'achievement.friend_supporter_desc',
    },

    # ===== NEW: Community Category =====
    'first_community_post': {
        'category': 'community',
        'icon': 'megaphone',
        'threshold': 1,
        'name_key': 'achievement.first_community_post',
        'desc_key': 'achievement.first_community_post_desc',
    },
    'community_supporter': {
        'category': 'community',
        'icon': 'hands_helping',
        'threshold': 10,
        'name_key': 'achievement.community_supporter',
        'desc_key': 'achievement.community_supporter_desc',
    },
    'community_voice': {
        'category': 'community',
        'icon': 'sparkle_heart',
        'threshold': 5,
        'name_key': 'achievement.community_voice',
        'desc_key': 'achievement.community_voice_desc',
    },

    # ===== NEW: Health Category =====
    'first_sleep_log': {
        'category': 'health',
        'icon': 'bed',
        'threshold': 1,
        'name_key': 'achievement.first_sleep_log',
        'desc_key': 'achievement.first_sleep_log_desc',
    },
    'sleep_streak_7': {
        'category': 'health',
        'icon': 'moon_stars',
        'threshold': 7,
        'name_key': 'achievement.sleep_streak_7',
        'desc_key': 'achievement.sleep_streak_7_desc',
    },
    'quality_sleeper': {
        'category': 'health',
        'icon': 'star_filled',
        'threshold': 1,
        'name_key': 'achievement.quality_sleeper',
        'desc_key': 'achievement.quality_sleeper_desc',
    },
    'first_health_sync': {
        'category': 'health',
        'icon': 'watch',
        'threshold': 1,
        'name_key': 'achievement.first_health_sync',
        'desc_key': 'achievement.first_health_sync_desc',
    },
    'step_goal_10k': {
        'category': 'health',
        'icon': 'footprints',
        'threshold': 1,
        'name_key': 'achievement.step_goal_10k',
        'desc_key': 'achievement.step_goal_10k_desc',
    },

    # ===== NEW: Wellness expanded (habits + breathing) =====
    'first_habit': {
        'category': 'wellness',
        'icon': 'target',
        'threshold': 1,
        'name_key': 'achievement.first_habit',
        'desc_key': 'achievement.first_habit_desc',
    },
    'habit_streak_7': {
        'category': 'wellness',
        'icon': 'flame_small',
        'threshold': 7,
        'name_key': 'achievement.habit_streak_7',
        'desc_key': 'achievement.habit_streak_7_desc',
    },
    'habit_streak_30': {
        'category': 'wellness',
        'icon': 'crown',
        'threshold': 30,
        'name_key': 'achievement.habit_streak_30',
        'desc_key': 'achievement.habit_streak_30_desc',
    },
    'first_breathing': {
        'category': 'wellness',
        'icon': 'lungs',
        'threshold': 1,
        'name_key': 'achievement.first_breathing',
        'desc_key': 'achievement.first_breathing_desc',
    },
    'wellness_sessions_10': {
        'category': 'wellness',
        'icon': 'lotus',
        'threshold': 10,
        'name_key': 'achievement.wellness_sessions_10',
        'desc_key': 'achievement.wellness_sessions_10_desc',
    },

    # ===== NEW: Explore expanded =====
    'first_assessment': {
        'category': 'explore',
        'icon': 'clipboard_check',
        'threshold': 1,
        'name_key': 'achievement.first_assessment',
        'desc_key': 'achievement.first_assessment_desc',
    },
    'assessment_regular': {
        'category': 'explore',
        'icon': 'graph_up',
        'threshold': 5,
        'name_key': 'achievement.assessment_regular',
        'desc_key': 'achievement.assessment_regular_desc',
    },
    'dashboard_customized': {
        'category': 'explore',
        'icon': 'layout',
        'threshold': 1,
        'name_key': 'achievement.dashboard_customized',
        'desc_key': 'achievement.dashboard_customized_desc',
    },
    'ai_chat_50': {
        'category': 'social',
        'icon': 'robot_star',
        'threshold': 50,
        'name_key': 'achievement.ai_chat_50',
        'desc_key': 'achievement.ai_chat_50_desc',
    },

    # ===== NEW: Meta achievements =====
    'achievement_hunter': {
        'category': 'meta',
        'icon': 'medal_bronze',
        'threshold': 10,
        'name_key': 'achievement.achievement_hunter',
        'desc_key': 'achievement.achievement_hunter_desc',
    },
    'achievement_legend': {
        'category': 'meta',
        'icon': 'medal_gold',
        'threshold': 25,
        'name_key': 'achievement.achievement_legend',
        'desc_key': 'achievement.achievement_legend_desc',
    },

    # ============================================================
    # ===== 2026-05-24 expansion: 55 new achievements ============
    # Target: cross the 100-total threshold so the Achievements
    # page feels meaningfully gamified pre-Play-Store launch.
    # New helpers + progress fields below in _get_progress.
    # ============================================================

    # --- Writing (extended) ---
    'notes_500': {'category': 'writing', 'icon': 'trophy_silver', 'threshold': 500,
                  'name_key': 'achievement.notes_500', 'desc_key': 'achievement.notes_500_desc'},
    'notes_1000': {'category': 'writing', 'icon': 'trophy_gold', 'threshold': 1000,
                   'name_key': 'achievement.notes_1000', 'desc_key': 'achievement.notes_1000_desc'},
    'words_1k_note': {'category': 'writing', 'icon': 'scroll_long', 'threshold': 1000,
                      'name_key': 'achievement.words_1k_note', 'desc_key': 'achievement.words_1k_note_desc'},
    'morning_writer': {'category': 'writing', 'icon': 'sun_morning', 'threshold': 5,
                       'name_key': 'achievement.morning_writer', 'desc_key': 'achievement.morning_writer_desc'},
    'evening_writer': {'category': 'writing', 'icon': 'moon_evening', 'threshold': 5,
                       'name_key': 'achievement.evening_writer', 'desc_key': 'achievement.evening_writer_desc'},
    'midnight_writer': {'category': 'writing', 'icon': 'owl', 'threshold': 3,
                        'name_key': 'achievement.midnight_writer', 'desc_key': 'achievement.midnight_writer_desc'},
    'photo_album': {'category': 'writing', 'icon': 'photo_stack', 'threshold': 10,
                    'name_key': 'achievement.photo_album', 'desc_key': 'achievement.photo_album_desc'},
    'detailed_writer': {'category': 'writing', 'icon': 'book_open', 'threshold': 10,
                        'name_key': 'achievement.detailed_writer', 'desc_key': 'achievement.detailed_writer_desc'},

    # --- Consistency (extended) ---
    'streak_14': {'category': 'consistency', 'icon': 'flame_blue', 'threshold': 14,
                  'name_key': 'achievement.streak_14', 'desc_key': 'achievement.streak_14_desc'},
    'streak_60': {'category': 'consistency', 'icon': 'flame_purple', 'threshold': 60,
                  'name_key': 'achievement.streak_60', 'desc_key': 'achievement.streak_60_desc'},
    'streak_100': {'category': 'consistency', 'icon': 'flame_diamond', 'threshold': 100,
                   'name_key': 'achievement.streak_100', 'desc_key': 'achievement.streak_100_desc'},
    'streak_365': {'category': 'consistency', 'icon': 'crown_gold', 'threshold': 365,
                   'name_key': 'achievement.streak_365', 'desc_key': 'achievement.streak_365_desc'},
    'comeback_kid': {'category': 'consistency', 'icon': 'phoenix', 'threshold': 1,
                     'name_key': 'achievement.comeback_kid', 'desc_key': 'achievement.comeback_kid_desc'},

    # --- Mood (extended) ---
    'happy_week': {'category': 'mood', 'icon': 'smile_big', 'threshold': 1,
                   'name_key': 'achievement.happy_week', 'desc_key': 'achievement.happy_week_desc'},
    'calm_week': {'category': 'mood', 'icon': 'leaf_zen', 'threshold': 1,
                  'name_key': 'achievement.calm_week', 'desc_key': 'achievement.calm_week_desc'},
    'emotional_spectrum': {'category': 'mood', 'icon': 'rainbow_full', 'threshold': 5,
                           'name_key': 'achievement.emotional_spectrum', 'desc_key': 'achievement.emotional_spectrum_desc'},
    'mood_journal_50': {'category': 'mood', 'icon': 'brain_star', 'threshold': 50,
                        'name_key': 'achievement.mood_journal_50', 'desc_key': 'achievement.mood_journal_50_desc'},

    # --- Health (extended) ---
    'sleep_streak_14': {'category': 'health', 'icon': 'bed_clouds', 'threshold': 14,
                        'name_key': 'achievement.sleep_streak_14', 'desc_key': 'achievement.sleep_streak_14_desc'},
    'sleep_streak_30': {'category': 'health', 'icon': 'bed_stars', 'threshold': 30,
                        'name_key': 'achievement.sleep_streak_30', 'desc_key': 'achievement.sleep_streak_30_desc'},
    'sleep_logger_30': {'category': 'health', 'icon': 'log_sleep', 'threshold': 30,
                        'name_key': 'achievement.sleep_logger_30', 'desc_key': 'achievement.sleep_logger_30_desc'},
    'early_sleeper': {'category': 'health', 'icon': 'crescent_moon', 'threshold': 5,
                      'name_key': 'achievement.early_sleeper', 'desc_key': 'achievement.early_sleeper_desc'},
    'step_streak_7': {'category': 'health', 'icon': 'sneaker_streak', 'threshold': 7,
                      'name_key': 'achievement.step_streak_7', 'desc_key': 'achievement.step_streak_7_desc'},
    'step_streak_30': {'category': 'health', 'icon': 'sneaker_gold', 'threshold': 30,
                      'name_key': 'achievement.step_streak_30', 'desc_key': 'achievement.step_streak_30_desc'},
    'health_sync_100': {'category': 'health', 'icon': 'watch_pulse', 'threshold': 100,
                        'name_key': 'achievement.health_sync_100', 'desc_key': 'achievement.health_sync_100_desc'},
    'health_data_diverse': {'category': 'health', 'icon': 'health_grid', 'threshold': 5,
                            'name_key': 'achievement.health_data_diverse', 'desc_key': 'achievement.health_data_diverse_desc'},

    # --- Wellness (extended) ---
    'habit_count_3': {'category': 'wellness', 'icon': 'target_3', 'threshold': 3,
                      'name_key': 'achievement.habit_count_3', 'desc_key': 'achievement.habit_count_3_desc'},
    'habit_count_5': {'category': 'wellness', 'icon': 'target_5', 'threshold': 5,
                      'name_key': 'achievement.habit_count_5', 'desc_key': 'achievement.habit_count_5_desc'},
    'breathing_minutes_30': {'category': 'wellness', 'icon': 'lungs_air', 'threshold': 30,
                             'name_key': 'achievement.breathing_minutes_30', 'desc_key': 'achievement.breathing_minutes_30_desc'},
    'breathing_minutes_120': {'category': 'wellness', 'icon': 'lungs_deep', 'threshold': 120,
                              'name_key': 'achievement.breathing_minutes_120', 'desc_key': 'achievement.breathing_minutes_120_desc'},
    'meditation_sessions_30': {'category': 'wellness', 'icon': 'lotus_open', 'threshold': 30,
                               'name_key': 'achievement.meditation_sessions_30', 'desc_key': 'achievement.meditation_sessions_30_desc'},
    'wellness_master_100': {'category': 'wellness', 'icon': 'wellness_crown', 'threshold': 100,
                            'name_key': 'achievement.wellness_master_100', 'desc_key': 'achievement.wellness_master_100_desc'},
    'breathing_streak_7': {'category': 'wellness', 'icon': 'wind_streak', 'threshold': 7,
                           'name_key': 'achievement.breathing_streak_7', 'desc_key': 'achievement.breathing_streak_7_desc'},
    'diverse_wellness': {'category': 'wellness', 'icon': 'mosaic', 'threshold': 3,
                         'name_key': 'achievement.diverse_wellness', 'desc_key': 'achievement.diverse_wellness_desc'},

    # --- Explore (extended) ---
    'tag_collector_30': {'category': 'explore', 'icon': 'tags_full', 'threshold': 30,
                         'name_key': 'achievement.tag_collector_30', 'desc_key': 'achievement.tag_collector_30_desc'},
    'all_features_tried': {'category': 'explore', 'icon': 'compass_star', 'threshold': 6,
                           'name_key': 'achievement.all_features_tried', 'desc_key': 'achievement.all_features_tried_desc'},
    'diverse_activities': {'category': 'explore', 'icon': 'activity_grid', 'threshold': 10,
                           'name_key': 'achievement.diverse_activities', 'desc_key': 'achievement.diverse_activities_desc'},
    'weather_diversity': {'category': 'explore', 'icon': 'weather_full', 'threshold': 5,
                          'name_key': 'achievement.weather_diversity', 'desc_key': 'achievement.weather_diversity_desc'},
    'assessment_master_10': {'category': 'explore', 'icon': 'clipboard_star', 'threshold': 10,
                             'name_key': 'achievement.assessment_master_10', 'desc_key': 'achievement.assessment_master_10_desc'},
    'pin_master_10': {'category': 'explore', 'icon': 'pin_stack', 'threshold': 10,
                      'name_key': 'achievement.pin_master_10', 'desc_key': 'achievement.pin_master_10_desc'},

    # --- AI (extended) ---
    'ai_chat_100': {'category': 'social', 'icon': 'robot_pro', 'threshold': 100,
                    'name_key': 'achievement.ai_chat_100', 'desc_key': 'achievement.ai_chat_100_desc'},
    'ai_chat_500': {'category': 'social', 'icon': 'robot_master', 'threshold': 500,
                    'name_key': 'achievement.ai_chat_500', 'desc_key': 'achievement.ai_chat_500_desc'},
    'daily_ai_chat_7': {'category': 'social', 'icon': 'robot_streak', 'threshold': 7,
                        'name_key': 'achievement.daily_ai_chat_7', 'desc_key': 'achievement.daily_ai_chat_7_desc'},

    # --- Friends (extended) ---
    'friends_10': {'category': 'friends', 'icon': 'users_group', 'threshold': 10,
                   'name_key': 'achievement.friends_10', 'desc_key': 'achievement.friends_10_desc'},
    'friends_25': {'category': 'friends', 'icon': 'users_crowd', 'threshold': 25,
                   'name_key': 'achievement.friends_25', 'desc_key': 'achievement.friends_25_desc'},
    'friend_share_10': {'category': 'friends', 'icon': 'gift_stack', 'threshold': 10,
                        'name_key': 'achievement.friend_share_10', 'desc_key': 'achievement.friend_share_10_desc'},
    'friend_comment_25': {'category': 'friends', 'icon': 'message_heart_full', 'threshold': 25,
                          'name_key': 'achievement.friend_comment_25', 'desc_key': 'achievement.friend_comment_25_desc'},
    'friend_share_received_5': {'category': 'friends', 'icon': 'gift_received', 'threshold': 5,
                                'name_key': 'achievement.friend_share_received_5', 'desc_key': 'achievement.friend_share_received_5_desc'},

    # --- Community (extended) ---
    'community_posts_5': {'category': 'community', 'icon': 'megaphone_5', 'threshold': 5,
                          'name_key': 'achievement.community_posts_5', 'desc_key': 'achievement.community_posts_5_desc'},
    'community_posts_20': {'category': 'community', 'icon': 'megaphone_pro', 'threshold': 20,
                           'name_key': 'achievement.community_posts_20', 'desc_key': 'achievement.community_posts_20_desc'},
    'community_top_post': {'category': 'community', 'icon': 'sparkle_star', 'threshold': 10,
                           'name_key': 'achievement.community_top_post', 'desc_key': 'achievement.community_top_post_desc'},
    'community_active_10': {'category': 'community', 'icon': 'calendar_active', 'threshold': 10,
                            'name_key': 'achievement.community_active_10', 'desc_key': 'achievement.community_active_10_desc'},
    'reactions_given_50': {'category': 'community', 'icon': 'thumbs_pro', 'threshold': 50,
                           'name_key': 'achievement.reactions_given_50', 'desc_key': 'achievement.reactions_given_50_desc'},

    # --- Meta (extended) ---
    'achievement_master': {'category': 'meta', 'icon': 'medal_silver', 'threshold': 50,
                           'name_key': 'achievement.achievement_master', 'desc_key': 'achievement.achievement_master_desc'},
    'achievement_god': {'category': 'meta', 'icon': 'medal_diamond', 'threshold': 100,
                        'name_key': 'achievement.achievement_god', 'desc_key': 'achievement.achievement_god_desc'},
}


def _get_note_count(user):
    return MoodNote.objects.filter(user=user, is_deleted=False).count()


def _get_longest_streak(user):
    dates = list(
        MoodNote.objects.filter(user=user, is_deleted=False)
        .values_list('created_at__date', flat=True)
        .distinct()
        .order_by('-created_at__date')[:366]
    )
    if not dates:
        return 0
    sorted_dates = sorted(set(dates))
    best = 1
    run = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def _get_max_note_length(user):
    """Get max character count of any note using search_text (plaintext, up to 500 chars)."""
    from django.db.models.functions import Length
    result = (
        MoodNote.objects.filter(user=user, is_deleted=False)
        .exclude(search_text='')
        .annotate(text_len=Length('search_text'))
        .order_by('-text_len')
        .values_list('text_len', flat=True)
        .first()
    )
    return result or 0


def _get_distinct_mood_buckets(user):
    """Count distinct mood buckets used: very_negative, negative, neutral, positive, very_positive."""
    scores = list(
        MoodNote.objects.filter(user=user, sentiment_score__isnull=False)
        .values_list('sentiment_score', flat=True)
    )
    buckets = set()
    for s in scores:
        if s <= -0.6:
            buckets.add('very_negative')
        elif s <= -0.2:
            buckets.add('negative')
        elif s <= 0.2:
            buckets.add('neutral')
        elif s <= 0.6:
            buckets.add('positive')
        else:
            buckets.add('very_positive')
    return len(buckets)


def _has_positive_streak(user, count=3):
    """Check if last `count` notes all have positive sentiment (>0.3)."""
    scores = list(
        MoodNote.objects.filter(user=user, sentiment_score__isnull=False)
        .order_by('-created_at')
        .values_list('sentiment_score', flat=True)[:count]
    )
    return len(scores) >= count and all(s > 0.3 for s in scores)


def _has_mood_improving(user, count=3):
    """Check if last `count` notes have consecutively increasing sentiment."""
    scores = list(
        MoodNote.objects.filter(user=user, sentiment_score__isnull=False)
        .order_by('-created_at')
        .values_list('sentiment_score', flat=True)[:count]
    )
    if len(scores) < count:
        return False
    # Reverse so oldest first
    scores = scores[::-1]
    return all(scores[i] < scores[i + 1] for i in range(len(scores) - 1))


def _get_ai_analyzed_count(user):
    return MoodNote.objects.filter(user=user, ai_feedback__gt='').count()


def _has_weekend_pair(user):
    """Check if the user has written notes on both Saturday and Sunday of the same week."""
    dates = list(
        MoodNote.objects.filter(user=user, is_deleted=False)
        .values_list('created_at__date', flat=True)
        .distinct()
        .order_by('created_at__date')
    )
    # Group by ISO week
    weeks = {}
    for d in dates:
        key = (d.isocalendar()[0], d.isocalendar()[1])
        weeks.setdefault(key, set()).add(d.isoweekday())
    # isoweekday: 6=Saturday, 7=Sunday
    return any(6 in days and 7 in days for days in weeks.values())


def _get_distinct_tag_count(user):
    """Count distinct tags across all notes (only recent 500 for performance)."""
    tags = set()
    for meta in MoodNote.objects.filter(user=user, is_deleted=False).order_by('-created_at').values_list('metadata', flat=True)[:500]:
        if meta and isinstance(meta, dict):
            for tag in (meta.get('tags') or []):
                tags.add(tag)
    return len(tags)


def _get_weather_note_count(user):
    """Count notes that have a non-empty weather field."""
    count = 0
    for meta in MoodNote.objects.filter(user=user, is_deleted=False).order_by('-created_at').values_list('metadata', flat=True)[:500]:
        if meta and isinstance(meta, dict) and meta.get('weather'):
            count += 1
    return count


def _get_longest_sleep_streak(user):
    """Longest consecutive-day streak of DailySleep records."""
    dates = list(
        DailySleep.objects.filter(user=user).values_list('date', flat=True).order_by('date')[:366]
    )
    if not dates:
        return 0
    best = 1
    run = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def _get_quality_sleep_week(user):
    """1 if any 7-day window has avg sleep_quality >= 4, else 0."""
    from datetime import timedelta
    qualities = list(
        DailySleep.objects.filter(user=user, sleep_quality__isnull=False)
        .order_by('-date').values_list('date', 'sleep_quality')[:60]
    )
    if len(qualities) < 7:
        return 0
    # Group by date for rolling window
    date_to_q = {d: q for d, q in qualities}
    sorted_dates = sorted(date_to_q.keys())
    for i in range(len(sorted_dates) - 6):
        window = [
            date_to_q[d] for d in sorted_dates[i:i + 7]
            if (sorted_dates[i + 6] - sorted_dates[i]).days == 6
        ]
        if len(window) == 7 and sum(window) / 7 >= 4.0:
            return 1
    return 0


def _get_window_stat(values_by_date, window=7, *, fn=sum, divisor=None):
    """Slide a window of N consecutive dates across (date → numeric) data,
    return the best value of fn(window_values) / (divisor or 1).

    Used for happy_week / calm_week — find the best (or worst) 7-day
    window's average sentiment / stress. Returns None if no window
    qualifies (fewer than N consecutive days).
    """
    if not values_by_date:
        return None
    sorted_dates = sorted(values_by_date.keys())
    best = None
    for i in range(len(sorted_dates) - window + 1):
        slice_dates = sorted_dates[i:i + window]
        if (slice_dates[-1] - slice_dates[0]).days != window - 1:
            continue
        agg = fn(values_by_date[d] for d in slice_dates)
        if divisor:
            agg = agg / divisor
        if best is None:
            best = agg
        else:
            best = max(best, agg) if fn is sum or fn is max else min(best, agg)
    return best


def _happy_week_hit(user):
    """1 if any 7-consecutive-day window has avg sentiment > 0.4."""
    from datetime import date as _date
    rows = (
        MoodNote.objects.filter(user=user, sentiment_score__isnull=False)
        .values_list('created_at__date', 'sentiment_score')
    )
    # average per day (multiple notes / day → mean)
    by_date = {}
    counts = {}
    for d, s in rows:
        by_date[d] = by_date.get(d, 0) + float(s)
        counts[d] = counts.get(d, 0) + 1
    daily_avg = {d: by_date[d] / counts[d] for d in by_date}
    sorted_dates = sorted(daily_avg.keys())
    for i in range(len(sorted_dates) - 6):
        if (sorted_dates[i + 6] - sorted_dates[i]).days != 6:
            continue
        window = [daily_avg[d] for d in sorted_dates[i:i + 7]]
        if sum(window) / 7 > 0.4:
            return 1
    return 0


def _calm_week_hit(user):
    """1 if any 7-consecutive-day window has avg stress_index < 4."""
    rows = (
        MoodNote.objects.filter(user=user, stress_index__isnull=False)
        .values_list('created_at__date', 'stress_index')
    )
    by_date = {}
    counts = {}
    for d, s in rows:
        by_date[d] = by_date.get(d, 0) + float(s)
        counts[d] = counts.get(d, 0) + 1
    daily_avg = {d: by_date[d] / counts[d] for d in by_date}
    sorted_dates = sorted(daily_avg.keys())
    for i in range(len(sorted_dates) - 6):
        if (sorted_dates[i + 6] - sorted_dates[i]).days != 6:
            continue
        window = [daily_avg[d] for d in sorted_dates[i:i + 7]]
        if sum(window) / 7 < 4:
            return 1
    return 0


def _has_7day_gap_and_returned(user):
    """1 if the user ever had a 7+ day gap between consecutive entries
    AND wrote again afterwards. Detects 'comeback' behavior."""
    dates = list(
        MoodNote.objects.filter(user=user, is_deleted=False)
        .values_list('created_at__date', flat=True)
        .distinct()
        .order_by('created_at__date')
    )
    if len(dates) < 2:
        return 0
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days >= 7:
            return 1
    return 0


def _get_step_streak(user, threshold=10000):
    """Longest streak of consecutive days where steps >= threshold."""
    rows = (
        HealthMetric.objects.filter(user=user, metric_type='steps', value__gte=threshold)
        .values_list('date', flat=True)
        .distinct()
        .order_by('date')
    )
    dates = list(rows)
    if not dates:
        return 0
    best = 1
    run = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def _distinct_health_types_synced(user):
    return (
        HealthMetric.objects.filter(user=user)
        .exclude(source='manual')
        .values_list('metric_type', flat=True)
        .distinct()
        .count()
    )


def _breathing_minutes_total(user):
    from django.db.models import Sum
    secs = WellnessSession.objects.filter(
        user=user, session_type='breathing',
    ).aggregate(s=Sum('duration_seconds'))['s'] or 0
    return secs // 60


def _meditation_count(user):
    return WellnessSession.objects.filter(user=user, session_type='meditation').count()


def _breathing_day_streak(user):
    """Longest consecutive-day streak of any breathing session."""
    dates = list(
        WellnessSession.objects.filter(user=user, session_type='breathing')
        .values_list('completed_at__date', flat=True)
        .distinct()
        .order_by('completed_at__date')
    )
    if not dates:
        return 0
    best = 1
    run = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def _wellness_session_type_count(user):
    return (
        WellnessSession.objects.filter(user=user)
        .values_list('session_type', flat=True).distinct().count()
    )


def _distinct_activities_in_metadata(user):
    """Count distinct activity tags across the user's notes (legacy metadata.activities)."""
    activities = set()
    for meta in MoodNote.objects.filter(user=user, is_deleted=False).order_by('-created_at').values_list('metadata', flat=True)[:500]:
        if meta and isinstance(meta, dict):
            for a in (meta.get('activities') or []):
                activities.add(a)
    return len(activities)


def _distinct_weather_in_metadata(user):
    weathers = set()
    for meta in MoodNote.objects.filter(user=user, is_deleted=False).order_by('-created_at').values_list('metadata', flat=True)[:500]:
        if meta and isinstance(meta, dict):
            w = meta.get('weather')
            if w:
                weathers.add(w)
    return len(weathers)


def _features_used_count(user):
    """Count of distinct major features the user has touched.

    Tracks 6 features: journal, AI chat, habit tracking, dashboard
    customization, friends, community. Drives the all_features_tried
    achievement — encourages users to explore the breadth of the app.
    """
    n = 0
    if MoodNote.objects.filter(user=user, is_deleted=False).exists(): n += 1
    if AIChatSession.objects.filter(user=user).exists(): n += 1
    if Habit.objects.filter(user=user).exists(): n += 1
    if DashboardLayout.objects.filter(user=user).exists(): n += 1
    if Friendship.objects.filter(user=user).exists(): n += 1
    if PublicPost.objects.filter(user=user).exists(): n += 1
    return n


def _early_sleeper_count(user):
    """Count of DailySleep rows where bedtime hour < 23 (local time).

    DateTimeField stores UTC; we approximate by checking the hour of
    the stored datetime. Not timezone-perfect but good enough for
    a gamification metric.
    """
    n = 0
    for bt in DailySleep.objects.filter(user=user, bedtime__isnull=False).values_list('bedtime', flat=True):
        if bt and bt.hour < 23 and bt.hour >= 19:
            n += 1
    return n


def _community_top_post_reactions(user):
    """Max reaction count received on any single PublicPost the user made."""
    from django.db.models import Count
    row = (
        PublicPost.objects.filter(user=user, is_active=True)
        .annotate(rc=Count('reactions'))
        .order_by('-rc').values_list('rc', flat=True).first()
    )
    return row or 0


def _community_post_distinct_dates(user):
    return (
        PublicPost.objects.filter(user=user, is_active=True)
        .values_list('created_at__date', flat=True).distinct().count()
    )


def _shares_received(user):
    """Count of SharedWithFriend rows where this user is the recipient."""
    return SharedWithFriend.objects.filter(shared_with=user).count()


def _daily_ai_chat_streak(user):
    """Longest streak of consecutive days with at least one AI chat session."""
    dates = list(
        AIChatSession.objects.filter(user=user)
        .values_list('created_at__date', flat=True)
        .distinct()
        .order_by('created_at__date')
    )
    if not dates:
        return 0
    best = 1
    run = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def _long_notes_count(user, threshold=300):
    """Notes whose plaintext is >= threshold chars."""
    from django.db.models.functions import Length
    return (
        MoodNote.objects.filter(user=user, is_deleted=False)
        .annotate(text_len=Length('search_text'))
        .filter(text_len__gte=threshold)
        .count()
    )


def _get_longest_habit_streak(user):
    """Across all of the user's habits, the longest single-habit consecutive-day streak."""
    habits = Habit.objects.filter(user=user, is_active=True).values_list('id', flat=True)
    best = 0
    for habit_id in habits:
        dates = list(
            HabitLog.objects.filter(habit_id=habit_id).values_list('date', flat=True).order_by('date')[:400]
        )
        if not dates:
            continue
        run = 1
        local_best = 1
        for i in range(1, len(dates)):
            if (dates[i] - dates[i - 1]).days == 1:
                run += 1
                local_best = max(local_best, run)
            else:
                run = 1
        best = max(best, local_best)
    return best


_PROGRESS_CACHE_TTL = 30  # seconds — short enough to feel "live", long enough to dedupe a page load


def _progress_cache_key(user):
    return f'ach_progress:{user.id}'


def invalidate_progress_cache(user):
    """Call after any state change that could affect achievement progress.

    Most progress changes flow through ``check_achievements`` (which
    invalidates internally), but external mutation paths can call this
    directly to avoid the user seeing stale numbers.
    """
    from django.core.cache import cache
    cache.delete(_progress_cache_key(user))


def _get_progress(user):
    """Calculate progress for all achievements. Returns dict of achievement_id -> current value.

    Result is cached for ~30 s per user. Multiple endpoints on the same
    page load (``/achievements/`` + ``/achievements/check/`` historically)
    re-aggregated 15+ tables on every hit; the cache collapses repeat
    work to a single DB pass within the cache window.
    """
    from django.core.cache import cache
    from django.db.models import Count, Q

    cache_key = _progress_cache_key(user)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # --- Batch 1: Aggregate MoodNote counts in a single query ---
    note_agg = MoodNote.objects.filter(user=user).aggregate(
        note_count=Count('id', filter=Q(is_deleted=False)),
        pinned_count=Count('id', filter=Q(is_pinned=True)),
        ai_analyzed=Count('id', filter=Q(ai_feedback__gt='')),
        has_night=Count('id', filter=Q(created_at__hour__gte=0, created_at__hour__lt=5)),
        has_early=Count('id', filter=Q(created_at__hour__gte=5, created_at__hour__lt=7)),
        low_stress_count=Count('id', filter=Q(stress_index__isnull=False, stress_index__lte=3)),
        has_high_sentiment=Count('id', filter=Q(sentiment_score__gt=0.6)),
        has_low_sentiment=Count('id', filter=Q(sentiment_score__lt=-0.6)),
        # New (2026-05-24): hour-windowed counts for morning/evening/midnight
        # writer achievements. Buckets are inclusive lower / exclusive upper.
        morning_notes=Count('id', filter=Q(created_at__hour__gte=5, created_at__hour__lt=9, is_deleted=False)),
        evening_notes=Count('id', filter=Q(created_at__hour__gte=18, created_at__hour__lt=22, is_deleted=False)),
        # midnight = 23:00-23:59 OR 00:00-02:59
        midnight_notes=Count('id', filter=(Q(created_at__hour__gte=23) | Q(created_at__hour__lt=3)) & Q(is_deleted=False)),
    )
    note_count = note_agg['note_count']

    # Max note length (separate query - Length is not an aggregate function)
    max_len = _get_max_note_length(user)

    longest_streak = _get_longest_streak(user)

    # --- Batch 2: Aggregate other model counts in single queries ---
    other_counts = {
        'share_count': SharedNote.objects.filter(note__user=user).count(),
        'booking_count': Booking.objects.filter(user=user).count(),
        'ai_session_count': AIChatSession.objects.filter(user=user).count(),
        'conversation_count': Conversation.objects.filter(user=user).count(),
        'message_count': Message.objects.filter(sender=user).count(),
        'feedback_count': Feedback.objects.filter(user=user).count(),
        'image_count': NoteAttachment.objects.filter(note__user=user, file_type='image').count(),
    }

    has_weekend = _has_weekend_pair(user)
    distinct_months = MoodNote.objects.filter(user=user, is_deleted=False).dates('created_at', 'month').count()
    mood_buckets = _get_distinct_mood_buckets(user)
    tag_count = _get_distinct_tag_count(user)
    weather_count = _get_weather_note_count(user)

    emotional_range = (1 if note_agg['has_high_sentiment'] > 0 else 0) + (1 if note_agg['has_low_sentiment'] > 0 else 0)

    # --- Batch 3: New feature counters ---
    new_counts = {
        'friend_count': Friendship.objects.filter(user=user).count(),
        'friend_share_count': SharedWithFriend.objects.filter(shared_by=user).count(),
        'friend_comment_count': FriendComment.objects.filter(commenter=user).count(),
        'community_posts': PublicPost.objects.filter(user=user, is_active=True).count(),
        'community_reactions_given': PostReaction.objects.filter(user=user).count(),
        'community_reactions_received': PostReaction.objects.filter(post__user=user).count(),
        'sleep_logs': DailySleep.objects.filter(user=user).count(),
        # Non-manual = synced from Health Connect / Apple Health
        'health_synced': HealthMetric.objects.filter(user=user).exclude(source='manual').count(),
        'habits_count': Habit.objects.filter(user=user, is_active=True).count(),
        'assessments_count': SelfAssessment.objects.filter(user=user).count(),
        'wellness_sessions': WellnessSession.objects.filter(user=user).count(),
        # DashboardLayout exists ⇒ user customized at least once
        'dashboard_customized': 1 if DashboardLayout.objects.filter(user=user).exists() else 0,
    }
    # Single-day step goal 10k
    step_10k_hit = HealthMetric.objects.filter(
        user=user, metric_type='steps', value__gte=10000,
    ).exists()
    longest_sleep_streak = _get_longest_sleep_streak(user)
    longest_habit_streak = _get_longest_habit_streak(user)
    quality_sleep_hit = _get_quality_sleep_week(user)

    # Meta: count of currently-unlocked achievements
    # (computed BEFORE this run's unlocks — the check_achievements caller
    # will re-run if any meta achievements just crossed their threshold.)
    unlocked_count = UserAchievement.objects.filter(user=user).count()

    result = {
        'first_note': note_count,
        'notes_10': note_count,
        'notes_50': note_count,
        'notes_100': note_count,
        'long_writer': max_len,
        'streak_3': longest_streak,
        'streak_7': longest_streak,
        'streak_30': longest_streak,
        'mood_explorer': mood_buckets,
        'positive_streak': 3 if _has_positive_streak(user) else 0,
        'mood_improver': 3 if _has_mood_improving(user) else 0,
        'self_aware': note_agg['ai_analyzed'],
        'first_share': other_counts['share_count'],
        'first_booking': other_counts['booking_count'],
        'first_ai_chat': other_counts['ai_session_count'],
        'ai_chat_10': other_counts['ai_session_count'],
        'night_owl': 1 if note_agg['has_night'] > 0 else 0,
        'early_bird': 1 if note_agg['has_early'] > 0 else 0,
        'pin_master': note_agg['pinned_count'],
        # New achievements
        'notes_200': note_count,
        'first_image': other_counts['image_count'],
        'weekend_warrior': 1 if has_weekend else 0,
        'dedicated_months_3': distinct_months,
        'stress_manager': note_agg['low_stress_count'],
        'emotional_range': emotional_range,
        'conversation_starter': other_counts['conversation_count'],
        'messages_50': other_counts['message_count'],
        'tag_collector': tag_count,
        'weather_logger': weather_count,
        'feedback_giver': other_counts['feedback_count'],
        # NEW: friends
        'first_friend': new_counts['friend_count'],
        'friends_5': new_counts['friend_count'],
        'first_friend_share': new_counts['friend_share_count'],
        'friend_supporter': new_counts['friend_comment_count'],
        # NEW: community
        'first_community_post': new_counts['community_posts'],
        'community_supporter': new_counts['community_reactions_given'],
        'community_voice': new_counts['community_reactions_received'],
        # NEW: health
        'first_sleep_log': new_counts['sleep_logs'],
        'sleep_streak_7': longest_sleep_streak,
        'quality_sleeper': quality_sleep_hit,
        'first_health_sync': new_counts['health_synced'],
        'step_goal_10k': 1 if step_10k_hit else 0,
        # NEW: wellness expanded
        'first_habit': new_counts['habits_count'],
        'habit_streak_7': longest_habit_streak,
        'habit_streak_30': longest_habit_streak,
        'first_breathing': new_counts['wellness_sessions'],
        'wellness_sessions_10': new_counts['wellness_sessions'],
        # NEW: explore expanded
        'first_assessment': new_counts['assessments_count'],
        'assessment_regular': new_counts['assessments_count'],
        'dashboard_customized': new_counts['dashboard_customized'],
        'ai_chat_50': other_counts['ai_session_count'],
        # NEW: meta (compares against the OTHER achievements unlocked)
        'achievement_hunter': unlocked_count,
        'achievement_legend': unlocked_count,
    }

    # === 2026-05-24 expansion: progress for the 55 new achievements ===
    # Compute extra metrics needed by the new definitions. All defensive —
    # any helper that hits a missing row just returns 0.
    long_notes_300 = _long_notes_count(user, threshold=300)
    happy_week = _happy_week_hit(user)
    calm_week = _calm_week_hit(user)
    has_comeback = _has_7day_gap_and_returned(user)
    step_streak = _get_step_streak(user, threshold=10000)
    health_types = _distinct_health_types_synced(user)
    breathing_min = _breathing_minutes_total(user)
    meditation_n = _meditation_count(user)
    breathing_streak = _breathing_day_streak(user)
    wellness_types = _wellness_session_type_count(user)
    activities_n = _distinct_activities_in_metadata(user)
    weather_types_n = _distinct_weather_in_metadata(user)
    features_used = _features_used_count(user)
    early_sleeps = _early_sleeper_count(user)
    top_post_reactions = _community_top_post_reactions(user)
    community_post_dates = _community_post_distinct_dates(user)
    ai_chat_streak = _daily_ai_chat_streak(user)
    shares_recv = _shares_received(user)

    result.update({
        # writing (extended)
        'notes_500': note_count,
        'notes_1000': note_count,
        'words_1k_note': max_len,
        'morning_writer': note_agg['morning_notes'],
        'evening_writer': note_agg['evening_notes'],
        'midnight_writer': note_agg['midnight_notes'],
        'photo_album': other_counts['image_count'],
        'detailed_writer': long_notes_300,
        # consistency (extended)
        'streak_14': longest_streak,
        'streak_60': longest_streak,
        'streak_100': longest_streak,
        'streak_365': longest_streak,
        'comeback_kid': has_comeback,
        # mood (extended)
        'happy_week': happy_week,
        'calm_week': calm_week,
        'emotional_spectrum': mood_buckets,
        'mood_journal_50': note_agg['ai_analyzed'],
        # health (extended)
        'sleep_streak_14': longest_sleep_streak,
        'sleep_streak_30': longest_sleep_streak,
        'sleep_logger_30': new_counts['sleep_logs'],
        'early_sleeper': early_sleeps,
        'step_streak_7': step_streak,
        'step_streak_30': step_streak,
        'health_sync_100': new_counts['health_synced'],
        'health_data_diverse': health_types,
        # wellness (extended)
        'habit_count_3': new_counts['habits_count'],
        'habit_count_5': new_counts['habits_count'],
        'breathing_minutes_30': breathing_min,
        'breathing_minutes_120': breathing_min,
        'meditation_sessions_30': meditation_n,
        'wellness_master_100': new_counts['wellness_sessions'],
        'breathing_streak_7': breathing_streak,
        'diverse_wellness': wellness_types,
        # explore (extended)
        'tag_collector_30': tag_count,
        'all_features_tried': features_used,
        'diverse_activities': activities_n,
        'weather_diversity': weather_types_n,
        'assessment_master_10': new_counts['assessments_count'],
        'pin_master_10': note_agg['pinned_count'],
        # AI (extended)
        'ai_chat_100': other_counts['ai_session_count'],
        'ai_chat_500': other_counts['ai_session_count'],
        'daily_ai_chat_7': ai_chat_streak,
        # friends (extended)
        'friends_10': new_counts['friend_count'],
        'friends_25': new_counts['friend_count'],
        'friend_share_10': new_counts['friend_share_count'],
        'friend_comment_25': new_counts['friend_comment_count'],
        'friend_share_received_5': shares_recv,
        # community (extended)
        'community_posts_5': new_counts['community_posts'],
        'community_posts_20': new_counts['community_posts'],
        'community_top_post': top_post_reactions,
        'community_active_10': community_post_dates,
        'reactions_given_50': new_counts['community_reactions_given'],
        # meta (extended)
        'achievement_master': unlocked_count,
        'achievement_god': unlocked_count,
    })

    cache.set(cache_key, result, _PROGRESS_CACHE_TTL)
    return result


def check_achievements(user):
    """Check all achievement conditions and unlock any new ones.

    Two-pass: meta achievements (achievement_hunter, achievement_legend)
    count *currently-unlocked* achievements. When a single call unlocks
    several normal achievements, the meta count needs to reflect the new
    total. We loop until no new unlocks happen (capped at 5 iterations
    to defend against bugs causing an unlock loop).
    """
    # Mutations may have happened since the last cache snapshot — start
    # fresh so we don't miss a threshold the caller's action just crossed.
    invalidate_progress_cache(user)
    newly_unlocked = []
    for _iteration in range(5):
        existing = set(
            UserAchievement.objects.filter(user=user).values_list('achievement_id', flat=True)
        )
        progress = _get_progress(user)
        unlocked_this_pass = []
        for aid, defn in ACHIEVEMENT_DEFINITIONS.items():
            if aid in existing:
                continue
            # hidden=True means the feature backing this achievement is
            # currently disabled (e.g. counselor flows pre-launch). Don't
            # auto-unlock or notify — the achievement would feel out-of-place.
            if defn.get('hidden'):
                continue
            current = progress.get(aid, 0)
            if current >= defn['threshold']:
                UserAchievement.objects.create(user=user, achievement_id=aid)
                unlocked_this_pass.append(aid)
        if not unlocked_this_pass:
            break
        # Meta achievements count unlocks — invalidate before the next pass.
        invalidate_progress_cache(user)
        newly_unlocked.extend(unlocked_this_pass)
    # Surface each unlock as a Notification so the WebSocket fan-out
    # delivers a real-time toast wherever the user is in the app —
    # the previous flow only showed a toast on the Achievements page.
    if newly_unlocked:
        _emit_unlock_notifications(user, newly_unlocked)
    return newly_unlocked


def _emit_unlock_notifications(user, achievement_ids):
    """Create + fan out a Notification for each newly unlocked achievement.

    Translation of the title/body is done client-side via the achievement
    id stored in ``data.achievement_id`` — the message field carries a
    fallback string for clients that don't translate.
    """
    for aid in achievement_ids:
        defn = ACHIEVEMENT_DEFINITIONS.get(aid, {})
        notification = Notification.objects.create(
            user=user,
            type='achievement',
            title='Achievement unlocked',
            message=aid,
            data={
                'achievement_id': aid,
                'category': defn.get('category', ''),
                'icon': defn.get('icon', 'trophy'),
            },
        )
        # Best-effort WS push — same pattern as save_message in consumers.py.
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            layer = get_channel_layer()
            if layer is not None:
                async_to_sync(layer.group_send)(
                    f'notifications_{user.id}',
                    {
                        'type': 'notify',
                        'data': {
                            'id': notification.id,
                            'type': notification.type,
                            'title': notification.title,
                            'message': notification.message,
                            'data': notification.data,
                            'is_read': False,
                            'created_at': notification.created_at.isoformat(),
                        },
                    },
                )
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                'Achievement notification fan-out failed user=%s aid=%s', user.id, aid,
            )
        # Also fire a web-push so users see the unlock when they're not
        # actively in the tab. Wrapped in try so a missing VAPID key or a
        # 410 from a stale subscription never blocks the achievement save.
        try:
            from api.views import send_push_notification
            send_push_notification(
                user,
                'Achievement unlocked',
                aid,
                url='/achievements',
            )
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                'Achievement push failed user=%s aid=%s', user.id, aid,
            )


def get_user_achievements_with_progress(user):
    """Return all achievements with progress info and unlock status."""
    unlocked = {
        ua.achievement_id: ua.unlocked_at
        for ua in UserAchievement.objects.filter(user=user)
    }
    progress = _get_progress(user)

    result = []
    for aid, defn in ACHIEVEMENT_DEFINITIONS.items():
        # Hidden achievements (counselor-coupled, pre-launch) are excluded
        # from the listing entirely — but if a user already has one unlocked
        # from before the flag was added, surface it so we don't appear to
        # silently strip a trophy from their profile.
        if defn.get('hidden') and aid not in unlocked:
            continue
        current = progress.get(aid, 0)
        threshold = defn['threshold']
        result.append({
            'id': aid,
            'category': defn['category'],
            'icon': defn['icon'],
            'name_key': defn['name_key'],
            'desc_key': defn['desc_key'],
            'threshold': threshold,
            'current': min(current, threshold),
            'unlocked': aid in unlocked,
            'unlocked_at': unlocked.get(aid),
        })
    return result
