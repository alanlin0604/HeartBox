import api from './axios';
import { getCached, setCache, invalidate } from './cache';

/** Invalidate all friend-related caches */
const invalidateFriendsCaches = () => {
  invalidate('friends');
  invalidate('friendRequests');
  invalidate('sharedNotes');
  invalidate('friendActivity');
};

// ============ Friend Management APIs ============

/** Get friend list */
export const getFriends = () => {
  const key = 'friends:list';
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get('/friends/').then(res => {
    setCache(key, res, 60_000);
    return res;
  });
};

/** Search users */
export const searchUsers = (query) => {
  return api.post('/friends/search/', { query });
};

/** Send friend request */
export const sendFriendRequest = (to_user_id, message = '') => {
  invalidateFriendsCaches();
  return api.post('/friends/requests/', { to_user_id, message });
};

/** Get received friend requests */
export const getReceivedRequests = () => {
  const key = 'friendRequests:received';
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get('/friends/requests/received/').then(res => {
    setCache(key, res, 30_000);
    return res;
  });
};

/** Get sent friend requests */
export const getSentRequests = () => {
  const key = 'friendRequests:sent';
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get('/friends/requests/sent/').then(res => {
    setCache(key, res, 30_000);
    return res;
  });
};

/** Accept friend request */
export const acceptFriendRequest = (id) => {
  invalidateFriendsCaches();
  return api.post(`/friends/requests/${id}/accept/`);
};

/** Reject friend request */
export const rejectFriendRequest = (id) => {
  invalidateFriendsCaches();
  return api.post(`/friends/requests/${id}/reject/`);
};

/** Remove friend */
export const removeFriend = (friend_id) => {
  invalidateFriendsCaches();
  return api.delete(`/friends/${friend_id}/`);
};

// ============ Note Sharing APIs ============

/** Share note with friends */
export const shareNoteWithFriends = (note_id, friend_ids) => {
  invalidate('sharedNotes');
  return api.post('/friends/share-note/', { note_id, friend_ids });
};

/** Revoke share */
export const revokeShare = (share_id) => {
  invalidate('sharedNotes');
  return api.delete(`/friends/share/${share_id}/`);
};

/** Get notes shared with me */
export const getSharedWithMe = (page = 1) => {
  const key = `sharedNotes:withMe:${page}`;
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get(`/friends/shared-with-me/?page=${page}`).then(res => {
    setCache(key, res, 30_000);
    return res;
  });
};

/** Get notes shared by me */
export const getSharedByMe = (page = 1) => {
  const key = `sharedNotes:byMe:${page}`;
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get(`/friends/shared-by-me/?page=${page}`).then(res => {
    setCache(key, res, 30_000);
    return res;
  });
};

/** Get shared note detail */
export const getSharedNoteDetail = (share_id) => {
  const key = `sharedNote:${share_id}`;
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get(`/friends/share/${share_id}/detail/`).then(res => {
    setCache(key, res, 30_000);
    return res;
  });
};

// ============ Comment APIs ============

/** Add comment to shared note */
export const addComment = (share_id, content) => {
  invalidate(`sharedNote:${share_id}`);
  invalidate('sharedNotes');
  return api.post(`/friends/share/${share_id}/comment/`, { content });
};

/** Get comments for shared note */
export const getComments = (share_id) => {
  const key = `comments:${share_id}`;
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get(`/friends/share/${share_id}/comments/`).then(res => {
    setCache(key, res, 30_000);
    return res;
  });
};

/** Delete comment */
export const deleteComment = (comment_id) => {
  invalidate('sharedNotes');
  return api.delete(`/friends/comment/${comment_id}/`);
};

// ============ Activity APIs ============

/** Get friend activity */
export const getFriendActivity = (hours = 24) => {
  const key = `friendActivity:${hours}h`;
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get(`/friends/activity/?hours=${hours}`).then(res => {
    setCache(key, res, 60_000);
    return res;
  });
};
