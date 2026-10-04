# ZyPulse Product Requirements Document

**Product:** ZyPulse  
**Version:** 0.1 (Hackathon Product Direction)  
**Status:** Proposed  
**Category:** Safe AI self-care companion for people managing Type 2 Diabetes

## 1. Product Vision

ZyPulse helps people turn everyday self-care into safer, clearer conversations with their care team.

It is not a diagnostic tool, a medical device, or a replacement for clinical care. It is a personalised self-care companion that helps users record routines, understand verified trends, take low-risk next steps, and prepare better questions for healthcare professionals.

## 2. Problem Statement

People managing Type 2 Diabetes often need to track glucose readings, meals, medication adherence, and activity. Existing trackers can collect data but frequently leave users with three gaps:

- They do not explain what the recorded information means in plain language.
- They do not turn scattered records into a manageable next action.
- They do not help users prepare meaningful, evidence-based conversations with their doctor, pharmacist, or care team.

At the same time, open-ended health chatbots can create unsafe expectations by appearing to diagnose conditions, prescribe medication, or infer causation from incomplete data.

## 3. Product Opportunity

ZyPulse differentiates itself through a safe, closed-loop experience:

```text
Record -> Verified insight -> One small action -> Reflection -> Visit preparation
```

The product uses deterministic code for calculations and safety controls, while AI is used only to explain verified information in approachable language. This makes the product both useful and appropriately bounded for a healthcare setting.

## 4. Target User

### Primary user: Mr Tan

A fictional Singapore-based adult managing Type 2 Diabetes who:

- Wants a simple routine for logging glucose, medication, meals, and activity.
- May feel overwhelmed by complex health information.
- Wants to notice patterns without being given medical instructions.
- Needs support preparing for conversations with clinicians.
- May prefer English, Chinese, Malay, or Tamil.

### Secondary users

- Family caregivers, with explicit user consent.
- Doctors, pharmacists, or care teams reviewing a user-prepared summary.
- Community-health partners in a future integration model.

## 5. Product Principles

1. **AI for language; deterministic code for facts.** Trend values, adherence rates, and record summaries must be calculated by verified code.
2. **Safety is non-bypassable.** Medication changes, diagnoses, unsafe medical claims, and prompt-injection attempts must be blocked before reaching the model or user.
3. **Support action, not treatment decisions.** ZyPulse can suggest logging, reflection, preparation, and professional discussion; it must not prescribe, diagnose, or direct medication changes.
4. **Explain uncertainty.** Sparse or incomplete data must be labelled as insufficient and must never be used to imply causation.
5. **Respect user control.** Sensitive data sharing is opt-in, visible, revocable, and clearly separated from demo data.
6. **Make local relevance tangible.** Language, food, routines, and community-resource concepts should reflect the Singapore context.

## 6. Core Product Experience

### 6.1 Daily Pulse: the new home experience

The default landing screen should answer three questions:

1. How am I doing today?
2. What is one small thing I can do next?
3. Why is ZyPulse suggesting it?

The Daily Pulse must show:

- Recent record completeness for glucose, medication, meals, and activity.
- Deterministic 7-day/30-day trend highlights.
- A single low-risk, practical micro-action.
- A transparent explanation based only on available records.
- A clear limitation statement when evidence is insufficient.

**Example:**

> Your recent fasting-glucose trend has changed compared with the previous period, but there are limited readings. For your next log, consider adding your evening meal and activity. This can help you build a clearer record to discuss with your care team.

The product must not say that a meal, exercise, or behaviour caused a glucose change.

### 6.2 Capture everyday self-care

Users can log:

- Fasting and evening glucose readings.
- Medication status (for example, taken, missed, or not recorded), without dosage recommendations.
- Activities, duration, and general location.
- Meals, portions, notes, and whether the entry should be included in a visit summary.
- Personal notes, symptoms, or questions for a future healthcare visit.

### 6.3 Meal awareness

Users can search and add familiar Singapore foods from a curated catalogue, review estimated carbohydrates and sugar, and adjust entries before saving.

Photo-assisted meal entry may be included only when connected to a real vision service. Until then, it must be explicitly labelled as a simulated workflow and must never be presented as image recognition.

### 6.4 Coach: safe, evidence-grounded conversation

The coach should:

- Explain deterministic trends in the user's selected language.
- Help users reflect on their logging routine.
- Suggest questions to ask a clinician or pharmacist.
- Redirect prohibited medical requests to an appropriate professional.

The coach must not:

- Diagnose diabetes or any other condition.
- Recommend starting, stopping, increasing, or decreasing medication.
- Claim a behaviour caused a health outcome.
- Invent readings, events, or programme availability.
- Declare an activity medically safe for an individual user.

### 6.5 Health Summary and Doctor Visit Pack

ZyPulse should turn everyday records into a user-controlled, visit-ready summary containing:

- Recent glucose, medication-adherence, and activity trend cards.
- User-selected meal notes, symptoms, and personal observations.
- A list of questions the user wants to discuss.
- Safe suggested discussion topics based on deterministic trends.
- A visible disclaimer that the summary is not a clinical report and has not been shared automatically.

For the hackathon demo, this can be presented as an export-ready preview. Future versions may provide a PDF export or consent-based share link.

### 6.6 Community connection

The product may surface relevant community activities based on user interests, area, and accessibility preferences.

All current catalogue data must be labelled as synthetic/demo content. Registration must remain simulated until a verified external integration and a complete consent workflow exist.

## 7. Key User Flow

1. The user opens **Daily Pulse**.
2. They see a concise, verified status and one small micro-action.
3. They log an evening meal, activity, or glucose reading.
4. ZyPulse updates the deterministic trend context and explains what was recorded without drawing causal conclusions.
5. The user asks a self-care question in Coach.
6. If the question is safe, Coach responds using verified context. If it requests diagnosis or medication changes, safety controls block it and redirect the user.
7. The user saves a concern or question for their next appointment.
8. The user opens the **Doctor Visit Pack** to review the summary they control.

## 8. Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Provide a Daily Pulse dashboard with record completeness, deterministic trend highlights, one micro-action, rationale, and uncertainty label. | P0 |
| FR-02 | Persist glucose, medication-status, activity, meal, and note logs in a user-scoped data store. | P0 |
| FR-03 | Calculate glucose trends, medication adherence, and activity frequency deterministically. | P0 |
| FR-04 | Screen user input and AI output against safety policies before it is displayed. | P0 |
| FR-05 | Generate conversational explanations from verified trend context only; use a safe fallback when no LLM is configured. | P0 |
| FR-06 | Create an editable Doctor Visit Pack from user-approved records and notes. | P0 |
| FR-07 | Provide clearly labelled local food-catalogue search and manual meal entry. | P1 |
| FR-08 | Translate core navigation, safety notices, and key workflows into English, Chinese, Malay, and Tamil. | P1 |
| FR-09 | Provide a real photo-analysis workflow only after connecting a vision service; otherwise retain explicit simulation labels. | P1 |
| FR-10 | Use a complete, explicit consent flow before any external activity-registration or data-sharing integration. | P2 |

## 9. Non-Functional and Safety Requirements

- Every numerical health trend shown to a user must originate from the deterministic calculation engine.
- AI output must be checked before display and must fail safely if validation cannot be completed.
- The UI must identify synthetic data, simulations, and unavailable integrations.
- Any information shared externally must require explicit user approval and state the fields, purpose, recipient, and cancellation option.
- Users must be able to review and edit their own notes before including them in the Doctor Visit Pack.
- The product must clearly state that it is a self-care support prototype, not a medical device.

## 10. Explicit Non-Goals

ZyPulse will not, in this hackathon version:

- Diagnose, triage, or predict medical conditions.
- Give medication doses or treatment-change recommendations.
- Replace clinical care or emergency services.
- Claim clinical validation.
- Automatically share data with HPB, Healthy 365, clinicians, or family members.
- Present simulated image recognition, activity listings, registration, reminders, or rewards as live services.
- Implement authentication, identity verification, or production-grade multi-tenant account management.

## 11. Success Metrics

### Hackathon success

- A judge can understand the product value proposition in the first 30 seconds.
- The core demo completes reliably in under 3 minutes.
- The safety-interception scenario is clearly visible and understandable.
- The demo shows a complete path from record to insight to action to visit preparation.

### Product signals for a future pilot

- Percentage of active users completing at least three self-care logs per week.
- Percentage of active users opening Daily Pulse at least twice per week.
- Percentage of users creating or updating a Doctor Visit Pack before an appointment.
- Percentage of unsafe medical prompts safely redirected.
- User-reported confidence in discussing self-care records with a healthcare professional.

## 12. Hackathon Demo Narrative

1. Introduce Mr Tan and the challenge of turning scattered daily records into a useful clinical conversation.
2. Show Daily Pulse: verified trends, data limitations, and one small next action.
3. Log a familiar dinner and an evening glucose reading.
4. Show the resulting trend context without claiming causation.
5. Ask Coach an unsafe medication question. Demonstrate that ZyPulse blocks it, explains the boundary, and offers a safe alternative: save a question for a clinician.
6. Open the Doctor Visit Pack and show how the user's observations, trends, and questions become a concise, user-controlled preparation tool.
7. Close with the trust architecture: deterministic calculation, bounded AI explanation, non-bypassable safety, and explicit user consent.

## 13. Delivery Roadmap

### Phase 1: Competition-ready (P0)

- Build Daily Pulse as the default screen.
- Connect existing logs, trends, coach, and summary into one continuous flow.
- Improve Doctor Visit Pack presentation.
- Make safety intervention visibly explainable in the UI.
- Prepare a seeded, repeatable demo user journey.

### Phase 2: Product polish (P1)

- Localise core UI strings across the four supported languages.
- Add real-time refresh after data entry.
- Add visual data-source and explanation cards to AI responses.
- Integrate a real image-analysis provider or remove the photo-entry entry point from the main demo.

### Phase 3: Integration readiness (P2)

- Complete the consent workflow for external sharing or registrations.
- Add exportable Doctor Visit Pack PDF.
- Establish integration contracts for community activity providers.
- Add automated coverage for safety policies, calculation correctness, and critical API flows.

## 14. Product Positioning

> **ZyPulse does not replace clinical care. It helps people turn everyday self-care into safer, clearer conversations with their care team.**

