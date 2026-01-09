# Selling Orbis - Launch Plan

## Overview

This document outlines the steps to monetize Orbis, from payment integration to public launch.

**Target Timeline:** 2-3 weeks
**Goal:** First paying customers

---

## 1. Stripe Integration

### 1.1 Setup (Day 1)

- [ ] Create Stripe account at https://stripe.com
- [ ] Get API keys (test mode first)
- [ ] Add to `.env`:
  ```
  STRIPE_SECRET_KEY=sk_test_...
  STRIPE_PUBLISHABLE_KEY=pk_test_...
  STRIPE_WEBHOOK_SECRET=whsec_...
  STRIPE_PRICE_ID_MONTHLY=price_...
  STRIPE_PRICE_ID_YEARLY=price_...
  STRIPE_PRICE_ID_LIFETIME=price_...
  ```

### 1.2 Database Model (Day 1)

Create `models/subscription.py`:
```python
class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    tier = db.Column(db.String(20), default="free")  # free, pro, lifetime
    stripe_customer_id = db.Column(db.String(255), nullable=True)
    stripe_subscription_id = db.Column(db.String(255), nullable=True)
    current_period_end = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
```

### 1.3 Pricing Tiers

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | 5 todos, 3 habits, 2 dailies, no calendar sync |
| **Pro Monthly** | $5/mo | Unlimited everything, Google Calendar sync, goals |
| **Pro Yearly** | $40/yr | Same as Pro Monthly (33% discount) |
| **Lifetime** | $60 | Forever access, all Pro features |

### 1.4 Backend Implementation (Day 2-3)

Create `blueprints/billing.py`:

```python
# Key endpoints:
POST /api/billing/create-checkout     # Redirect to Stripe Checkout
POST /api/billing/webhook             # Handle Stripe events
GET  /api/billing/portal              # Customer portal for managing subscription
GET  /billing                         # Billing page with current plan
```

**Stripe Checkout Flow:**
1. User clicks "Upgrade to Pro"
2. Backend creates Stripe Checkout Session
3. User completes payment on Stripe
4. Webhook receives `checkout.session.completed`
5. Update user's subscription tier

**Webhook Events to Handle:**
- `checkout.session.completed` → Activate subscription
- `customer.subscription.updated` → Update period end
- `customer.subscription.deleted` → Downgrade to free
- `invoice.payment_failed` → Send warning email

### 1.5 Feature Gating (Day 3)

Create decorator in `utilities.py`:
```python
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def requires_pro(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.subscription or current_user.subscription.tier == 'free':
            flash('This feature requires Pro. Upgrade to unlock!', 'warning')
            return redirect(url_for('billing.pricing'))
        return f(*args, **kwargs)
    return decorated_function
```

**Features to Gate:**
- [ ] Google Calendar sync → Pro only
- [ ] Goals feature → Pro only
- [ ] Unlimited todos/habits/dailies → Pro only (free has limits)
- [ ] Notes with attachments → Pro only

### 1.6 Free Tier Limits

```python
FREE_LIMITS = {
    'todos': 10,
    'habits': 5,
    'dailies': 3,
    'goals': 0,  # Pro only
    'notes': 5,
}
```

Check limits before creating items.

---

## 2. Landing Page

### 2.1 Structure (Day 4-5)

Create `templates/landing.html` (public, no login required):

```
┌─────────────────────────────────────────────────┐
│  Header: Logo | Features | Pricing | Login      │
├─────────────────────────────────────────────────┤
│  Hero Section                                   │
│  "Organize Your Life with Google Calendar Sync" │
│  [Try Free] [See Pricing]                       │
├─────────────────────────────────────────────────┤
│  Features (3-4 cards)                           │
│  📅 Calendar Sync | ✅ Habits | 🎯 Goals        │
├─────────────────────────────────────────────────┤
│  Screenshot / Demo GIF                          │
├─────────────────────────────────────────────────┤
│  Pricing Table                                  │
│  Free | Pro $5/mo | Lifetime $60               │
├─────────────────────────────────────────────────┤
│  Testimonials (add later)                       │
├─────────────────────────────────────────────────┤
│  FAQ                                            │
├─────────────────────────────────────────────────┤
│  Footer: Privacy | Terms | Contact              │
└─────────────────────────────────────────────────┘
```

### 2.2 Key Messaging

**Headline Options:**
- "The Habit Tracker That Actually Syncs With Your Calendar"
- "Organize Your Life – Habits, Todos, Goals in One Place"
- "Your Life, Organized. With Real Google Calendar Sync."

**Unique Selling Points:**
1. **Google Calendar Sync** – See habits/todos in your calendar
2. **Swiss Hosting** – Your data stays in Switzerland
3. **All-in-One** – Todos, habits, dailies, goals in one app
4. **No Subscription Lock-in** – Lifetime option available

### 2.3 Screenshots Needed

- [ ] Dashboard with todos and habits
- [ ] Google Calendar with synced events
- [ ] Mobile view (responsive)
- [ ] Goals with milestones

### 2.4 Legal Pages

- [ ] Privacy Policy (`/privacy`) – Use generator, customize
- [ ] Terms of Service (`/terms`) – Use generator, customize
- [ ] Imprint/Contact (`/imprint`) – Required for EU

**Free Generators:**
- https://www.privacypolicygenerator.info/
- https://www.termsofservicegenerator.net/

---

## 3. Launch Strategy

### 3.1 Pre-Launch Checklist

- [ ] Stripe in live mode (switch from test keys)
- [ ] All payment flows tested with real card
- [ ] Error monitoring setup (Sentry free tier)
- [ ] Analytics setup (Plausible or Umami)
- [ ] Landing page live at root URL
- [ ] Privacy Policy & Terms published
- [ ] Welcome email working
- [ ] Receipt emails from Stripe

### 3.2 Launch Day Platforms

**Day 1: Product Hunt**
- Schedule for Tuesday-Thursday, 12:01 AM PT
- Prepare:
  - [ ] Tagline (60 chars): "Habit tracker with real Google Calendar sync"
  - [ ] Description (260 chars)
  - [ ] 5 screenshots/GIFs
  - [ ] Maker comment ready
  - [ ] Ask 5-10 friends to upvote + comment early

**Day 1-2: Reddit**
Post in these subreddits (stagger by 24h to avoid spam flags):
- [ ] r/productivity (~2M members)
- [ ] r/getdisciplined (~1M members)
- [ ] r/ADHD (~1.7M members) – position as "simple, not overwhelming"
- [ ] r/habitica (~50K) – "looking for alternatives" posts
- [ ] r/selfhosted – if you open-source later

**Day 2: Hacker News**
- [ ] "Show HN: Orbis – habit tracker with Google Calendar sync"
- Post at 8-9 AM ET for best visibility
- Be ready to answer questions for 2-3 hours

**Day 3+: Twitter/X**
- [ ] Launch thread with demo GIF
- [ ] Tag productivity influencers
- [ ] Use hashtags: #buildinpublic #productivity #habits

### 3.3 Launch Post Templates

**Product Hunt Tagline:**
> Habit & task manager with real Google Calendar sync 📅

**Reddit Post (r/productivity):**
```
Title: I built a habit tracker that actually syncs with Google Calendar

Hey r/productivity!

After being frustrated that Todoist/Habitica don't sync properly with
Google Calendar, I built Orbis.

What it does:
- Todos, habits, dailies, and goals in one place
- Real two-way Google Calendar sync (see your habits as calendar events!)
- Streak tracking with freeze days
- Free tier available, Pro is $5/mo

I'm a solo dev and would love feedback. What features would make this
more useful for you?

Try it: https://orbis.zumgugger.ch
```

**Hacker News:**
```
Title: Show HN: Orbis – Habit tracker with Google Calendar sync

I built Orbis because existing habit trackers (Habitica, Todoist, etc.)
don't sync properly with Google Calendar.

Key features:
- Todos, habits, dailies, goals
- Two-way Google Calendar sync
- Streaks with freeze days
- Swiss-hosted (GDPR compliant)

Stack: Flask, PostgreSQL, Google Calendar API, hosted in Switzerland.

Would love feedback from the HN community.

https://orbis.zumgugger.ch
```

### 3.4 Week 1 Metrics to Track

| Metric | Target |
|--------|--------|
| Landing page visits | 500+ |
| Signups | 50+ |
| Free → Pro conversion | 5-10% |
| First revenue | $25+ |

### 3.5 Post-Launch (Week 2+)

- [ ] Respond to all comments/feedback
- [ ] Fix bugs reported by users
- [ ] Write blog post: "Why I Built a Habitica Alternative"
- [ ] Start weekly "build in public" updates on Twitter
- [ ] Collect testimonials from early users
- [ ] Consider AppSumo lifetime deal (high volume, low margin)

---

## Budget Summary

| Item | Cost |
|------|------|
| Hosting (existing) | ~€10/mo |
| Stripe fees | 2.9% + €0.25/transaction |
| Domain (if new) | ~€10/year |
| Product Hunt | Free |
| Reddit/HN | Free |
| **Total to launch** | **~€0** |

---

## Success Criteria

| Milestone | Target Date | Goal |
|-----------|-------------|------|
| Stripe working | Day 3 | Test payment completes |
| Landing page live | Day 5 | Public URL accessible |
| Launch on PH | Day 7 | 50+ upvotes |
| First paying customer | Day 10 | $5+ revenue |
| 10 paying customers | Day 30 | $50+/month |
| Break even | Day 60 | Revenue > hosting costs |

---

## Notes

- Start with manual onboarding for first 10 users (learn what they need)
- Don't over-engineer – launch fast, iterate based on feedback
- Swiss hosting is a differentiator – emphasize it
- Lifetime deals create urgency and cash flow early
