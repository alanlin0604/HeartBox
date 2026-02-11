# MoodNotes Pro QA Checklist

## UX / Experience

1. Remember me
- Login with remember checked.
- Close/reopen browser, user remains logged in.
- Login with remember unchecked.
- Close/reopen browser, user is logged out.

2. Password show/hide
- Verify toggle on login/register/settings password fields.

3. Toast notifications
- Verify success and error toasts on form actions.

4. Delete confirmation modal
- Open note detail and delete.
- Confirm modal appears and respects cancel/confirm.

5. Empty states
- Dashboard empty sections show CTA.
- Counselor list empty state shows CTA.
- Notification panel empty state shows CTA.

6. Skeleton loading
- Navigate between heavy pages and verify skeletons show.

## Features

7. Note editing
- Edit note content and metadata; save and verify persisted.

8. Forgot/reset password
- Submit forgot password email.
- Open reset link and set new password.
- Login with new password succeeds.

9. Avatar upload
- Upload avatar in settings.
- Verify avatar in navbar, chat header/messages, counselor list.

10. Search highlight
- Search keyword in journal list.
- Matched text is highlighted in note previews.

11. PWA support
- Verify `manifest.json` and service worker load.
- Test installability on HTTPS.

## Security / Technical

12. API rate limiting
- Trigger repeated login/register calls.
- Verify throttling returns 429 after threshold.

13. Password strength indicator
- Weak/medium/strong changes as user types.

14. Logout other devices
- Login on two devices.
- Use "Log Out Other Devices" on one.
- Verify other device token becomes invalid.
