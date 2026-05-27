Recommended Roadmap 
Phase 1 — Production Foundation
1A Basic 
✅ Portfolio
✅ Watchlist
✅ AnalysisCache
✅ AnalysisHistory
✅ Settings
1B Advance
✅ 3 Layer Optimizer
✅ Deterministic Scoring
✅ Latency & Cost Tracking
✅ Confidence Capping
✅ Chart Indicators
1C Server Deploy
✅ Deploy
✅ PostgreSQL
✅ VPS
✅ Vercel
Phase 2 — Portfolio Memory
✅ Transactions
✅ Snapshots
✅ portfolio performance history [ Performance charts , Portfolio growth ]
Phase 2.5
✅ Benchmark tracking
✅ signal history

Phase 3 — Investment Intelligence (Institutional Intelligence Layer)
Phase 3A — Core Historical Analytics
✅ Equity curve
✅ Drawdown
✅ Sharpe
✅ Alpha/Beta
✅ Signal analytics
✅ Allocation analytics
✅ Benchmark comparison
Phase 3B — Investment Intelligence
3B.1 — Factor Exposure Analysis ⭐ PRIORITY
3B.2 — Strategy Persona System 
3B.3 — Regime Detection
3B.4 — Optimizer Intelligence Upgrade / Adaptive Optimizer Policy Engine
3B.5 — Deterministic Constraint Resolution Layer
3B.6 — Hierarchical Risk Trade-Off Engine
3B.7 — Decision Attribution & Benchmark Intelligence / Decision Memory System
3B.7A — Recommendation Snapshot Architecture ✅
recommendation snapshots
regime snapshots
optimizer metadata
consensus storage
3B.7B — Attribution Analytics Engine ✅
attribution_engine
human_vs_ai
regime attribution
calibration analytics
3B.7C — Execution Lifecycle Tracking ⏳
user_execution_decisions
shadow_portfolios
shadow_portfolio_snapshots
execution linkage
paper trading lifecycle
3B.7D — Adaptive Learning Memory (อนาคต)
confidence_calibration_records
routing feedback memory
model trust score
agent scoring history
persona performance memory
Phase 3B.8 — Cash-Flow-Adjusted Return Accounting
Phase 3B.9 — Position Import Accounting Fix ✅ SHIPPED 2026-05-25


Checklist ที่ควร verify ด้วยข้อมูลจริง:

Accounting Integrity
 realized/unrealized continuity
 deposits stripped
 imports stripped
 fee deduction
 DR pricing
 shadow portfolio continuity
Analytics Integrity
 alpha reasonable
 sharpe reasonable
 drawdown not exploding
 calibration buckets stable
Optimizer Integrity
 REBALANCE no longer deadlock
 turnover relaxation works
 policy hierarchy works
 regime switching works
 
Phase 3C — Advanced Historical Analytics
✅ Dynamic routing => ตอนนี้: DONE ระดับสูงแล้ว
✅ Performance Attribution => PARTIAL DONE
✅ Sector evolution => ตอนนี้: foundation พร้อม เหลือแค่: 
stacked area chart
historical aggregation
✅ Quality Score Logging => PARTIAL DONE เหลือแค่: 
optimizer outcome score
recommendation success
signal persistence
rebalance effectiveness
✅ AI Attribution History => PARTIAL DONE เหลือแค่: 
ต่อไปคือ:
“ใครเป็นคนเสนอ”
“ใคร override”
“สุดท้ายใครถูก”
✅ Confidence calibration
ตอนนี้: STARTED
Agree/Disagree
Confidence
Risk
อนาคต:
probabilistic confidence
historical accuracy calibration
confidence vs realized return

Phase 3D -- Testing & Tuning
✅ Backtesting => ยังไม่ควรทำเต็มระบบตอนนี้
✅ Optimization / Signal tuning => ทำได้ “เฉพาะ lightweight tuning”
แต่ยังไม่ควร:
brute force optimization
hyperparameter sweep
genetic tuning
จนกว่า:
data >= 6–12 เดือน
✅ ML optimization
✅ hyperparameter search


PHASE 4: PERSONAL WEALTH FEATURES (Human Experience Layer)
 │
 ├── 🟩 Phase 4A: Real Asset Tracking (ฐานข้อมูลสินทรัพย์จริง)
 │    └── Net worth tracking & Dividends / Cash flow
 │
 ├── 🟨 Phase 4B: Future Projection & Strategy (การจำลองอนาคต)
 │    └── DCA planning & Retirement simulation
 │
 └── 🟦 Phase 4C: The Muji UI (ซ่อนความซับซ้อนให้มนุษย์ใช้งาน)
      └── Human-Friendly Translation Layer: จูน Prompt ส่วนขยายให้แปลงศัพท์การเงินดิบๆ ให้เป็นคำเปรียบเปรยบ้านๆ (
	  └── The Minimalist View Toggle (MUJI UI):ซ่อนแผงควอนท์ 3A/3B ทั้งหมดออกไปจากสายตา เหลือแค่กราฟวงกลมคลีนๆ ตัวเลขเงินที่งอกงาม และกล่องสรุปภาษาไทยน่ารักๆ สไตล์มินิมอล
	  └── Risk Profile & Investment Goal Onboarding 
		[ คำตอบของผู้ใช้ในหน้า 4C ] 
			│
			▼ (ส่งผ่าน AI / Rules Engine หลังบ้าน)
			[ ปรับค่าโครงสร้างพอร์ตโฟลิโอนั้นโดยอัตโนมัติ ]
			 ├── กำหนด Strategy Persona ➔ (DIVIDEND, GROWTH, VALUE, BALANCED)
			 ├── ล็อกข้อจำกัดภาษี        ➔ (OPEN, ThaiESG, RMF, SSF)
			 └── สร้างขอบเขตความเสี่ยง    ➔ (เช่น ตั้งค่า max_single_position_pct หรือ beta_ceiling คุมทับอีกชั้น)
	  └── Goal-Based & Notification Features: ระบบแจ้งเตือนผ่าน LINE / Email และระบบตั้งเป้าหมายชีวิต (เช่น พอร์ตเพื่อจัดงานแต่งงานเดือนธันวาคม, พอร์ตเงินออมระยะยาว)
Frontend
 ├── Simple Mode (Default)
 └── Advanced Mode (Power User)

Phase 5 — Multi-user SaaS Platform engineering (Platform / SaaS Layer)
✅ workspaces
✅ credits / User Wallet
✅ policy engine
✅ billing
✅ usage reports


## Run Instructions
```bash
# Backend (Windows)
g:\work\ta\stock-analysis\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# DB migrations (PostgreSQL)
cd backend && alembic upgrade head
```