# Blood Donation Network with Smart Matching

An event-driven platform prototype that helps hospitals and requesters
identify suitable blood donors faster by ranking eligible donors and
prioritizing urgent requests.

## Overview

Finding a compatible blood donor during an emergency can be slow when
requests are shared through phone calls or unstructured messaging
groups. This project brings donor discovery, request prioritization,
availability checks, and notifications into one platform.

The system is designed to rank donors using blood-group compatibility,
availability, distance, and response history. Emergency requests receive
higher priority, while event-driven notifications help track donor
responses and escalate when a donor declines or does not respond.

> **Project status:** Academic prototype. Location and notification
> behaviour may be simulated. This project is not a substitute for
> medical advice, clinical eligibility checks, or official blood-bank
> procedures.

## Key Features

-   **Donor and requester workflows:** Organize donor profiles and blood
    requests.
-   **Blood-group compatibility:** Filter candidates using a blood-group
    compatibility map.
-   **Smart donor ranking:** Score eligible candidates using
    compatibility, distance, availability, and response history.
-   **Eligibility and cooldown checks:** Exclude unavailable donors and
    donors within the configured post-donation cooldown period.
-   **Urgency-based request queue:** Prioritize Critical, Urgent, and
    Normal requests, with waiting time used to order requests of equal
    priority.
-   **Event-driven notifications:** Model events such as
    `RequestCreated`, `DonorMatched`, `DonorAccepted`, `DonorDeclined`,
    `NoResponseTimeout`, and `DonationCompleted`.
-   **Scheduling and escalation:** Track availability and move to the
    next suitable donor when a response is declined or times out.
-   **Dashboards:** Support request tracking and donor
    availability/history views.
-   **Automated tests:** Includes tests for authentication,
    compatibility, cooldowns, event flow, rate limiting, prioritization,
    and scoring.

## How Smart Matching Works

1.  **Compatibility filter** --- retain donors compatible with the
    recipient's blood group.

2.  **Eligibility filter** --- remove unavailable donors and donors who
    have not completed the configured cooldown period.

3.  **Distance calculation** --- calculate distance from simulated donor
    and hospital coordinates using the Haversine formula.

4.  **Scoring and ranking** --- rank the remaining donors using a
    weighted score:

    `Score = w1 × BloodMatch + w2 × (1 / Distance) + w3 × Availability + w4 × ResponseHistory`

5.  **Notification** --- select the top-ranked donors for notification.
    Weights can vary with urgency so distance and availability matter
    more in critical cases.

6.  **Escalation** --- if a donor declines or does not respond in time,
    consider the next suitable donor.

The exact scoring weights and configuration are defined by the
implementation. Any cooldown values are configurable prototype rules and
must not be treated as medical guidance.

## System Architecture

The project is organized into a Python backend, a JavaScript frontend,
and automated tests.

``` text
Project/
├── backend/
│   ├── database.py
│   ├── event_bus.py
│   ├── main.py
│   ├── matching_service.py
│   ├── models.py
│   ├── notification_service.py
│   ├── priority_queue.py
│   ├── scheduling_service.py
│   └── synthetic_data.py
├── frontend/
│   ├── app.js
│   ├── index.html
│   └── styles.css
├── tests/
├── benchmark.py
├── run.py
├── README.md
└── .gitignore
```

### Main components

-   **User and data layer:** Maintains application models and data
    access.
-   **Matching service:** Filters and ranks donor candidates.
-   **Priority queue:** Orders requests by urgency and waiting time.
-   **Event bus:** Enables services to react to application events
    without being tightly coupled.
-   **Scheduling service:** Manages donor availability and cooldowns.
-   **Notification service:** Handles notification events and response
    escalation.
-   **Frontend:** Provides the browser-based user interface.
-   **Tests and benchmark:** Help validate behaviour and evaluate
    performance.

## Technology Stack

-   **Backend:** Python
-   **Frontend:** HTML, CSS, JavaScript
-   **Testing:** pytest
-   **Core concepts:** Event-driven architecture, publish/subscribe
    messaging, priority queues/heaps, weighted ranking, blood-group
    compatibility, Haversine distance calculation, synthetic data

The repository's source code and dependency configuration are the source
of truth for the exact frameworks and package versions.

## Getting Started

### Prerequisites

-   Python installed
-   Git
-   A modern web browser

### 1. Clone the repository

Replace `YOUR_GITHUB_USERNAME` with your GitHub username.

``` bash
git clone https://github.com/YOUR_GITHUB_USERNAME/blood-donation-network-smart-matching.git
cd blood-donation-network-smart-matching
```

### 2. Create and activate a virtual environment

**Windows PowerShell**

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

``` bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

If the repository contains a `requirements.txt` file:

``` bash
python -m pip install -r requirements.txt
```

If it does not, install the dependencies listed or imported by the
project source files. Do not install arbitrary packages without checking
the project's imports.

### 4. Run the application

The repository includes a root-level `run.py` entry point. Start with:

``` bash
python run.py
```

If the application prints a local URL, open that URL in your browser. If
startup fails, check the terminal traceback and the project's
configuration before changing the launch command.

### 5. Run tests

``` bash
python -m pytest
```

To run a particular test file:

``` bash
python -m pytest tests/test_matching_service.py
```

Use the actual test filenames present in the repository if they differ.

## Testing and Evaluation

The project is designed to be evaluated using:

-   **Time to first match:** How quickly the system returns a suitable
    donor.
-   **Top-ranked donor acceptance rate:** How often highly ranked donors
    accept a request.
-   **Queue waiting time by urgency:** Whether critical requests are
    processed ahead of routine requests.
-   **Matching correctness:** Whether compatibility and eligibility
    rules are applied correctly.
-   **Event-flow reliability:** Whether declines and timeouts trigger
    the expected escalation behaviour.
-   **Load behaviour:** Performance with larger synthetic donor and
    request sets.

Use synthetic data for development and benchmarking. Do not test with
real donor health information unless the necessary authorization,
consent, security, and privacy safeguards are in place.

## Future Enhancements

-   Integrate map and routing APIs for real travel distance and
    estimated travel time.
-   Add mobile support with consent-based location sharing and push
    notifications.
-   Explore machine learning for donor response likelihood and
    blood-demand forecasting.
-   Integrate with hospital and blood-bank inventory systems where
    authorized.
-   Extend the model to other donation workflows where clinically and
    legally appropriate.
-   Strengthen authentication, role-based access control, audit logging,
    consent management, and encryption.

## Privacy and Safety

-   Use synthetic or anonymized data in public demos.
-   Never commit `.env` files, credentials, private keys, or real donor
    records.
-   Treat compatibility, eligibility, and cooldown logic as prototype
    rules until validated by qualified medical professionals and
    applicable official guidance.
-   Do not use this prototype to make clinical decisions or replace
    blood-bank screening and procedures.

## References

-   World Health Organization --- *Blood Safety and Availability*:
    https://www.who.int/news-room/fact-sheets/detail/blood-safety-and-availability
-   Cormen, Leiserson, Rivest, and Stein --- *Introduction to
    Algorithms* (priority queues and heaps).
-   Hohpe and Woolf --- *Enterprise Integration Patterns* (messaging and
    event-driven design).
-   Sam Newman --- *Building Microservices* (service decomposition and
    communication patterns).
-   National Blood Transfusion Council, India --- blood donor selection
    and referral guidance.
-   e-RaktKosh, Government of India: https://eraktkosh.mohfw.gov.in/

------------------------------------------------------------------------

**Built as a software engineering project** exploring how event-driven
systems and smart ranking can support faster blood-donor discovery.
