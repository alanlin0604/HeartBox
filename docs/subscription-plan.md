# HeartBox Subscription Plan

## Overview

HeartBox adopts a freemium model with a generous free tier and premium subscription for advanced features. This document outlines the subscription tiers, pricing, and implementation considerations.

---

## Pricing Tiers

### Free Tier (Basic)

**Price**: $0/month

**Features**:
- Unlimited journal entries (text only)
- Basic AI sentiment analysis
- Mood trends (last 7 days)
- 3 AI chat sessions/month
- Basic self-assessments (PHQ-9, GAD-7)
- Year Pixels view
- 1 breathing exercise
- Community articles access

**Limits**:
- Max 5 image attachments/month
- No PDF/CSV export
- No weekly summary AI insights
- No therapist report generation
- No note sharing with counselors
- No custom templates (max 2)
- Ads shown (non-intrusive banner)

---

### Premium Tier

**Price**: NT$149/month (~$4.99 USD) or NT$1,190/year (~$39.99 USD, ~33% savings)

**Free Trial**: 14 days (no credit card required for first 7 days)

**Everything in Free, plus**:
- Unlimited image attachments
- PDF & CSV export
- Weekly AI summary with personalized insights
- Unlimited AI chat sessions
- Therapist report generation & sharing
- Note sharing with counselors
- Advanced analytics (weather correlation, activity correlation, sleep-mood, stress by tag)
- Calendar heatmap with click-through
- Custom templates (unlimited)
- All breathing & meditation exercises
- Full course library access
- Priority AI response
- No ads

---

### Professional Tier (Future Consideration)

**Price**: NT$299/month (~$9.99 USD) or NT$2,390/year (~$79.99 USD)

**Everything in Premium, plus**:
- Multi-device sync
- End-to-end encrypted cloud backup
- Voice journal entries with transcription
- AI-powered journal prompts tailored to personal history
- Advanced trend reports (monthly/quarterly)
- API access for personal integrations
- Priority support

---

## Competitive Benchmark

| App | Free Tier | Premium Monthly | Premium Yearly | Trial |
|-----|-----------|-----------------|----------------|-------|
| Daylio | Yes (with ads) | $4.99 | $35.99 | 7 days |
| MoodFit | Yes | $10.00 | $40.00 | 7 days |
| Bearable | Yes | $5.99 | $39.99 | 14 days |
| Reflectly | No | $9.99 | $47.99 | 7 days |
| **HeartBox** | **Yes** | **$4.99 (NT$149)** | **$39.99 (NT$1,190)** | **14 days** |

---

## Implementation Roadmap

### Phase 1: Foundation (Backend)
1. Add `SubscriptionPlan` model (free/premium/professional)
2. Add `UserSubscription` model (user, plan, status, start_date, end_date, payment_provider)
3. Create subscription middleware to check feature access
4. Add `@requires_plan('premium')` decorator for premium-only API endpoints
5. Implement trial period logic (14-day auto-start on registration)

### Phase 2: Payment Integration
1. Integrate Stripe (international) + ECPay/NewebPay (Taiwan local)
2. Implement webhook handlers for payment events
3. Handle subscription lifecycle (create, renew, cancel, expire)
4. Implement graceful degradation on expiry (don't delete data, just limit features)

### Phase 3: Frontend
1. Add subscription status to user profile API
2. Create pricing page component
3. Add feature gates (show upgrade prompts for locked features)
4. Implement payment flow UI (Stripe Checkout / local gateway redirect)
5. Add subscription management page (current plan, billing history, cancel)

### Phase 4: Feature Gating Details

| Feature | Free | Premium |
|---------|------|---------|
| `POST /api/notes/` attachments | 5/month | Unlimited |
| `GET /api/export/` | Blocked | Allowed |
| `GET /api/export/csv/` | Blocked | Allowed |
| `GET /api/export/pdf/` | Blocked | Allowed |
| `GET /api/weekly-summary/` | Blocked | Allowed |
| `POST /api/reports/` | Blocked | Allowed |
| `POST /api/notes/:id/share/` | Blocked | Allowed |
| `POST /api/ai-chat/:id/send/` | 3/month | Unlimited |
| `GET /api/analytics/` | Basic (7d) | Full |
| Courses | First 2 free | All |

---

## Revenue Projections (Conservative)

Assuming 1,000 MAU after 6 months:
- Free tier: 85% = 850 users
- Premium: 12% = 120 users x NT$149 = NT$17,880/month
- Professional: 3% = 30 users x NT$299 = NT$8,970/month
- **Monthly revenue**: ~NT$26,850 (~$895 USD)
- **Annual revenue**: ~NT$322,200 (~$10,740 USD)

With annual plans (higher retention):
- 40% annual subscribers = ~NT$380,000/year estimated

---

## Migration Strategy (Existing Users)

1. All existing users are grandfathered into a **6-month Premium trial**
2. Send email notification 30 days before trial ends
3. Send reminder at 7 days and 1 day before expiry
4. On expiry: gracefully downgrade to Free tier (no data loss)
5. Show non-intrusive upgrade prompts in the UI

---

## Technical Notes

- Store subscription state in JWT claims for fast middleware checks
- Cache subscription status with 5-minute TTL to reduce DB lookups
- Use feature flags for gradual rollout
- All payment operations should be idempotent
- Log all subscription state changes to AuditLog

---

*Last updated: 2026-02-20*
