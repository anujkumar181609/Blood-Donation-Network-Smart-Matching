"""
Blood Donation Network with Smart Matching
Main Entrypoint & Server Launcher
Chandigarh University | AIT-CSE-AIML (Academic Year: 2026-27)
Authors: Anuj Kumar [24BAI70735], Shlok Kandola [24BAI70823]
Guide: Ms. Amandeep Kaur Seekhon
"""

import sys
import webbrowser
import threading
import time
import uvicorn


def open_browser():
    time.sleep(1.2)
    url = "http://127.0.0.1:8000"
    print(f"\n[+] Opening web interface at {url} in your browser...")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"[-] Could not auto-launch browser: {e}. Please open {url} manually.")


def main():
    print("=" * 78)
    print("  BLOOD DONATION NETWORK WITH SMART MATCHING")
    print("  An Event-Driven Platform for Finding the Right Donor in Time")
    print("  Chandigarh University | Department of AIT-CSE-AIML (2026-27)")
    print("=" * 78)
    print("  Project Team:")
    print("    - Anuj Kumar   [UID: 24BAI70735]")
    print("    - Shlok Kandola [UID: 24BAI70823]")
    print("  Project Guide:")
    print("    - Ms. Amandeep Kaur Seekhon")
    print("-" * 78)
    print("  Components active:")
    print("    [✓] User & Hospital Service (Chandigarh Tricity geo-grid)")
    print("    [✓] Smart Matching Service (Haversine & 4-parameter dynamic weights)")
    print("    [✓] Priority Queue Service (O(log n) min-heap & starvation prevention)")
    print("    [✓] Scheduling Service (NBTC 90-day / 120-day cooldown period)")
    print("    [✓] Event Bus Broker (Decoupled pub/sub event stream)")
    print("    [✓] Notification Service (In-App, SMS, Email simulation & escalation)")
    print("    [✓] Interactive Web Dashboard (Leaflet GIS map & live monitor)")
    print("=" * 78)

    # Launch browser in separate thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Start FastAPI server
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False, log_level="info")


if __name__ == "__main__":
    main()
