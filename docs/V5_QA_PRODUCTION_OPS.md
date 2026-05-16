# v5 Q&A Part 2 — 25 câu hỏi production operations

> **Phụ lục bổ sung cho** `SOLUTION_ARCHITECTURE_V5.md` và `V5_QA_EDGECASES.md`
> **Ngày:** 2026-05-16
> **Phạm vi:** 25 câu hỏi về production operations — data ingestion, MLOps, deployment, security, business ops. Bổ sung cho 25 câu technical edge cases (V5_QA_EDGECASES.md).
> **Mục đích:** Định hình rõ những vấn đề non-ML mà sẽ gặp khi vận hành thực tế, đặc biệt khi scale từ POC → SaaS multi-club.

---

## 📑 Mục lục theo nhóm

- **Nhóm H: Data Ingestion & Storage** (5 câu)
- **Nhóm I: MLOps & Model Lifecycle** (5 câu)
- **Nhóm J: Deployment & Infrastructure** (5 câu)
- **Nhóm K: Security & Access Control** (5 câu)
- **Nhóm L: Business Operations & Cost** (5 câu)

---

## NHÓM H — Data Ingestion & Storage

### Q26. Video file ingestion — upload, streaming, format conversion?

**Vấn đề:**
Bradford gửi video qua nhiều cách: upload Google Drive, YouTube link, send hard drive. Format khác nhau (MP4, MOV, AV1, H.264, H.265). Resolution khác (720p, 1080p, 4K). Bitrate khác. Hệ thống cần handle uniformly.

**Giải pháp v5:**

**Architecture:**
```
┌──────────────────────────────────────┐
│  Ingestion API endpoints              │
│  • POST /upload (multipart, ≤5GB)     │
│  • POST /from-url (S3 presigned, YT)  │
│  • POST /from-storage (mounted disk)  │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Validation                           │
│  • Codec sanity (ffprobe)             │
│  • Duration ≥ 30 min                  │
│  • Resolution ≥ 720p                  │
│  • Audio present? (optional)          │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Normalization (ffmpeg)               │
│  • Re-encode H.264 yuv420p 1080p      │
│  • CRF 18 (visually lossless)         │
│  • 30 fps constant                    │
│  • Strip audio (save space)           │
│  • Output: {video_id}.mp4             │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Metadata extraction                  │
│  • Duration, resolution, bitrate      │
│  • Stadium audio analysis (optional)  │
│  • Add to DB                          │
└──────────────────────────────────────┘
```

**Critical decisions:**
- **Normalize before processing** — eliminates downstream branching
- **Re-encode to standard target** (H.264 1080p 30fps) — predictable inference cost
- **CRF 18** balances quality and storage

**Cost estimate:**
- 90 min match @ 1080p H.264 ~ 2-3 GB
- 10 matches/season × N clubs = 20 GB/club/season — minimal

### Q27. Storage architecture — raw videos, frames, models, reports?

**Vấn đề:**
Multiple data types, multiple lifecycles, multiple access patterns.

**Giải pháp v5 — Tiered storage:**

```
HOT (fast access, expensive):
  • Recent reports (last 30 days)
  • Active model weights
  • Reference banks (DINOv2 embeddings)
  Storage: Local SSD or S3 Standard
  Size estimate: 5-10 GB total

WARM (moderate access):
  • Normalized videos (last 6 months)
  • Selected frames + annotations
  • Cached intermediate results (detections, tracks)
  Storage: S3 Standard-IA or local HDD
  Size estimate: 100-500 GB/club

COLD (archival):
  • Raw uploaded videos (immutable)
  • Old reports (>6 months)
  • Training data snapshots
  Storage: S3 Glacier or Google Cold Line
  Size estimate: 1-3 TB/club/year
```

**Lifecycle automation:**
```python
# Pseudocode
def storage_lifecycle():
    # After 30 days inactivity → move to warm
    # After 6 months → move to cold (Glacier)
    # Audit trail: 7 years (sponsor disputes possible)
```

**Recommendation:** S3 (or equivalent: GCS, Azure Blob) with lifecycle policies. Local-only for POC, cloud for SaaS.

### Q28. Database schema for detections, events, exposure metrics?

**Vấn đề:**
Stage 4-5 produces millions of detection records, thousands of events. Need efficient query.

**Giải pháp v5 — PostgreSQL với extensions:**

```sql
-- Match metadata
CREATE TABLE matches (
    match_id UUID PRIMARY KEY,
    club_id UUID,
    opponent VARCHAR,
    match_date DATE,
    kit_color VARCHAR,  -- 'home' or 'away'
    video_path TEXT,
    duration_seconds NUMERIC,
    processed_at TIMESTAMP,
    pipeline_version VARCHAR
);

-- Tracked players
CREATE TABLE player_tracks (
    track_id UUID PRIMARY KEY,
    match_id UUID REFERENCES matches,
    team VARCHAR,  -- 'bradford', 'opponent', 'unknown'
    first_seen_frame INT,
    last_seen_frame INT,
    total_visible_frames INT
);

-- Per-detection records (large table)
CREATE TABLE detections (
    detection_id BIGSERIAL PRIMARY KEY,
    match_id UUID REFERENCES matches,
    track_id UUID REFERENCES player_tracks,
    frame_idx INT,
    timestamp_ms BIGINT,
    brand_class VARCHAR,
    obb_coords NUMERIC[8],  -- 4 corners
    confidence NUMERIC,
    dinov2_similarity NUMERIC,
    dinov2_margin NUMERIC,
    qi_size NUMERIC,
    qi_position NUMERIC,
    qi_clarity NUMERIC,
    qi_clutter NUMERIC,
    qi_exclusivity NUMERIC,
    qi_total NUMERIC,
    source VARCHAR,  -- 'detected', 'inferred', 'sam2_propagated'
    inferred_position VARCHAR  -- 'chest', 'sleeve', etc.
);

CREATE INDEX ON detections (match_id, brand_class);
CREATE INDEX ON detections (track_id);

-- Aggregated events (computed)
CREATE TABLE exposure_events (
    event_id UUID PRIMARY KEY,
    match_id UUID REFERENCES matches,
    track_id UUID REFERENCES player_tracks,
    brand_class VARCHAR,
    start_frame INT,
    end_frame INT,
    duration_seconds NUMERIC,
    avg_qi NUMERIC,
    is_replay BOOLEAN,
    detection_count INT
);

CREATE INDEX ON exposure_events (match_id, brand_class);
```

**Why PostgreSQL:**
- ACID transactions (audit-grade)
- JSON/array support (OBB coords)
- Free, mature, scales to TB

**For SaaS scale:** Consider Citus extension (sharded Postgres) or TimescaleDB for time-series queries.

### Q29. Data retention — how long to keep raw videos, frames, results?

**Vấn đề:**
Storage cost vs sponsor dispute timeline vs GDPR.

**Giải pháp v5:**

| Data type | Retention | Reason |
|-----------|-----------|--------|
| Raw uploaded video | 7 years | Sponsor contract dispute window (Industry standard) |
| Normalized video | 2 years | Active analysis window |
| Selected frames | 1 year | Re-training data |
| Annotations | Forever | Training corpus |
| Detection records | 3 years | Audit trail for reports |
| Reports | Forever | Permanent reference |
| Intermediate compute results (tracks, etc.) | 90 days | Can re-compute from video |

**GDPR considerations (UK):**
- Player likeness in broadcast video = derivative of public broadcast → fair use for analytics
- BUT: don't expose player names/PII publicly without consent
- Right to be forgotten: tag-based deletion (mark player for exclusion)

### Q30. Handling video corruption / partial uploads?

**Vấn đề:**
Network drops mid-upload, ffmpeg fails on certain codecs, video truncated.

**Giải pháp v5:**

1. **Upload integrity:**
   - Multipart upload with checksum (MD5/SHA256) per chunk
   - Verify on completion → reject if mismatch

2. **Codec robustness:**
   ```python
   try:
       result = subprocess.run(["ffprobe", video_path], capture_output=True, timeout=60)
       metadata = parse_ffprobe(result.stdout)
       if metadata.duration < 30 * 60:
           raise ValueError("Video too short — likely truncated")
   except Exception as e:
       move_to_quarantine(video_path)
       notify_user("Video upload failed validation: " + str(e))
   ```

3. **Graceful degradation in pipeline:**
   - If pipeline encounters corrupt frame mid-video → log + skip + continue
   - Report flags "X% of frames unprocessable" so user knows quality compromised

4. **Retry logic:**
   - Failed processing → retry with different decoder (e.g., libavcodec fallback)
   - 3 retries → human escalation

---

## NHÓM I — MLOps & Model Lifecycle

### Q31. Model versioning strategy?

**Vấn đề:**
v5 has multiple model components (YOLOv11-OBB, DINOv2, BoT-SORT). Each can update independently. How to version?

**Giải pháp v5 — Per-component semantic versioning:**

```
pipeline.version: v5.1.3
├── person_detector: yolov11l_coco_v8.3.0 (pretrained, frozen)
├── logo_detector: yolov11m_obb_bradford_v1.2.0 (fine-tuned, our weights)
├── dinov2_encoder: dinov2_vitb14_meta_v2.1 (pretrained, frozen)
├── reference_bank: bradford_2025_2026_v1.0
├── tracker: botsort_supervision_v0.18 (library)
└── config: qi_v1, replay_handling_v1
```

**Pipeline version bumps when:**
- Major: architectural change (e.g., switch to RT-DETRv2)
- Minor: model component upgrade (logo_detector retrain)
- Patch: config tweak (QI weight adjustment)

**Each report includes pipeline version** → can re-trace which model produced which numbers.

### Q32. Training data versioning?

**Vấn đề:**
Training data evolves (more annotations added each iteration). Need to reproduce old models.

**Giải pháp v5 — DVC (Data Version Control):**

```
data/
├── .dvc/                  # DVC metadata
├── frames/                # gitignored, tracked by DVC
├── annotations/           # gitignored, tracked by DVC
└── splits/
    ├── v1.0_train.txt     # frame IDs in train set
    ├── v1.0_val.txt
    └── v1.0_test.txt
```

**Workflow:**
```bash
# Add new annotations
dvc add data/annotations/
git commit -m "feat: +200 annotations for sleeve sponsors"
git tag annotations-v1.2

# Reproduce model
git checkout annotations-v1.2
dvc pull  # downloads exact data version
python train.py
```

**Alternative:** MLflow Tracking với artifacts logging — simpler nhưng less granular.

### Q33. Continuous training pipeline — when to retrain?

**Vấn đề:**
New matches keep coming. When should we retrain model?

**Giải pháp v5 — Trigger-based retraining:**

| Trigger | Action |
|---------|--------|
| New sponsor added | Update reference bank (no retrain) |
| Sponsor rebrand | Update reference bank (multi-version) |
| New match data with X annotations added | Queue retrain when X >= 100 |
| Model precision drops below 0.85 in production monitoring | Emergency retrain |
| Scheduled monthly | Automated retrain on accumulated new data |
| Kit major redesign (start of season) | Force retrain Stage 3A detector |

**Retrain flow:**
```
1. Snapshot current production model (rollback safety)
2. Pull latest annotations (DVC)
3. Train on extended dataset
4. Cross-validate vs latest 3 matches
5. If new model AP within 2% of current → deploy as canary (10% traffic)
6. After 1 week canary OK → promote to production
7. Else → rollback, investigate
```

### Q34. Model registry — production vs staging vs experiments?

**Vấn đề:**
Multiple model versions co-exist (current prod, candidates, experiments, archived).

**Giải pháp v5 — MLflow Model Registry:**

```
registered_models:
  bradford_logo_detector:
    stages:
      Production: v1.2.0 (active, serving)
      Staging: v1.3.0-rc1 (canary)
      Archived: v1.1.0, v1.0.0
    
  dinov2_embedder:
    stages:
      Production: v2.1 (frozen, never retrained for v1)
    
  reference_bank:
    stages:
      Production: bradford_2025_2026_v1.2
```

**Deployment flow:**
```bash
mlflow models serve -m "models:/bradford_logo_detector/Production" -p 5000
```

**Promotion gate:**
- Staging must pass: AP > 0.85, no class < 0.5 AP, latency < 50ms/frame
- Canary period: 1 week observing in production
- Promote: marked manual approval

### Q35. Model rollback if production regresses?

**Vấn đề:**
New model deployed, sponsor reports complain numbers changed unexpectedly. Need quick rollback.

**Giải pháp v5:**

1. **Blue-green deployment:**
   - Old model (blue) running, new model (green) deployed alongside
   - Switch traffic at router level — instant rollback possible

2. **Automatic rollback triggers:**
   ```python
   def monitor_production():
       last_24h_reports = fetch_recent_reports()
       avg_brand_count = sum(r.brand_count for r in last_24h_reports) / len(...)
       avg_exposure = ...
       
       if avg_exposure_drops > 30% vs last week:
           alert_team()
           auto_rollback_to_previous()
   ```

3. **Manual rollback command:**
   ```bash
   ./scripts/rollback.sh logo_detector v1.1.0
   # Re-points service to old model, no downtime
   ```

4. **Re-process affected reports:**
   - If rollback affects reports already delivered → re-process + send corrected
   - Versioned reports show "Report v1.2 (May 16) updated to v1.3 (May 17): -5% on TopNotch"

---

## NHÓM J — Deployment & Infrastructure

### Q36. On-prem vs cloud — recommendation?

**Vấn đề:**
Where to deploy? On Bradford's servers, on cloud (AWS/GCP/Azure), hybrid?

**Giải pháp v5:**

**POC phase (now):** Google Colab Pro+ ($50/month)
- Pro: Cheap, includes A100, instant setup
- Con: Session limits, not 24/7

**Production v1:** Single cloud GPU instance (~$500-1000/month)
- Recommendation: GCP n1-standard + T4 GPU, OR AWS g4dn.xlarge
- Reason: GPU per-second billing, suspend when not running
- Cost estimate: 1 match = ~$0.50 in compute

**SaaS v3 (multi-club):** Kubernetes on GCP/AWS
- Auto-scale GPU pool based on queue depth
- Spot instances for batch processing (~70% cheaper)

**On-prem only if:** Bradford has strict data residency (UK only) — UK-based cloud OK (AWS London, GCP london).

### Q37. Containerization strategy?

**Vấn đề:**
Reproducible deployment, dependency management.

**Giải pháp v5 — Docker:**

```dockerfile
# Dockerfile.inference
FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

# System deps
RUN apt-get update && apt-get install -y \
    ffmpeg python3.11 python3-pip git wget

# Python deps
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Models (pre-downloaded for fast cold start)
COPY models/ /app/models/
COPY src/ /app/src/

# Entrypoint
CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Image size optimization:**
- Multi-stage build
- Models in separate image layer (cache hit on code change)
- Final size target: <8 GB (acceptable for GPU deployments)

**Orchestration:**
- POC: docker-compose (single host)
- Production: Kubernetes (GKE or EKS) with NVIDIA device plugin

### Q38. GPU allocation — dedicated vs shared, spot vs on-demand?

**Vấn đề:**
GPU expensive. Need to balance cost and SLA.

**Giải pháp v5:**

**For inference (real-time-ish):**
- Dedicated GPU (T4 or A10) — on-demand
- Cost: ~$0.35/hr (T4), $1.20/hr (A10)
- SLA: <2 hr processing per match

**For training (batch, fault-tolerant):**
- Spot GPU (A100, V100) — 70% cheaper
- Checkpoint frequently (every 5 epochs)
- If preempted, resume from checkpoint

**Multi-tenant SaaS:**
- Shared GPU pool with K8s pod scheduling
- Per-club quotas (e.g., max 5 concurrent jobs/club)
- Priority queue: paid tier > free tier

### Q39. API design for inference service?

**Vấn đề:**
How do users submit videos and get results?

**Giải pháp v5 — Async REST API + Webhook:**

```
POST /api/v1/jobs
Body: {
  "video_url": "s3://...",  // or multipart upload
  "club_id": "bradford_bulls",
  "match_metadata": {
    "opponent": "Castleford Tigers",
    "match_date": "2026-03-15",
    "kit_color": "home"
  },
  "callback_url": "https://bradford.com/webhook/sponsor-report"
}

Response: 202 Accepted
{
  "job_id": "abc123",
  "status": "queued",
  "estimated_completion_seconds": 5400
}

# Polling
GET /api/v1/jobs/{job_id}
Response: {
  "status": "processing",
  "progress_pct": 42,
  "current_stage": "logo_detection"
}

# When done, webhook fired:
POST {callback_url}
Body: {
  "job_id": "abc123",
  "status": "completed",
  "report_urls": {
    "csv": "https://...",
    "json": "https://...",
    "pdf": "https://..."
  }
}
```

**Why async:**
- Processing takes hours, can't block HTTP connection
- Webhook for completion notification
- Polling for progress

**Authentication:** API key per club, rate limiting per key.

### Q40. Monitoring — what metrics to track in production?

**Vấn đề:**
How to know if system healthy?

**Giải pháp v5 — Multi-layer monitoring:**

**Infrastructure (Prometheus + Grafana):**
- GPU utilization, memory
- API request rate, latency, error rate
- Queue depth (jobs pending)
- Storage usage

**Pipeline (custom metrics):**
- Jobs processed per hour
- Avg processing time per match
- Per-stage timing breakdown
- Frame quality distribution (Gold/Silver/Bronze ratio)

**Model quality (offline + online):**
- Daily synthetic test (run on holdout match, compare predictions vs ground truth)
- Detection AP trend over time
- DINOv2 classification accuracy trend
- "Unknown brand" rate (flag spike — possible new sponsor not in bank)

**Business:**
- Reports delivered per week
- Per-club active usage
- Sponsor satisfaction (NPS post-report)

**Alerts:**
- Processing failure rate > 5% → Slack alert
- Model AP drops > 5% → email DS team
- New "unknown brand" detected in N matches → review queue

---

## NHÓM K — Security & Access Control

### Q41. Multi-tenant isolation (multiple clubs) — data segregation?

**Vấn đề:**
Club A và Club B can't see each other's data, models, reports.

**Giải pháp v5:**

1. **Database-level isolation:**
   - All tables have `club_id` column
   - Row-Level Security (RLS) in PostgreSQL
   - Application enforces club_id in every query

2. **Storage isolation:**
   - S3 buckets organized: `bucket/{club_id}/videos/...`
   - IAM policies per club_id

3. **Model isolation:**
   - Per-club reference banks
   - Shared detection model (Stage 3A) — but inference results filtered by club_id

4. **Kubernetes namespace per club** (for SaaS):
   - Resource quotas per namespace
   - Network policies prevent cross-club communication

### Q42. Authentication & authorization?

**Vấn đề:**
Who can access what?

**Giải pháp v5:**

**Authentication: OAuth2 + JWT**
- Single Sign-On (SSO) integration for club admins
- API keys for service-to-service

**Authorization (RBAC):**
- Roles: `club_admin`, `analyst`, `viewer`, `system_admin`
- club_admin: full control of their club's data
- analyst: can run jobs, view reports
- viewer: read-only access to reports
- system_admin: cross-club (us, internal)

**Multi-factor authentication (MFA):** Required for club_admin role.

### Q43. Sensitive data — broadcast video copyright, sponsor contracts?

**Vấn đề:**
Videos are copyrighted by broadcaster. Reports may include commercially sensitive info.

**Giải pháp v5:**

1. **License agreement:**
   - Bradford warrants they have right to provide video (clause in service agreement)
   - We process for analytics only, no public redistribution
   - Reports include "Confidential — for {Club Name} use only"

2. **Encryption:**
   - At rest: AES-256 (S3 SSE)
   - In transit: TLS 1.3 everywhere
   - Backups encrypted

3. **Access logs:**
   - Every access to video/report logged (who, when, IP)
   - Auditable

### Q44. Audit logging — who accessed what?

**Vấn đề:**
Compliance + sponsor dispute support.

**Giải pháp v5 — Centralized audit log:**

```python
# Every privileged action emits audit event
audit_log({
    "timestamp": now(),
    "user_id": "alice@bradford.com",
    "action": "report.download",
    "resource": "report:abc123",
    "club_id": "bradford_bulls",
    "ip_address": "1.2.3.4",
    "user_agent": "...",
    "outcome": "success"
})
```

**Stored in append-only log (S3 immutable bucket or CloudTrail-style).**

**Retention: 7 years** (matches sponsor contract dispute window).

**Searchable** (via Elasticsearch or Athena) for incident response.

### Q45. Compliance — GDPR (UK), data residency?

**Vấn đề:**
UK GDPR requires personal data protection. Players are identifiable in video.

**Giải pháp v5:**

1. **Lawful basis:**
   - Public broadcast = no expectation of privacy in players
   - Our processing = legitimate interest (sports analytics for club)
   - Document DPIA (Data Protection Impact Assessment)

2. **Data minimization:**
   - We process video → extract aggregate metrics → discard raw frames if possible
   - We do NOT extract per-player identifiable data (faces) for analytics

3. **Data residency:**
   - UK clubs → UK-based hosting (AWS London, GCP london-west)
   - Configurable per tenant

4. **Right to erasure:**
   - If a player invokes GDPR right, we can mark their face/tracks for exclusion from future reports
   - Past reports remain (legal basis: contract performance)

5. **Data Protection Officer (DPO):** Assigned for SaaS scale.

---

## NHÓM L — Business Operations & Cost

### Q46. Pricing model for SaaS?

**Vấn đề:**
How do we monetize?

**Giải pháp v5 — Tiered pricing:**

**Tier 1: Per-match (small clubs):**
- £200/match (POC report)
- £150/match (subscription, 10+ matches/year)
- Includes: 1 report, basic dashboard, 90-day retention

**Tier 2: Season subscription (mid clubs):**
- £15,000/season (20+ matches)
- Includes: all matches, cross-match trends, custom QI weights, API access

**Tier 3: Enterprise (Super League, top clubs):**
- £50,000+/year custom
- Includes: dedicated GPU, white-label dashboards, sponsor portal, integration with their CRM

**Add-ons:**
- Replay analysis: +20% per report
- Custom branding for sponsor handouts: +£500
- Live match analytics (v3 feature): +50% per match

**Comparison to industry:**
- Nielsen Sports: £100K+ per club annual
- GumGum: similar
- Hookit/KORE: £30-80K
- We position: **25-50% cheaper, more transparent methodology**

### Q47. Cost per match (compute) — estimate and optimize?

**Vấn đề:**
Cost determines pricing floor.

**Giải pháp v5 — Cost breakdown:**

| Component | Cost (T4) | Cost (A100) |
|-----------|-----------|-------------|
| Storage (90 min video) | $0.05 | $0.05 |
| Frame extraction (Stage 1) | $0.15 | $0.05 |
| Annotation (one-time per match) | $0.00 (auto via SAM 2) | $0.00 |
| Training (amortized) | $0.20 | $0.20 |
| Inference (Stage 2-5) | $0.40 | $0.15 |
| Storage (results) | $0.02 | $0.02 |
| **Total per match** | **$0.82** | **$0.47** |

**Margin:**
- T4 cost $0.82, sell £150 ($188) → 99% gross margin
- A100 cost $0.47, sell £150 → 99.7% gross margin

**Even with overhead (engineering, ops, support): 70-80% net margin → strong SaaS unit economics.**

**Optimization opportunities:**
- Spot GPU for batch: -70% compute cost
- Per-class lazy loading (don't load DINOv2 for matches without certain brands): -10%
- Caching reference banks: -5%

### Q48. SLA — uptime, processing time guarantees?

**Vấn đề:**
Sponsor expects "report delivered within 24h post-match." Engineering can promise what?

**Giải pháp v5 — SLA tiers:**

**Standard SLA:**
- Processing time: 4 hours from upload to report
- Uptime: 99% (allows 7 hours downtime/month)
- Support response: 24h business days

**Premium SLA:**
- Processing time: 1 hour
- Uptime: 99.9%
- Support: 4h response, 24/7

**Implementation:**
- Standard: shared GPU queue, may wait if many jobs
- Premium: dedicated GPU per club, no queue
- Monitoring: alert if any job > SLA → escalate

### Q49. Customer support workflow?

**Vấn đề:**
Clubs report bugs / questions. How handled?

**Giải pháp v5:**

**Tier 1: Self-service**
- Documentation portal (per-club FAQs)
- Video tutorials
- Sample reports

**Tier 2: Email/chat support**
- Response within SLA
- Common issues: report interpretation, dashboard navigation, billing

**Tier 3: Engineering escalation**
- Bugs in pipeline
- Custom report requests
- Integration issues

**Tier 4: Dedicated CSM (Customer Success Manager)** for Enterprise tier
- Quarterly business reviews
- Custom feature requests

**Ticketing system:** Zendesk or Linear (depending on team size).

**SLA on response:**
- Standard: 24h
- Premium: 4h
- Enterprise: 1h

### Q50. Onboarding new club — friction points?

**Vấn đề:**
Club signs up. How long until first report?

**Giải pháp v5 — 4-week onboarding:**

**Week 1: Setup**
- Club provides: 1 sample match video, sponsor logo files, kit photos, sponsorship pricing CSV
- Engineering: build per-club reference bank, calibrate team palette, setup namespace
- Output: pipeline ready

**Week 2: First match**
- Club uploads first real match
- Pipeline processes
- Engineering reviews report internally, adjusts if obvious issues
- Deliver report to club

**Week 3-4: Iteration**
- Club provides feedback on report format, metrics
- We iterate (custom QI weights if club has strong opinions)
- Process 2-3 more matches to establish baseline

**By end of week 4:** Self-service mode. Club uploads, gets report within SLA.

**Friction points to mitigate:**
- "What format for sponsor logo files?" → upload guide, accept any PNG/JPG, auto-validate
- "How to interpret report?" → glossary + sample annotated report
- "Why is brand X exposure low?" → diagnostic mode showing per-brand confidence

---

## 🎯 Tổng kết Part 2

50 câu hỏi tổng cộng (25 technical edge cases + 25 production ops) — comprehensive cover từ ML internals đến SaaS deployment.

**Critical insights:**

1. **Storage tiered architecture** giảm cost 80% vs naive S3 standard
2. **Per-component model versioning** essential cho rollback
3. **API async + webhook** là pattern chuẩn cho long-running ML jobs
4. **Audit logging** là #1 defensibility feature (vẫn confirmed từ V5_QA_EDGECASES Q22)
5. **Per-match cost $0.50-1.00** → ~99% gross margin tại £150/match pricing
6. **4-week onboarding** realistic cho new club, hầu hết friction ở thu thập initial assets

**No question discovered an unsolvable problem.** v5 + production ops architecture remain valid.

**Open architecture questions to validate:**
1. Multi-tenant isolation patterns work for >50 clubs? (PostgreSQL RLS scaling)
2. Spot GPU reliability acceptable for training batches?
3. DPIA (GDPR) compliance review with UK legal counsel
4. Sponsor contract templates (we own report data vs club owns)?

---

## Phụ lục: Tổng số câu hỏi đã trả lời

| File | Số câu hỏi | Phạm vi |
|------|-------------|---------|
| SOLUTION_ARCHITECTURE_V5.md | 5 (user-implied) | Core architecture decisions |
| V5_DEEP_DIVE.md | 2 (DINOv2 + SAM 2) | Component deep dives |
| V5_QA_EDGECASES.md | 25 | Technical edge cases |
| **V5_QA_PRODUCTION_OPS.md** | **25** | Production operations |
| **Total** | **57** | Comprehensive |
