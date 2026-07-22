UI Polish Backlog — Optimizer / Execution UX
UI-01 — Funding Awareness

Problem

Optimizer แนะนำ Source of Fund ตาม allocation logic

Execution Plan พบว่า cash เพียงพอ จึง override เป็น "ไม่ต้องขาย"

ผู้ใช้ที่ไม่รู้ architecture จะเข้าใจว่า

"AI ไม่เห็นเงินสด"

ทั้งที่จริงเป็นคนละ layer

Goal

ทำให้ผู้ใช้เข้าใจว่า

Optimizer
ตอบ "ควรถือพอร์ตแบบไหน"
Execution Planner
ตอบ "จะ execute ยังไง"
Possible UX

ก่อน Execution Plan

Funding Analysis

Available Cash
฿420,000

Required
฿135,000

Status

✓ Existing cash is sufficient.

No liquidation required.

แล้ว Execution Plan ก็เหลือแค่

BUY

MTUM
XLK

โดยไม่มี SELL ที่ถูก override

UI Hint

หรือเพิ่มข้อความเล็ก ๆ

Execution layer detected sufficient available cash.

Sell recommendations generated for funding are not required.
Expected User Perception

จากเดิม

AI ไม่เห็นเงิน

เปลี่ยนเป็น

AI แยก Strategic Allocation กับ Execution Planning