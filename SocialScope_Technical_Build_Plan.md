SocialScope — Technical Build Plan
1. Project Overview
SocialScope is a self-hosted Social Media Intelligence and Growth Analytics
platform.
Core objective
Allow a user to add a public social-media profile/page URL or handle and,
where publicly accessible and permitted, collect profile and content metrics over
time. The system stores historical snapshots, calculates growth and engagement
analytics, detects unusual changes, and presents results in a dashboard.
Initial platforms
• Instagram
• X (Twitter)
• Facebook Pages
Core principle
SocialScope is an analytics platform with collectors, not simply a scraper.
Public profile/page
↓
Platform collector
↓
Parser / normalizer
↓
Historical database
↓
Analytics engine
↓
FastAPI
↓
React dashboard
The system must not attempt to bypass CAPTCHAs, authentication barriers,
rate limits, access controls, or other platform protections. When a metric is un-
available, store it as unavailable/null rather than circumventing the restriction.
2. Product Goals
1. Add and monitor social-media profiles.
2. Collect publicly accessible profile information.
3. Collect publicly accessible recent content and visible engagement metrics.
1

--- PAGE ---

4. Store historical snapshots instead of overwriting previous observations.
5. Calculate follower growth, growth percentage, growth velocity, engage-
ment, posting frequency, content performance, and anomalies.
6. Provide interactive dashboards.
7. Compare multiple profiles and platforms.
8. Export collected and derived data.
9. Provide auditable collection history.
10. Keep platform collectors modular and replaceable.
Non-goals for MVP
• CAPTCHA/anti-bot bypass
• Private-account access
• Credential harvesting
• Password storage
• Proxy rotation designed to evade restrictions
• Large-scale distributed scraping
• Identity resolution as a definitive claim
• Sentiment analysis
• LLM-based primary analytics
• Automated posting/scheduling
• 100+ platforms
3. Recommended Stack
Backend
• Python 3.12+
• FastAPI
• Pydantic
• SQLAlchemy 2.x
• Alembic
• Uvicorn
Database
• PostgreSQL
Browser collection
• Playwright preferred over Selenium for the initial implementation.
• Collector interfaces must not depend directly on Playwright so Selenium
or another implementation can be introduced later.
2

--- PAGE ---

F rontend
• React
• TypeScript
• Vite
• Tailwind CSS
• Recharts or another maintained charting library
Scheduling
• APScheduler initially
• Celery + Redis only if scale later requires it
Infrastructure
• Docker
• Docker Compose
• Git
• .env configuration
4. High-Level Architecture
SOCIALSCOPE
|
+----------------------+----------------------+
| | |
v v v
Collectors Analytics Dashboard
| | |
v v v
Instagram Growth React UI
Facebook Engagement Charts
X Content Tables
| Anomaly Filters
| |
+----------+-----------+
|
v
PostgreSQL
|
v
FastAPI API
3

--- PAGE ---

5. Repository Structure
socialscope/
￿￿￿ backend/
￿ ￿￿￿ app/
￿ ￿ ￿￿￿ api/
￿ ￿ ￿ ￿￿￿ routes/
￿ ￿ ￿ ￿￿￿ dependencies.py
￿ ￿ ￿￿￿ collectors/
￿ ￿ ￿ ￿￿￿ base.py
￿ ￿ ￿ ￿￿￿ browser/
￿ ￿ ￿ ￿￿￿ instagram/
￿ ￿ ￿ ￿￿￿ facebook/
￿ ￿ ￿ ￿￿￿ x/
￿ ￿ ￿￿￿ analytics/
￿ ￿ ￿ ￿￿￿ growth.py
￿ ￿ ￿ ￿￿￿ engagement.py
￿ ￿ ￿ ￿￿￿ content.py
￿ ￿ ￿ ￿￿￿ frequency.py
￿ ￿ ￿ ￿￿￿ anomalies.py
￿ ￿ ￿ ￿￿￿ comparison.py
￿ ￿ ￿￿￿ database/
￿ ￿ ￿ ￿￿￿ session.py
￿ ￿ ￿ ￿￿￿ base.py
￿ ￿ ￿￿￿ models/
￿ ￿ ￿￿￿ schemas/
￿ ￿ ￿￿￿ services/
￿ ￿ ￿￿￿ scheduler/
￿ ￿ ￿￿￿ config.py
￿ ￿ ￿￿￿ main.py
￿ ￿￿￿ tests/
￿ ￿￿￿ alembic/
￿ ￿￿￿ requirements.txt
￿￿￿ frontend/
￿ ￿￿￿ src/
￿ ￿ ￿￿￿ components/
￿ ￿ ￿￿￿ pages/
￿ ￿ ￿￿￿ charts/
￿ ￿ ￿￿￿ api/
￿ ￿ ￿￿￿ hooks/
￿ ￿ ￿￿￿ types/
￿ ￿￿￿ package.json
￿￿￿ tests/
￿￿￿ docs/
￿￿￿ docker-compose.yml
￿￿￿ .env.example
4

--- PAGE ---

￿￿￿ README.md
6. Collector Architecture
Every platform collector implements a common abstraction:
class BaseCollector:
def validate_target(self, target): ...
def collect_profile(self, target): ...
def collect_posts(self, target): ...
def collect_post_metrics(self, post): ...
Implementations:
BaseCollector
￿￿￿ InstagramCollector
￿￿￿ FacebookCollector
￿￿￿ XCollector
The analytics engine must never contain platform-specific scraping logic.
7. Platform Strategy
Instagram
Target publicly accessible profiles/content and API-supported accounts where
available.
Potential fields:
username
display_name
bio
profile_url
profile_image
followers
following
post_count
verified
posts
likes
comments
views when publicly visible
timestamps
captions
5

--- PAGE ---

media type
hashtags
Do not assume every metric is always available.
X
Potential profile data:
username
display_name
bio
profile_url
followers
following
post count where available
verified
profile image
Potential post data:
post_id
post_url
text
timestamp
likes
replies
reposts
views when publicly visible
media type
hashtags
Browser-session collection may be required for some workflows. Never store an
X password and never commit session cookies to Git.
F acebook
Initial scope is F acebook Pages/public entities , not arbitrary pri-
vate/personal profiles.
Potential data:
page name
page URL
description
followers/likes where publicly available
post count
public posts
timestamps
visible reactions
6

--- PAGE ---

comments
shares
Prefer oﬀicial APIs where applicable.
8. Data Model
Profile
id
platform
platform_profile_id
username
display_name
profile_url
bio
profile_image_url
verified
created_at
updated_at
Profile Snapshot
id
profile_id
collected_at
followers
following
post_count
other_platform_metrics
collector_version
Every collection creates a new snapshot. Never overwrite historical observations.
Post
id
profile_id
platform_post_id
url
caption/text
posted_at
media_type
created_at
updated_at
7

--- PAGE ---

Post Snapshot
id
post_id
collected_at
likes
comments
shares/reposts
views
engagement
Collection Job
id
profile_id
platform
started_at
completed_at
status
records_collected
error_message
collector_version
Statuses:
PENDING
RUNNING
SUCCESS
PARTIAL
FAILED
Anomaly
id
profile_id
detected_at
metric
baseline
observed_value
severity
method
description
9. Historical Snapshot Principle
Historical data is the heart of SocialScope.
8

--- PAGE ---

Example:
Day 1 100,000 followers
Day 2 100,430
Day 3 101,220
Day 4 101,500
Store every observation. Never replace Day 1 with Day 4.
If a profile is added today, SocialScope cannot know its true follower count six
months ago unless a historical source already provides that information.
10. Scheduler and Collection Workflow
Initial scheduler: APScheduler.
Supported schedules:
Manual
Every 6 hours
Every 12 hours
Daily
Workflow:
Scheduler
↓
Find monitored profiles
↓
Create collection job
↓
Run platform collector
↓
Validate data
↓
Store profile snapshot
↓
Store/update posts
↓
Store post snapshots
↓
Run analytics
↓
Mark SUCCESS/PARTIAL/FAILED
Collectors need timeouts, retries, exponential backoff, reasonable request spac-
ing, structured errors, and last-success timestamps. These mechanisms must
not be used to evade platform protections.
9

--- PAGE ---

11. Analytics Engine
Analytics must be deterministic and unit-testable.
Growth
absolute_growth = current_followers - previous_followers
growth_percent = (current - previous) / previous * 100
7D growth = followers_today - followers_7_days_ago
30D growth = followers_today - followers_30_days_ago
growth_velocity = followers_gained / unit_time
Growth acceleration compares recent growth velocity with an earlier equivalent
period.
Engagement
Depending on available metrics:
likes
comments
shares/reposts
views
Calculate:
total engagement
average engagement
median engagement
engagement rate
Where appropriate:
engagement_rate = total_engagement / followers * 100
The formula must be configurable per platform and clearly displayed.
Content analytics
Normalize:
IMAGE
VIDEO
REEL
CAROUSEL
10

--- PAGE ---

TEXT
LINK
THREAD
UNKNOWN
Calculate posts, average/median engagement, views, and posting frequency by
content type.
Do not infer causation from correlations.
Posting behavior
Calculate:
posts/day
posts/week
posts/month
Analyze day of week, hour of day, and posting intervals. Present these as de-
scriptive observations.
T op content
Sort by:
likes
comments
shares
views
engagement
engagement rate
newest
oldest
12. Anomaly Detection
Initial approach:
• rolling median
• median absolute deviation (MAD)
• optional z-score where appropriate
Example:
Normal follower growth: +300/day
Observed: +8,700/day
Create an anomaly event with the measured baseline and observed value. Do
not speculate about the cause.
11

--- PAGE ---

13. Cross-Platform and Profile Comparison
Allow comparison of multiple monitored profiles.
Metrics:
followers
growth
growth velocity
engagement
posting frequency
content distribution
top posts
Comparison remains descriptive and should not produce subjective “best ac-
count” rankings in the MVP.
14. Dashboard
Main dashboard
Show:
Total monitored profiles
Active collection jobs
Successful collections today
Failed collections
Recent follower growth
Recent anomalies
Top performing content
Profile page
Header:
username
platform
verified state if available
profile URL
last collection time
Metrics:
followers
following
post count
7D growth
12

--- PAGE ---

30D growth
engagement
posting frequency
Tabs:
Overview
Growth
Content
Engagement
Activity
Anomalies
Raw Data
Growth page
Charts:
Follower count
Follower growth
Growth velocity
Growth acceleration
Ranges:
7D
30D
90D
6M
1Y
ALL
Content page
Columns:
Date
Type
Caption/Text
Likes
Comments
Shares
Views
Engagement
Engagement Rate
Collection status
Show:
13

--- PAGE ---

Last successful collection
Last failed collection
Failure reason
Next scheduled collection
Records collected
Collector version
Raw data/audit
Expose collection timestamp, source URL, collector version, extracted fields,
and status.
15. Export
Initial formats:
• CSV
• JSON
• XLSX
Future:
• PDF report
Exports should distinguish raw observations, derived metrics, and anomalies.
16. AI Insights — Phase 2
Do not use an LLM as the primary analytics engine.
Correct flow:
Raw observations
↓
Deterministic analytics
↓
Structured metrics
↓
LLM
↓
Natural-language explanation
Example outputs:
Follower count increased 8.7% over the last 30 days.
Video posts represented 38% of observed posts and accounted
14

--- PAGE ---

for 71% of observed engagement.
An unusually large follower increase occurred on September 19.
The LLM must only summarize supplied metrics and must not invent causes or
missing data.
17. Optional Future OSINT Features
Profile change tracking
• bio changed
• username changed
• profile picture changed
• follower spike
• following spike
Content change tracking
• new post
• deleted post
• changed caption
• engagement changes
Cross-platform signals
Potential signals:
• same username
• same website
• same linked profile
• similar public bio
These must be presented as signals, not definitive identity conclusions.
18. Security Requirements
Never store or commit:
• social-media passwords
• credentials in source code
• cookies in Git
• session tokens in frontend code
Use .env, secret configuration, and encrypted session storage where required.
15

--- PAGE ---

Protect secrets without using overly broad .gitignore rules that accidentally
hide legitimate project files.
19. Testing Strategy
Unit tests
Test:
growth formulas
engagement formulas
anomaly detection
normalization
date calculations
Collector tests
Use saved HTML fixtures where possible:
tests/fixtures/instagram/
tests/fixtures/facebook/
tests/fixtures/x/
Integration tests
Collector → Parser → Normalizer → Database
End-to-end
Add profile
↓
Collect
↓
Store
↓
Analyze
↓
Dashboard
20. MVP Definition
Instagram
• Profile metrics
• Recent publicly accessible posts
• Visible engagement metrics
16

--- PAGE ---

• Historical snapshots
X
• Public profile metrics available to the collector
• Recent publicly accessible posts
• Visible engagement metrics
• Historical snapshots
F acebook
• Public Pages
• Page information
• Public posts
• Visible engagement metrics
• Historical snapshots
Analytics
• 7-day growth
• 30-day growth
• follower graph
• engagement
• top content
• posting frequency
Dashboard
• profile list
• profile overview
• growth chart
• content table
• collection status
• basic comparison
21. Development Phases
Phase 0 — Specification
Create architecture, database schema, API contracts, collector interface, envi-
ronment specification, security model, and folder structure. Do not implement
platform collection yet.
17

--- PAGE ---

Phase 1 — Foundation
Build FastAPI, PostgreSQL, SQLAlchemy, Alembic, React, TypeScript, Tail-
wind, and Docker Compose. Verify frontend → backend → database.
Phase 2 — Database
Implement profiles, profile_snapshots, posts, post_snapshots, collection_jobs,
collection_errors, and anomalies. Create migrations and seed test data.
Phase 3 — Collector Core
Implement BaseCollector, browser abstraction, mock collector, collector registry,
and error handling. Test the complete pipeline with mock data.
Phase 4 — Instagram
Implement profile collection, post collection, visible metrics, normalization,
snapshots, and integration tests.
Phase 5 — X
Implement profile collection, post collection, visible metrics, normalization,
snapshots, and integration tests independently of Instagram.
Phase 6 — Facebook
Start with Pages. Implement page collection, public posts, visible metrics, nor-
malization, snapshots, and integration tests.
Phase 7 — Scheduler
Add manual collection, scheduled collection, collection status, retries, and failure
tracking.
Phase 8 — Analytics
Implement growth, engagement, content, frequency, anomaly detection, and
comparison.
Phase 9 — Dashboard
Implement overview, profile page, growth, content, engagement, anomalies, raw
data, and comparison.
Phase 10 — Export
Add CSV, JSON, and XLSX.
18

--- PAGE ---

Phase 11 — AI Insights
Add LLM summaries over deterministic analytics.
Phase 12 — Hardening
Add authentication, secret management, logging, monitoring, backups, produc-
tion Docker setup, and documentation.
22. Antigravity Build Strategy
Do not ask Antigravity to build the entire project in one prompt.
Use one controlled prompt per phase and inspect the result before continuing.
Recommended sequence:
Prompt 01 → Architecture/specification
Prompt 02 → Project scaffolding
Prompt 03 → Database models
Prompt 04 → Alembic migrations
Prompt 05 → Base collector
Prompt 06 → Mock collector
Prompt 07 → Collection API
Prompt 08 → Instagram collector
Prompt 09 → Instagram tests
Prompt 10 → X collector
Prompt 11 → X tests
Prompt 12 → Facebook collector
Prompt 13 → Facebook tests
Prompt 14 → Scheduler
Prompt 15 → Analytics engine
Prompt 16 → Analytics tests
Prompt 17 → Dashboard foundation
Prompt 18 → Profile dashboard
Prompt 19 → Growth dashboard
Prompt 20 → Content dashboard
Prompt 21 → Comparison
Prompt 22 → Export
Prompt 23 → AI insights
Prompt 24 → Security/hardening
Prompt 25 → Final integration/testing
After every prompt:
1. Run the application.
2. Run tests.
19

--- PAGE ---

3. Inspect generated files.
4. Fix errors.
5. Commit to Git.
6. Only then move to the next prompt.
23. Antigravity Instruction Contract
Every future implementation prompt should instruct Antigravity to:
1. Read this document first.
2. Inspect the existing code before changing anything.
3. Preserve existing working functionality.
4. Implement only the requested phase.
5. Follow the architecture defined here.
6. Write tests for new functionality.
7. Run tests after implementation.
8. Report changed files.
9. Report commands executed.
10. Report remaining limitations.
11. Never silently change the architecture.
12. Never implement access-control or anti-bot bypasses.
13. Never put secrets into source code.
14. Never fabricate unavailable social-media metrics.
24. Definition of Done
The MVP is complete when:
□ Backend starts successfully.
□ PostgreSQL connects.
□ Frontend starts successfully.
□ Profiles can be added.
□ Platform is identified or explicitly selected.
□ Collection jobs can be started manually.
□ Profile snapshots are persisted.
□ Post data is persisted.
□ Repeated collection creates historical snapshots.
□ Instagram collector works within its available access model.
□ X collector works within its available access model.
□ Facebook Page collector works within its available access model.
□ Growth calculations are tested.
□ Engagement calculations are tested.
20

--- PAGE ---

□ Anomaly detection is tested.
□ Dashboard displays historical growth.
□ Top content is displayed.
□ Collection failures are visible.
□ Raw observations can be inspected.
□ CSV/JSON/XLSX export works.
□ No credentials/secrets are committed.
□ Docker Compose reproduces the environment.
□ README documents setup and limitations.
25. Final Target Architecture
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
￿ USER ￿
￿ Profile URL/Handle ￿
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
￿
￿
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
￿ Platform Router ￿
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
￿
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
￿ ￿ ￿
￿ ￿ ￿
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿ ￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿ ￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
￿ Instagram ￿ ￿ X ￿ ￿ Facebook ￿
￿ Collector ￿ ￿ Collector ￿ ￿ Page Collector￿
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿ ￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿ ￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
￿ ￿ ￿
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
￿
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
￿ Parser / Normalizer ￿
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
￿
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
￿ PostgreSQL ￿
￿ Profiles/Snapshots ￿
￿ Posts/Post Snapshots￿
￿ Jobs/Anomalies ￿
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
￿
21

--- PAGE ---

￿
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
￿ Analytics Engine ￿
￿ Growth/Engagement ￿
￿ Content/Frequency ￿
￿ Anomaly/Comparison ￿
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
￿
￿
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
￿ FastAPI ￿
￿ REST API ￿
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
￿
￿
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
￿ React Dashboard ￿
￿ Overview/Growth ￿
￿ Content/Engagement ￿
￿ Anomalies/Compare ￿
￿ Raw Data ￿
￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿￿
26. Guiding Engineering Principles
1. Collectors are isolated from analytics.
2. Every observation is timestamped.
3. Historical snapshots are never overwritten.
4. Platform-specific limitations are represented explicitly.
5. Unavailable metrics are null, not fabricated.
6. Analytics are deterministic and testable.
7. AI only summarizes structured analytics.
8. No credential harvesting.
9. No access-control/CAPTCHA/anti-bot bypass.
10. Do not assume a newly added profile has historical data.
11. Use oﬀicial APIs when they provide the required information.
12. Browser automation is an implementation detail, not the architecture.
13. Every collector must be replaceable independently.
14. One failed platform collector must not break the whole application.
15. Important collection operations must be auditable.
22

--- PAGE ---

Source-of-Truth Rule
This document is the source of truth for the SocialScope build. Future Antigrav-
ity prompts should reference this document rather than redefining the architec-
ture. When implementation realities require a change, update this document
first, then implement the change.
23